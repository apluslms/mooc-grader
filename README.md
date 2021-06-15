# mooc-grader

This grading service accepts anonymous submissions for grading via HTTP.
The submissions are graded either synchronously in the web application or
asynchronously in containers (usually in Kubernetes, though it is possible
to run Docker containers in the web server for a small number of submissions).
The results are delivered to the calling system and the grader does not keep
any record other than service logs. The grader is designed to serve exercises
for the A+ learning system. If the number of submissions is large, we recommend
setting up a Kubernetes cluster for the grader.

The grader is implemented on Django 2.2 (`grader/settings.py`). The application
is tested on Python 3.7 and newer versions, but Python 3.5+ should also work.

The grader can be run stand alone without the full stack to test graders in
the local system environment. The grader is designed to be extended for
different courses and exercise types. Course and exercise configuration is in
`courses` directory where further documentation and examples are available.

## Installing for development

You may run the app with Docker without installing the whole software stack locally.
It is easy to get started with the aplus-manual course:
[apluslms/aplus-manual](https://github.com/apluslms/aplus-manual).
The Docker image is intended for local development and testing, not production:
[apluslms/run-mooc-grader](https://github.com/apluslms/run-mooc-grader).

> Ubuntu 20.04

### 1. Clone the software

General requirements

    sudo apt-get install git libjpeg-dev
    sudo apt-get install libxml2-dev libxslt-dev zlib1g-dev

Install software

    git clone https://github.com/apluslms/mooc-grader.git
    mkdir mooc-grader/uploads

### 2. Python requirements

    sudo apt-get install python3 python3-dev python3-pip python3-venv


Then, create virtual environment with grader requirements.

    python3 -m venv venv
    source venv/bin/activate
    pip install wheel
    pip install -r mooc-grader/requirements.txt

### 3. Testing grader application

Run the Django app locally:

    cd mooc-grader
    python manage.py runserver

The exercise configuration and grading of individual
exercises can be tested from the command line.

    python manage.py exercises
    python manage.py grade

### 4. For configuring courses and exercises, see

[courses/README.md](courses/README.md)

## Installing the full stack

> Ubuntu 20.04

### 0. User account

On a server, one can install mooc-grader for a specific grader
user account.

    sudo adduser --system --group \
      --shell /bin/bash --home /srv/grader \
      --gecos "A-plus mooc-gracer service" \
      grader
    su - grader

**Then follow the "Installing for development" and continue from here.**

### 1. Web server configuration

#### Create temporary directory for sockets

    echo "d /run/grader 0750 grader www-data - -" | \
      sudo tee /etc/tmpfiles.d/grader.conf > /dev/null
    sudo systemd-tmpfiles --create


Install uwsgi to run WSGI processes. The **mooc-grader directory
and user must** be set in the configuration files.

#### uWSGI with systemd (Ubuntu >= 15.04)

    source ~/venv/bin/activate
    pip install uwsgi
    cp ~/mooc-grader/doc/etc-uwsgi-grader.ini ~/grader-uwsgi.ini
    sudo cp ~grader/mooc-grader/doc/etc-systemd-system-uwsgi.service /etc/systemd/system/grader-uwsgi.service
    # EDIT ~/grader-uwsgi.ini
    # EDIT /etc/systemd/system/grader-uwsgi.service, set the correct uwsgi path to ExecStart

Operate the workers:

    # as root
    systemctl status grader-uwsgi
    systemctl start grader-uwsgi
    systemctl enable grader-uwsgi  # start on boot
    # Graceful application reload
    touch ~grader/grader-uwsgi.ini

#### nginx

    apt-get install nginx
    sed -e "s/__HOSTNAME__/$(hostname)/g" \
      ~grader/mooc-grader/doc/etc-nginx-sites-available-grader > \
      /etc/nginx/sites-available/$(hostname).conf
    ln -s ../sites-available/$(hostname).conf /etc/nginx/sites-enabled/$(hostname).conf
    # Edit /etc/nginx/sites-available/$(hostname).conf if necessary
    # Check nginx config validity
    nginx -t
    systemctl reload nginx

#### apache2

    apt-get install apache2 libapache2-mod-uwsgi
    # Configure based on doc/etc-apache2-sites-available-grader
    a2enmod headers

## 2. Django application settings for deployment

When deploying, overwrite necessary configurations in `mooc-grader/grader/local_settings.py`.
