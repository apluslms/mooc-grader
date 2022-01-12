from django.urls import path, register_converter

from access import views
from access.converters import BasenameConverter

register_converter(BasenameConverter, "basename")

urlpatterns = [
    path("", views.index, name='index'),
    path("configure", views.configure, name='configure'),
    path("test-result", views.test_result, name='test-result'),
    path("container-post", views.container_post, name='container-post'),
    path("ajax/<slug:course_key>/<slug:exercise_key>", views.exercise_ajax, name='ajax'),
    path(
        "model/<slug:course_key>/<slug:exercise_key>/<basename:parameter>",
        views.exercise_model,
        name='model',
    ),
    path(
        "exercise_template/<slug:course_key>/<slug:exercise_key>/<basename:parameter>",
        views.exercise_template,
        name='exercise_template',
    ),
    path(
        "generatedfile/<slug:course_key>/<slug:exercise_key>/<int:exercise_instance>/<basename:filename>",
        views.generated_exercise_file,
        name='generated-file',
    ),
    path("<slug:course_key>/", views.course, name='course'),
    path("<slug:course_key>/aplus-json", views.aplus_json, name='aplus-json'),
    path("<slug:course_key>/<slug:exercise_key>", views.exercise, name='exercise'),
    path("login", views.LoginView.as_view(), name="login"),
]
