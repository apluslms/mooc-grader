#!/bin/bash
#
# Provides library for scala. Exercise can add it to classpath.
#   scala_compile.sh --cp .:/usr/local/scala/libs/scalatest_2.11-2.1.7.jar
#
URL=https://oss.sonatype.org/content/groups/public/org/scalatest/scalatest_2.12/3.0.4/scalatest_2.12-3.0.4.jar
URL2=https://oss.sonatype.org/content/groups/public/org/scalactic/scalactic_2.12/3.0.4/scalactic_2.12-3.0.4.jar
NAME=${URL##*/}
NAME2=${URL2##*/}

apt-get -qy install libxtst6

mkdir -p /usr/local/scala/libs
cd /usr/local/scala/libs/
if [ ! -f $NAME ]
then
	wget --no-check-certificate -O $NAME $URL
fi
if [ ! -f $NAME2 ]
then
	wget --no-check-certificate -O $NAME2 $URL2
fi
