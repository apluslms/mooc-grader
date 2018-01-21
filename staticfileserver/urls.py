from django.conf import settings
from django.conf.urls.static import static

from .views import serve

urlpatterns = static(settings.STATIC_URL, view=serve)
