FROM apluslms/service-base:django-1.19

# Set container related configuration via environment variables
ENV CONTAINER_TYPE="grader" \
    GRADER_LOCAL_SETTINGS="/srv/grader-cont-settings.py" \
    GRADER_SECRET_KEY_FILE="/local/grader/secret_key.py" \
    GRADER_AJAX_KEY_FILE="/local/grader/ajax_key.py" \
    grader_NO_DATABASE="true"

ARG TARGETPLATFORM

RUN : \
 && apt_install \
      apt-transport-https \
      jq \
      # temp
      gnupg curl \
      libmagic1 \
\
  # install docker-ce
 && if [ "$TARGETPLATFORM" = "linux/amd64" ] ; then ARCH=amd64 ; elif [ "$TARGETPLATFORM" = "linux/arm64" ] ; then ARCH=arm64 ; else exit 1 ; fi \
 && curl -LSs https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg >/dev/null 2>&1 \
 && echo "deb [arch=$ARCH signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian trixie stable" > /etc/apt/sources.list.d/docker.list \
 && apt_install docker-ce \
\
  # create user
 && adduser --system --no-create-home --disabled-password --gecos "MOOC-Grader webapp server,,," --home /srv/grader --ingroup nogroup grader \
 && mkdir /srv/grader && chown grader.nogroup /srv/grader \
 && git config --global --add safe.directory /srv/grader \
 && :

COPY docker/rootfs /
COPY . /srv/grader

RUN cd /srv/grader \
  # patch and prebuild .pyc files
 && patch -p1 < /srv/cors.patch \
 && python3 -m compileall -q . \
\
  # install requirements, remove the file, remove unrequired locales and tests
 && pip_install -r requirements.txt \
 && rm requirements.txt \
 && find /usr/local/lib/python* -type d -regex '.*/locale/[a-z_A-Z]+' -not -regex '.*/\(en\|fi\|sv\)' -print0 | xargs -0 rm -rf \
 && find /usr/local/lib/python* -type d -name 'tests' -print0 | xargs -0 rm -rf \
\
 && export \
    GRADER_SECRET_KEY="-" \
    GRADER_AJAX_KEY="-" \
 && python3 manage.py compilemessages 2>&1 \
\
  # default course link
 && mkdir -p /srv/grader/courses/ \
 && mkdir -p /srv/courses/default \
 && ln -s -T /srv/courses/default /srv/grader/courses/default \
 && chown -R grader.nogroup \
    /srv/courses \
    /srv/course_store \
    /srv/grader \
\
  # clean
 && rm -rf $GRADER_SECRET_KEY_FILE $GRADER_AJAX_KEY_FILE \
 && rm -rf /etc/init.d/ /tmp/* \
 && apt_purge \
      gnupg curl \
 && :


VOLUME /srv/courses/default
WORKDIR /srv/grader/
EXPOSE 8080
CMD [ "manage", "runserver", "0.0.0.0:8080" ]
