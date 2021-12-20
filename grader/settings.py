####
# Default settings for MOOC Grader project.
# You should create local_settings.py and override any settings there.
# You can copy local_settings.example.py and start from there.
##
from os.path import abspath, dirname, join
from typing import Dict, Optional
BASE_DIR = dirname(dirname(abspath(__file__)))


# Base options, commonly overridden in local_settings.py
##########################################################################
DEBUG = False
SECRET_KEY = None
AJAX_KEY = None
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
#SERVER_EMAIL = 'root@'
ALLOWED_HOSTS = ["*"]
# Local nessaging library settings, see [aplus-auth](https://pypi.org/project/aplus-auth/) for explanations
APLUS_AUTH_LOCAL = {
    "PRIVATE_KEY": None,
    "PUBLIC_KEY": None,
    "REMOTE_AUTHENTICATOR_KEY": None,
    "REMOTE_AUTHENTICATOR_URL": None, # probably "https://<A+ domain>/api/v2/get-token/"
    #"TRUSTED_KEYS": [...],
    #"TRUSTING_REMOTES": [...],
    #"DISABLE_LOGIN_CHECKS": False,
    #"DISABLE_JWT_SIGNING": False,
}

# modify this if there are very large courses to be configured through /configure
# it is the maximum number of bytes allowed in a request body (doesn't count files)
# https://docs.djangoproject.com/en/3.2/ref/settings/#data-upload-max-memory-size
# Other applications in the pipeline, like NGINX and kubernetes, may have their
# own limits that need to be modified separately
DATA_UPLOAD_MAX_MEMORY_SIZE = 10*1024*1024 # 10MB
##########################################################################

# Messaging library
APLUS_AUTH: Dict[str, Optional[str]] = {
    "AUTH_CLASS": "access.auth.Authentication",
}

INSTALLED_APPS = (
    # 'django.contrib.admin',
    # 'django.contrib.auth',
    # 'django.contrib.contenttypes',
    # 'django.contrib.sessions',
    # 'django.contrib.messages',
    'staticfileserver', # override for runserver command, thus this needs to be before django contrib one
    'django.contrib.staticfiles',
    'access',
    'aplus_auth',
)

MIDDLEWARE = [
    # 'django.middleware.security.SecurityMiddleware',
    # 'django.contrib.sessions.middleware.SessionMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'aplus_auth.auth.django.AuthenticationMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(BASE_DIR, 'local_templates'),
            join(BASE_DIR, 'templates'),
            join(BASE_DIR, 'courses'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                #"django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                #'django.template.context_processors.request',
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                #"django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

#FILE_UPLOAD_HANDLERS = (
#    "django.core.files.uploadhandler.MemoryFileUploadHandler",
#    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
#)

ROOT_URLCONF = 'grader.urls'
# LOGIN_REDIRECT_URL = "/"
# LOGIN_ERROR_URL = "/login/"
WSGI_APPLICATION = 'grader.wsgi.application'

##########################################################################

# Cache (override in local_settings.py)
# https://docs.djangoproject.com/en/1.10/topics/cache
##########################################################################
#CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#        'TIMEOUT': None,
#    }
#}
#SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
##########################################################################

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = (
    join(BASE_DIR, 'locale'),
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATICFILES_DIRS = (
    join(BASE_DIR, 'assets'),
)
STATIC_URL = '/static/'
STATIC_URL_HOST_INJECT = ''
STATIC_ROOT = join(BASE_DIR, 'static')

#MEDIA_URL = '/media/'
#MEDIA_ROOT = join(BASE_DIR, 'media')


# Course configuration path:
# Every directory under this directory is expected to be a course configuration
COURSES_PATH = join(BASE_DIR, 'courses')
# This is required if external configuring is used and, in that case,
# this must be on the same device as COURSES_PATH
COURSE_STORE = join(BASE_DIR, 'course_store')

# Exercise files submission path:
# Django process requires write access to this directory.
SUBMISSION_PATH = join(BASE_DIR, 'uploads')

# Personalized exercises and user files are kept here.
# Django process requires write access to this directory.
PERSONALIZED_CONTENT_PATH = join(BASE_DIR, 'exercises-meta')


# Task queue settings
##########################################################################
RUNNER_MODULE = join(BASE_DIR, "scripts/docker-run.py")
# settings passed to the runner module. See the runner module file for more
# information.
HOST_BASE_DIR = BASE_DIR
RUNNER_MODULE_SETTINGS = {
  "network": "bridge",
  "mounts": {
    COURSES_PATH: COURSES_PATH.replace(BASE_DIR, HOST_BASE_DIR),
    SUBMISSION_PATH: SUBMISSION_PATH.replace(BASE_DIR, HOST_BASE_DIR),
    PERSONALIZED_CONTENT_PATH: PERSONALIZED_CONTENT_PATH.replace(BASE_DIR, HOST_BASE_DIR),
  },
}

# If running in a docker container, set this to the docker network used by the container
# e.g. the default for a docker-compose project is '<dir>_default', where <dir> is
# the directory the docker-compose.yml file is in
# 'bridge' is the default when running docker directly without compose
CONTAINER_NETWORK = "bridge"


# HTTP
DEFAULT_EXPIRY_MINUTES = 15


# Logging
# https://docs.djangoproject.com/en/1.7/topics/logging/
##########################################################################
LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'verbose': {
      'format': '[%(asctime)s: %(levelname)s/%(module)s] %(message)s'
    },
  },
  'handlers': {
    'console': {
      'level': 'DEBUG',
      'class': 'logging.StreamHandler',
      'stream': 'ext://sys.stdout',
      'formatter': 'verbose',
    },
    'email': {
      'level': 'ERROR',
      'class': 'django.utils.log.AdminEmailHandler',
    },
  },
  'loggers': {
    '': {
      'level': 'DEBUG',
      'handlers': ['console']
    },
    'main': {
      'level': 'DEBUG',
      'handlers': ['email'],
      'propagate': True
    },
  },
}





###############################################################################
from pathlib import Path
from os import environ
from r_django_essentials.conf import *

# get settings values from other sources
update_settings_with_file(__name__,
                          environ.get('GRADER_LOCAL_SETTINGS', 'local_settings'),
                          quiet='GRADER_LOCAL_SETTINGS' in environ)
update_settings_from_module(__name__, 'settings_local', quiet=True) # Compatibility with older releases

# Load settings from environment variables starting with ENV_SETTINGS_PREFIX (default GRADER_)
ENV_SETTINGS_PREFIX = environ.get('ENV_SETTINGS_PREFIX', 'GRADER_')
update_settings_from_environment(__name__, ENV_SETTINGS_PREFIX)

update_secret_from_file(__name__, environ.get('GRADER_SECRET_KEY_FILE', 'secret_key'))
update_secret_from_file(__name__, environ.get('GRADER_AJAX_KEY_FILE', 'ajax_key'), setting='AJAX_KEY')
assert AJAX_KEY, "Secure random string is required in AJAX_KEY"

APLUS_AUTH.update(APLUS_AUTH_LOCAL)

Path(COURSE_STORE).mkdir(parents=True, exist_ok=True)

# Drop x-frame policy when debugging
if DEBUG:
    MIDDLEWARE = [c for c in MIDDLEWARE if "XFrameOptionsMiddleware" not in c]

# update template loaders for production
use_cache_template_loader_in_production(__name__)
