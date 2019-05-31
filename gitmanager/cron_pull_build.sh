#!/bin/bash
set -x
TRY_PYTHON=$1
key=$2
id=$3
url=$4
branch=$5
DOCKER_HOST_PATH=$6

echo "Processing key=$key id=$id url=$url branch=$branch python=$TRY_PYTHON host_path=$DOCKER_HOST_PATH"
export DOCKER_HOST_PATH=$DOCKER_HOST_PATH$key
if [ -z "$key" -o -z "$id" -o -z "$url" -o -z "$branch" ]; then
    echo "  Some arguments are missing, skipping..."
fi

if [ -d exercises ]; then
  CDIR=exercises
else
  CDIR=courses
fi

if [ -f $TRY_PYTHON ]; then
  source $TRY_PYTHON
fi

# Update from git origin and move to dir.
dir=$CDIR/$key
if [ -e $dir ]; then
  pushd $dir
  git fetch
  # Following trick might not be needed. It's supposed to ensure there is local branch per remote
  branchnow=`git branch`
  if [ "${branchnow#* }" != "$branch" ]; then
    git reset -q --hard
    git checkout -q $branch
  fi
  git reset -q --hard origin/$branch
  git submodule update --init --recursive
  git --no-pager log --pretty=format:"------------;Commit metadata;;Hash:;%H;Subject:;%s;Body:;%b;Committer:;%ai;%ae;Author:;%ci;%cn;%ce;------------;" -1 | tr ';' '\n'
else
  git clone -b $branch --recursive $url $dir
  pushd $dir
fi

# Build course material.

if [ -e roman.yml ] || [ -e course.yml ] || [ -e roman.yaml ] || [ -e course.yaml ]; then
    echo "### Detected normal roman YAML file, running roman directly"
    roman
else
    roman -f ../../legacy_roman.yml
fi
popd

# Link to static.
static_dir=`python3 gitmanager/cron.py static $key`
if [ "$static_dir" != "" ]; then
  echo "Link static dir $static_dir"
  cd static
  target="../$dir/$static_dir"
  if [ -e $key ]; then
    if [ "`readlink $key`" != "$target" ]; then
      rm $key
      ln -s $target $key
    fi
  else
    ln -s $target $key
  fi
  cd ..
fi
