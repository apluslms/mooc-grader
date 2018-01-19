#!/bin/bash
#
# Provides library for scala. Exercise can add it to classpath.
#   scala_compile.sh --cp .:/usr/local/scala/libs/scalatest_2.11-2.1.7.jar:/usr/local/scala/libs/scalamock-core_2.11-3.1.2.jar:/usr/local/scala/libs/scalamock-scalatest-support_2.11-3.1.2.jar
#
URL=http://central.maven.org/maven2/org/scalamock/scalamock_2.12/4.0.0/scalamock_2.12-4.0.0.jar
NAME=${URL##*/}

mkdir -p /usr/local/scala/libs
cd /usr/local/scala/libs/
if [ ! -f $NAME ]
then
	wget --no-check-certificate -O $NAME $URL
fi
