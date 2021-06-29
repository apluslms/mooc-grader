'''
Tools to import modules by name.
'''
import importlib
import sys
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

from django.conf import settings

def import_path_attribute(dotted_path, root = "."):
    """Imports an attribute (e.g. class or function) from a module from a specified path"""
    module_name, attribute = dotted_path.rsplit(".", 1)
    full_path = Path(root, module_name.replace(".", "/") + ".py")

    spec = spec_from_file_location(module_name, full_path)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return getattr(module, attribute)

def import_named(course, path):
    if path.startswith('.'):
        return import_path_attribute(course['key'] + path, settings.COURSES_PATH)
    return import_path_attribute(path, ".")
