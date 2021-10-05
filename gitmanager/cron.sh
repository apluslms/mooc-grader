#!/bin/bash

FLAG="/tmp/mooc-grader-manager-clean"
FLAG_NEW="/tmp/mooc-grader-manager-clean-new-sphinx"
flagfile="$FLAG"
LOG="/tmp/mooc-grader-log"
LOG_NEW="/tmp/mooc-grader-log-new-sphinx"
logfile="$LOG"
SQL="sqlite3 -batch -noheader db.sqlite3"
TRY_PYTHON="/srv/grader/venv/bin/activate"

# Only support the new Sphinx version in this server. It is installed in the venv.
installed_sphinx_version='new'
flagfile="$FLAG_NEW"
logfile="$LOG_NEW"

if [ -e "$flagfile" ]; then
  exit 0
fi
touch "$flagfile"

cd `dirname $0`/..
if [ -d exercises ]; then
  CDIR=exercises
else
  CDIR=courses
fi
CDIR=$(realpath $CDIR)

if [ -f $TRY_PYTHON ]; then
  source $TRY_PYTHON
fi

# Handle each scheduled course key.
# Build only courses that require the same Sphinx version as is installed
# in this container that is running now.
$SQL "SELECT DISTINCT r.key
      FROM gitmanager_courseupdate AS u LEFT JOIN gitmanager_courserepo AS r ON u.course_repo_id=r.id
      WHERE u.updated=0
      ORDER BY u.request_time DESC;" | \
while read key; do
  IFS=$'\n' read -d '' -r repo_id url branch < <($SQL -separator $'\n' "
    SELECT id,git_origin,git_branch FROM gitmanager_courserepo WHERE key='$key';")
  if [ -z "$repo_id" ]; then
    echo "No db entry for key '$key'" >&2
    continue
  fi
  IFS=$'\n' read -d '' -r update_id request_time < <($SQL -separator $'\n' "
    SELECT id,request_time FROM gitmanager_courseupdate
    WHERE course_repo_id=$repo_id and updated=0 ORDER BY request_time DESC LIMIT 1;")

  # reset/start log
  echo "Updating '$key' (update_id=$update_id, request_time=$request_time)" > "$logfile"

  gitmanager/cron_pull_build.sh "$TRY_PYTHON" "$key" "$url" "$branch" >> "$logfile" 2>&1 || continue

  # Update database
  $SQL >/dev/null <<SQL
    -- add log file and set updated
    UPDATE gitmanager_courseupdate SET log=readfile('$logfile'),updated_time=CURRENT_TIMESTAMP,updated=1
      WHERE id=$update_id;
    -- mark all skipped (not updated, but older) to be updated (there shouldn't be any)
    UPDATE gitmanager_courseupdate SET log='skipped',updated_time=CURRENT_TIMESTAMP,updated=1
      WHERE request_time < '$request_time' AND course_repo_id=$repo_id AND updated=0;
    -- keep only 10 logs in the history
    DELETE FROM gitmanager_courseupdate
      WHERE request_time < '$request_time' AND course_repo_id=$repo_id
      ORDER BY request_time DESC
      LIMIT -1 OFFSET 10;
SQL
done

# Reload course configuration by restarting uwsgi processes
touch $CDIR
for f in /srv/grader/uwsgi-grader*.ini; do
    [ -e $f ] && touch $f
done
