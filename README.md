This grading service accepts anonymous submissions for grading via HTTP. The
grading can be done synchronously or asynchronously using a submission queue.
The results are delivered to the calling system and the grader does not keep
any record other than service logs. The grader is designed to serve exercises
for the A+ learning system. A farm of individual grading servers can be setup
to handle large amount of submissions.

The grader is implemented on Django 1.9 (`grader/settings.py`). The application 
is tested on both Python 2.7 and 3.4. 

The grader can be run stand alone without the full stack to test graders in
the local system environment. The grader is designed to be extended for
different courses and exercise types. Course and exercise configuration is in
`courses` directory where further documentation and examples are available.

Installing for development
==========================

> 6/2014 - Ubuntu 12.04.4

1. ### Clone the software

	General requirements

		sudo apt-get install git libjpeg-dev
		sudo apt-get install libxml2-dev libxslt-dev zlib1g-dev

	Install software

		git clone https://github.com/Aalto-LeTech/mooc-grader.git
		mkdir mooc-grader/uploads

2. ### Python requirements (2.7 should work too)

		sudo apt-get install python3 python3-dev python3-pip

	Make sure pip and virtualenv are installed.

		sudo pip3 install virtualenv

	Then, create virtual environment with grader requirements.

		virtualenv -p python3 venv
		source venv/bin/activate
		pip install -r mooc-grader/requirements.txt

3. ### Testing grader application

		cd mooc-grader
		python manage.py runserver

	In addition, the exercise configuration and grading of individual
	exercises can be tested from command line.

		python manage.py exercises
		python manage.py grade

4. ### For configuring courses and exercises, see

	`courses/README.md`

Installing the full stack
=========================

> 6/2014 - Ubuntu 12.04.4

0. ### User account

	On a server, one can install mooc-grader for a specific grader
	user account.

		sudo useradd -mUrd /srv/grader grader
		cd

	Then follow the "Installing for development" and continue from here.

1. ### Web server configuration

	Install uwsgi to run WSGI processes. The **mooc-grader directory
	and user must** be set in the configuration files.

	#### uWSGI with Upstart (Ubuntu < 15.04)

		source venv/bin/activate
		pip install uwsgi
		sudo mkdir -p /etc/uwsgi
		sudo mkdir -p /var/log/uwsgi
		sudo cp doc/etc-uwsgi-grader.ini /etc/uwsgi/grader.ini
		sudo cp doc/etc-init-uwsgi.conf /etc/init/uwsgi.conf
		# EDIT /etc/uwsgi/grader.ini
		# EDIT /etc/init/uwsgi.conf
		sudo touch /var/log/uwsgi/grader.log
		sudo chown -R [shell-username]:users /etc/uwsgi /var/log/uwsgi

	NOTE that the ownership of the log file is required for graceful
	restarts using touch. Operate the workers using:

		sudo status uwsgi
		sudo start uwsgi
		# Graceful application reload
		touch /etc/uwsgi/grader.ini

	#### uWSGI with systemd (Ubuntu >= 15.04)

		source venv/bin/activate
		pip install uwsgi
		sudo mkdir -p /etc/uwsgi
		sudo mkdir -p /var/log/uwsgi
		sudo cp doc/etc-uwsgi-grader.ini /etc/uwsgi/grader.ini
		sudo cp doc/etc-systemd-system-uwsgi.service /etc/systemd/system/uwsgi.service
		# EDIT /etc/uwsgi/grader.ini
		# EDIT /etc/systemd/system/uwsgi.service, set the correct uwsgi path to ExecStart
		sudo touch /var/log/uwsgi/grader.log
		sudo chown -R [shell-username]:users /etc/uwsgi /var/log/uwsgi

	Operate the workers:

		systemctl status uwsgi
		sudo systemctl start uwsgi
		sudo systemctl enable uwsgi  # start on boot
		# Graceful application reload
		touch /etc/uwsgi/grader.ini

	#### nginx

		sudo apt-get install nginx
		# Configure based on doc/etc-nginx-sites-available-grader

	#### apache2

		sudo apt-get install apache2 libapache2-mod-uwsgi
		# Configure based on doc/etc-apache2-sites-available-grader

2. ### Django application settings for deployment

	When deploying, overwrite necessary configurations in `mooc-grader/grader/local_settings.py`.

	If `gitmanager` is used to update course content via Git operations, enable it in
	`local_settings.py`:

		ADD_APPS = (
			'gitmanager',
		)

	`gitmanager` uses a database. If `sqlite3` is used (in `settings.py`), it must be installed:

		sudo apt-get install sqlite3 libsqlite3-dev

	Django must install the database schema for the `gitmanager` (Python virtual environment must be activated):

		python manage.py migrate

	The `gitmanager` requires a crontab for the root account:

		sudo crontab -u root doc/gitmanager-root-crontab
