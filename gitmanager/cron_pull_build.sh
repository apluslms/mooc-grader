#!/bin/bash

TRY_PYTHON=$1
key=$2
url=$3
branch=$4
echo "Processing key=$key url=$url branch=$branch python=$TRY_PYTHON"

if [ -z "$key" -o -z "$url" -o -z "$branch" ]; then
    echo "  Some arguments are missing, skipping..."
    exit 1
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
  cd $dir
  git fetch
  # Following trick might not be needed. It's supposed to ensure there is local branch per remote
  branchnow=`git branch`
  if [ "${branchnow#* }" != "$branch" ]; then
    git reset -q --hard
    git checkout -q $branch
  fi
  git reset -q --hard origin/$branch
  git submodule sync --recursive
  git submodule update --init --recursive
  git --no-pager log --pretty=format:"------------;Commit metadata;;Hash:;%H;Subject:;%s;Body:;%b;Committer:;%ai;%ae;Author:;%ci;%cn;%ce;------------;" -1 | tr ';' '\n'
else
  git clone -b $branch --recursive $url $dir
  cd $dir
fi

# Build course material.
if [ -e build.sh ]; then
  echo " ### Detected 'build.sh' executing it with bash. ###"
  /bin/bash build.sh
elif [ -e Makefile ] && grep -qsE '^SPHINXBUILD' Makefile && grep -qsE '^html:' Makefile; then
  echo " ### Detected sphinx Makefile. Running 'make html'. Add nop 'build.sh' to disable this! ###"
  make html
else
  echo " ### No build.sh or sphinx Makefile. Not building the course. ###"
fi
cd ../..

# Link to static.
static_dir=`python gitmanager/cron.py static $key`
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
