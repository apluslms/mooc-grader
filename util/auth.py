from functools import wraps
from typing import Callable, Union

from aplus_auth import settings as auth_settings
from aplus_auth.auth.django import login_required as login_required_base
from aplus_auth.payload import Permission
from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponse
from django.urls import reverse_lazy
from django.utils.text import format_lazy

ViewType = Callable[..., HttpResponse]
login_required: Callable[[ViewType], ViewType] = login_required_base(
    redirect_url=format_lazy('{}?{}', reverse_lazy('login'), 'referer={url}'),
)


def access_check(request, permission: Permission, course_key: Union[str,int]):
    """
    Raises PermissionDenied if no <permission> access, and ValueError if
    course_key couldn't be parsed as an integer.
    """
    if isinstance(course_key, str):
        try:
            course_key = int(course_key)
        except ValueError:
            raise ValueError("instance id is not an integer")

    if auth_settings().DISABLE_LOGIN_CHECKS:
        return True

    if not hasattr(request, "auth") or request.auth is None:
        return False

    # if the key is self signed and the permissions are empty, we assume it is
    # a 'master' key with access to everything
    has_empty_perms = next(iter(request.auth.permissions), None) is None
    if has_empty_perms and request.auth.iss == auth_settings().UID:
        return True

    if not request.auth.permissions.instances.has(permission, id=course_key):
        raise PermissionDenied(f"No access to instance {course_key}")

def access_read_check(request, course_key: Union[str,int]):
    """
    Raises PermissionDenied if no read access, and ValueError if
    course_key couldn't be parsed as an integer.
    """
    access_check(request, Permission.READ, course_key)

def access_write_check(request, course_key: Union[str,int]):
    """
    Raises PermissionDenied if no write access, and ValueError if
    course_key couldn't be parsed as an integer.
    """
    access_check(request, Permission.WRITE, course_key)


def access_check_if_number(request, permission: Permission, course_key: Union[str,int]):
    """Checks access if course_key is a number, otherwise does nothing"""
    try:
        access_check(request, permission, course_key)
    except ValueError:
        # cant check permissions if course key isn't a number
        pass

def access_read_check_if_number(request, course_key: Union[str,int]):
    """Checks read access if course_key is a number, otherwise does nothing"""
    access_check_if_number(request, Permission.READ, course_key)

def access_write_check_if_number(request, course_key: Union[str,int]):
    """Checks write access if course_key is a number, otherwise does nothing"""
    access_check_if_number(request, Permission.WRITE, course_key)


def has_access(request, permission: Permission, course_key: Union[str,int], *, default: bool = True):
    """Returns whether user has <permission> access to the course <course_key>"""
    try:
        access_check(request, permission, course_key)
    except ValueError:
        return default
    except PermissionDenied:
        return False

    return True

def has_read_access(request, course_key: Union[str,int], *, default: bool = True):
    """Returns whether user has read access to the course <course_key>"""
    return has_access(request, Permission.READ, course_key, default=default)

def has_write_access(request, course_key: Union[str,int], *, default: bool = True):
    """Returns whether user has write access to the course <course_key>"""
    return has_access(request, Permission.WRITE, course_key, default=default)


def _instance_access_required(permission: Permission, view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, course_key, **kwargs) -> HttpResponse:
        access_check_if_number(request, permission, course_key)
        return view_func(request, *args, course_key, **kwargs)

    return wrapper

def instance_read_access_required(view_func):
    """
    A decorator for a view function.

    1. Checks that user is logged in.
    2. checks read access if course_key is a number, otherwise does nothing.
    """
    return _instance_access_required(Permission.READ, view_func)


def instance_write_access_required(view_func):
    """
    A decorator for a view function.

    1. Checks that user is logged in.
    2. checks write access if course_key is a number, otherwise does nothing.
    """
    return _instance_access_required(Permission.WRITE, view_func)