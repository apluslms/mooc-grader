from django.conf.urls import url
from deploy_api import views

urlpatterns = [
    url(r'^(?P<course_name>[\w-]+)/select-files$', views.files_select, name='files_select'),
    url(r'^(?P<course_name>[\w-]+)/upload-files$', views.files_upload, name='files_upload'),
    url(r'^(?P<course_name>[\w-]+)/publish-files$', views.files_publish, name='files_publish'),
    url(r'^(?P<course_name>[\w-]+)/delete$', views.course_delete, name='course_delete'),
    url(r'^(?P<course_name>[\w-]+)/files/(?P<file_path>.*)$', views.file_delete, name='file_delete'),
    url(r'^(?P<course_name>[\w-]+)/update-index-file$', views.course_index_update, name='course_index_update'),
]
