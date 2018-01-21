from django.conf import settings
from django.conf.urls import include, url

import os

urlpatterns = []

if 'gitmanager' in settings.INSTALLED_APPS:
    import gitmanager.urls
    urlpatterns.append(url(r'^gitmanager/', include(gitmanager.urls)))

import access.urls
urlpatterns.append(url(r'^', include(access.urls)))

if settings.DEBUG:
    import staticfileserver.urls
    urlpatterns.append(url(r'^', include(staticfileserver.urls)))

os.umask(0o002)
