import os

from django.conf import settings
from django.urls import include, path


urlpatterns = []

if 'gitmanager' in settings.INSTALLED_APPS:
    import gitmanager.urls
    urlpatterns.append(path('gitmanager/', include(gitmanager.urls)))

import access.urls
urlpatterns.append(path('', include(access.urls)))

if settings.DEBUG:
    import staticfileserver.urls
    urlpatterns.append(path('', include(staticfileserver.urls)))

os.umask(0o002)
