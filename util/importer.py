'''
Tools to import modules by name.
'''
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys

from django.conf import settings


def import_path(path: str, module_name: str = "", force_reload = False):
    """Imports a module from a specified path"""
    if not force_reload and module_name and module_name in sys.modules:
        return sys.modules[module_name]

    spec = spec_from_file_location(module_name, path)

    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    if module_name:
        sys.modules[module_name] = module

    return module


def import_path_attribute(dotted_path: str, root: str = ".", force_reload=False):
    """Imports an attribute (e.g. class or function) from a module from a specified path"""
    dotted_module_path, attribute = dotted_path.rsplit(".", 1)
    full_path = Path(root, dotted_module_path.replace(".", "/") + ".py")

    module = import_path(full_path, dotted_module_path, force_reload)

    return getattr(module, attribute)


def import_named(course, path):
    if path.startswith('.'):
        return import_path_attribute(course['key'] + path, settings.COURSES_PATH, True)
    return import_path_attribute(path, ".")
