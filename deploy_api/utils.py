import logging
from functools import wraps

from django.conf import settings
from django.core.exceptions import (
    PermissionDenied,
)
from django.core.urlresolvers import reverse

from apluslms_file_transfer.server.auth import authenticate
from apluslms_file_transfer.server.django import prepare_decoder, convert_django_header

logger = logging.getLogger(__name__)

jwt_decode = prepare_decoder()


def course_manage_required(func):
    """
    Decorator for authenticating jwt token and checking whether a file of a course can be uploaded
    """

    @wraps(func)
    def wrapper(request, *args, **kwargs):

        headers = {convert_django_header(k): v for k, v in request.META.items()}

        course_name = kwargs.get('course_name', None)
        if course_name is None:
            raise PermissionDenied('No valid course name provided')

        auth = authenticate(jwt_decode, headers, course_name)

        kwargs['course_name'] = course_name
        kwargs['auth'] = auth

        return func(request, *args, **kwargs)

    return wrapper

# ----------------------------------------------------------------------------------------------------------------------
# Update index.yaml


def url_to_static(request, course_key, path):
    """ Creates an URL for a path in static files """
    return request.build_absolute_uri(
        '{}{}/{}'.format(settings.STATIC_URL, course_key, path))


def url_to_exercise(request, course_key, exercise_key):
    """ Creates an URL for an exercise"""
    return request.build_absolute_uri(
        reverse('exercise', args=[course_key, exercise_key]))


def update_static_url(request, course_key, data):
    """ Update static_content to url"""
    path = data.pop('static_content')
    if isinstance(path, dict):
        url = {
            lang: url_to_static(request, course_key, p)
            for lang, p in path.items()
        }
    else:
        url = url_to_static(request, course_key, path)

    return url


def update_course_index(request, index_data, course_key):
    """ Update course index """
    def children_recursion(parent):
        if "children" in parent:
            for o in [o for o in parent["children"] if "key" in o]:
                if 'config' in o and 'url' not in o:
                    o['url'] = url_to_exercise(request, course_key, o['key'])
                elif "static_content" in o:
                    o['url'] = update_static_url(request, course_key, o)
                children_recursion(o)

    if "modules" in index_data:
        for m in index_data["modules"]:
            children_recursion(m)

    return index_data








