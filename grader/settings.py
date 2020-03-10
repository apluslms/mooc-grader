####
# Default settings for MOOC Grader project.
# You should create local_settings.py and override any settings there.
# You can copy local_settings.example.py and start from there.
##
from os.path import abspath, dirname, join
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
##########################################################################


INSTALLED_APPS = (
    # 'django.contrib.admin',
    # 'django.contrib.auth',
    # 'django.contrib.contenttypes',
    # 'django.contrib.sessions',
    # 'django.contrib.messages',
    'staticfileserver', # override for runserver command, thus this needs to be before django contrib one
    'django.contrib.staticfiles',
    'access',
)
ADD_APPS = (
    #'gitmanager',
)

MIDDLEWARE_CLASSES = (
    # 'django.middleware.security.SecurityMiddleware',
    # 'django.contrib.sessions.middleware.SessionMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    # 'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(BASE_DIR, 'local_templates'),
            join(BASE_DIR, 'templates'),
            join(BASE_DIR, 'courses'),
            join(BASE_DIR, 'exercises'),
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

# Database (override in local_settings.py)
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
##########################################################################
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': join(BASE_DIR, 'db.sqlite3'),
        # NOTE: Above setting can't be changed if girmanager is used.
        # cron.sh expects database to be in that file.
    }
}
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


# Task queue settings
##########################################################################
CONTAINER_SCRIPT = join(BASE_DIR, "scripts/docker-run.sh")

# HTTP
DEFAULT_EXPIRY_MINUTES = 15


# Course configuration path:
# Every directory under this directory is expected to be a course configuration
# FIXME: this option is currently just place holder and it's waiting for deprecation
# of course specific view_types. ps. those are currently imported by util.importer.import_named
# access/config.py contains hardcoded version of this value.
COURSES_PATH = join(BASE_DIR, 'courses')

# Exercise files submission path:
# Django process requires write access to this directory.
SUBMISSION_PATH = join(BASE_DIR, 'uploads')

# Personalized exercises and user files are kept here.
# Django process requires write access to this directory.
PERSONALIZED_CONTENT_PATH = join(BASE_DIR, 'exercises-meta')

# Enable personal directories for users, which can be used in personalized
# exercises to permanently store personal files with the
# grader.actions.store_user_files action. Personalized exercises can still be
# used even if this setting is False if the grading only uses the pregenerated
# exercise instance files. Enabling and using personal directories makes the
# grader stateful, which at least increases the amount of disk space used.
ENABLE_PERSONAL_DIRECTORIES = False

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
from os import environ
from r_django_essentials.conf import *

# get settings values from other sources
update_settings_with_file(__name__,
                          environ.get('GRADER_LOCAL_SETTINGS', 'local_settings'),
                          quiet='GRADER_LOCAL_SETTINGS' in environ)
update_settings_from_module(__name__, 'settings_local', quiet=True) # Compatibility with older releases
update_settings_from_environment(__name__, 'DJANGO_') # FIXME: deprecated
update_settings_from_environment(__name__, 'GRADER_')
update_secret_from_file(__name__, environ.get('GRADER_SECRET_KEY_FILE', 'secret_key'))
update_secret_from_file(__name__, environ.get('GRADER_AJAX_KEY_FILE', 'ajax_key'), setting='AJAX_KEY')
assert AJAX_KEY, "Secure random string is required in AJAX_KEY"

# update INSTALLED_APPS
INSTALLED_APPS = INSTALLED_APPS + ADD_APPS

# Drop x-frame policy when debugging
if DEBUG:
    MIDDLEWARE_CLASSES = [c for c in MIDDLEWARE_CLASSES if "XFrameOptionsMiddleware" not in c]

# update template loaders for production
use_cache_template_loader_in_production(__name__)
