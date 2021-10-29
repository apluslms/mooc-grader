'''
The exercises and classes are configured in json/yaml.
Each directory inside courses/ holding an index.json/yaml is a course.
'''
import io
import json
from json.decoder import JSONDecodeError
import os
import re
import time
import logging
from typing import Any, Dict, Tuple

import yaml

from django.conf import settings
from django.template import loader as django_template_loader
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError

from util.dict import get_rst_as_html
from util.files import read_meta
from util.importer import import_named
from util.static import symbolic_link


META = "apps.meta"
INDEX = "index"
DEFAULT_LANG = "en"

LOGGER = logging.getLogger('main')


EXTERNAL_FILES_DIR = "files"
EXTERNAL_EXERCISES_DIR = "exercises"

def _ext_exercise_loader(course_root, exercise_key, course_dir):
    '''
    Loader for exercises that were received from /configure.

    @type course_root: C{dict}
    @param course_root: a course root dictionary
    @type exercise_key: C{str}
    @param exercise_key: an exercise key
    @type course_dir: C{str}
    @param course_dir: a path to the course root directory
    @rtype: C{str}, C{dict}
    @return: exercise config file path, modified time and data dict
    '''
    config_file = os.path.join(course_dir, EXTERNAL_EXERCISES_DIR, exercise_key) + ".json"
    try:
        with open(config_file) as f:
            data = json.load(f)
    except (OSError, JSONDecodeError) as e:
        raise ConfigError(f"Failed to load json: {e}")

    ndata = {}
    for lang, d in data.items():
        if "container" in d:
            if "mount" in d["container"]:
                d["container"]["mount"] = os.path.join(EXTERNAL_FILES_DIR, d["container"]["mount"])
            if "mounts" in d["container"]:
                for k,v in d["container"]["mounts"]:
                    d["container"]["mounts"][k] = os.path.join(EXTERNAL_FILES_DIR, v)

        for key, value in d.items():
            key = key+"|i18n"
            if key not in ndata:
                ndata[key] = {}
            ndata[key][lang] = value

    return config_file, os.path.getmtime(config_file), ndata


class ConfigError(Exception):
    '''
    Configuration errors.
    '''
    def __init__(self, value, error=None):
        self.value = value
        self.error = error

    def __str__(self):
        if self.error is not None:
            return "%s: %s" % (repr(self.value), repr(self.error))
        return repr(self.value)


class ConfigParser:
    '''
    Provides configuration data parsed and automatically updated on change.
    '''
    FORMATS = {
        'json': json.load,
        'yaml': yaml.safe_load
    }
    PROCESSOR_TAG_REGEX = re.compile(r'^(.+)\|(\w+)$')
    TAG_PROCESSOR_DICT = {
        'i18n': lambda root, parent, value, **kwargs: value.get(kwargs['lang']),
        'rst': lambda root, parent, value, **kwargs: get_rst_as_html(value),
    }

    def __init__(self):
        '''
        The constructor.
        '''
        self._courses = {}
        self._dir_mtime = 0


    def courses(self):
        '''
        Gets all courses.

        @rtype: C{list}
        @return: course configurations
        '''

        # Find all courses if exercises directory is modified.
        t = os.path.getmtime(settings.COURSES_PATH)
        if self._dir_mtime < t:
            self._courses.clear()
            self._dir_mtime = t
            LOGGER.debug('Recreating course list.')
            for item in os.listdir(settings.COURSES_PATH):
                try:
                    self._course_root(item)
                except ConfigError:
                    LOGGER.exception("Failed to load course: %s", item)
                    continue

        # Pick course data into list.
        course_list = []
        for c in self._courses.values():
            course_list.append(c["data"])
        return course_list


    def course_entry(self, course_key):
        '''
        Gets a course entry.

        @type course_key: C{str}
        @param course_key: a course key
        @rtype: C{dict}
        @return: course configuration or None
        '''
        root = self._course_root(course_key)
        return None if root is None else root["data"]


    def exercises(self, course_key):
        '''
        Gets course exercises for a course key.

        @type course_key: C{str}
        @param course_key: a course key
        @rtype: C{tuple}
        @return: course configuration or None, listed exercise configurations or None
        '''
        course_root = self._course_root(course_key)
        if course_root is None:
            return (None, None)

        # Pick exercise data into list.
        exercise_list = []
        for exercise_key in course_root["data"]["exercises"]:
            _, exercise = self.exercise_entry(course_root, exercise_key)
            if exercise is None:
                raise ConfigError('Invalid exercise key "%s" listed in "%s"'
                    % (exercise_key, course_root["file"]))
            exercise_list.append(exercise)
        return (course_root["data"], exercise_list)


    def exercise_entry(self, course, exercise_key, lang=None):
        '''
        Gets course and exercise entries for their keys.

        @type course: C{str|dict}
        @param course: a course key or root dict
        @type exercise_key: C{str}
        @param exercise_key: an exercise key
        @rtype: C{tuple}
        @return: course configuration or None, exercise configuration or None
        '''
        if isinstance(course, dict):
          course_root, course_key = course, course['data']['key']
        else:
          course_root, course_key = self._course_root(course), course

        if course_root is None:
            return None, None
        if exercise_key not in course_root["data"]["exercises"]:
            return course_root["data"], None

        exercise_root = self._exercise_root(course_root, exercise_key)
        if not exercise_root or "data" not in exercise_root or not exercise_root["data"]:
            return course_root["data"], None

        if lang == '_root':
            return course_root["data"], exercise_root["data"]

        # Try to find version for requested or configured language.
        for lang in (lang, course_root["lang"]):
            if lang in exercise_root["data"]:
                exercise = exercise_root["data"][lang]
                exercise["lang"] = lang
                return course_root["data"], exercise

        # Fallback to any existing language version.
        return course_root["data"], list(exercise_root["data"].values())[0]


    def _course_root(self, course_key):
        '''
        Gets course dictionary root (meta and data).

        @type course_key: C{str}
        @param course_key: a course key
        @rtype: C{dict}
        @return: course root or None
        '''

        # Try cached version.
        if course_key in self._courses:
            course_root = self._courses[course_key]
            try:
                if course_root["mtime"] >= os.path.getmtime(course_root["file"]):
                    return course_root
            except OSError:
                pass

        LOGGER.debug('Loading course "%s"' % (course_key))
        meta = read_meta(os.path.join(settings.COURSES_PATH, course_key, META))
        try:
            f = self._get_config(os.path.join(self._conf_dir(settings.COURSES_PATH, course_key, meta), INDEX))
        except ConfigError:
            return None

        t = os.path.getmtime(f)
        data = self._parse(f)
        if data is None:
            raise ConfigError('Failed to parse configuration file "%s"' % (f))
        elif not isinstance(data, dict):
            raise ConfigError(f'The configuration data is invalid. It must be a dictionary. File "{f}"')

        self._check_fields(f, data, ["name"])
        data["key"] = course_key
        data["mtime"] = t
        data["dir"] = self._conf_dir(settings.COURSES_PATH, course_key, {})

        if "static_url" not in data:
            data["static_url"] = "{}{}{}/".format(
                settings.STATIC_URL_HOST_INJECT,
                settings.STATIC_URL,
                course_key
            )

        if "modules" in data:
            keys = []
            config = {}
            def recurse_exercises(parent):
                if "children" in parent:
                    for exercise_vars in parent["children"]:
                        if "key" in exercise_vars:
                            exercise_key = str(exercise_vars["key"])
                            cfg = None
                            if "config" in exercise_vars:
                                cfg = exercise_vars["config"]
                            elif "type" in exercise_vars and "exercise_types" in data \
                                    and exercise_vars["type"] in data["exercise_types"] \
                                    and "config" in data["exercise_types"][exercise_vars["type"]]:
                                cfg = data["exercise_types"][exercise_vars["type"]]["config"]
                            if cfg:
                                keys.append(exercise_key)
                                config[exercise_key] = cfg
                        recurse_exercises(exercise_vars)
            for module in data["modules"]:
                recurse_exercises(module)
            data["exercises"] = keys
            data["config_files"] = config

        # Enable course configurable ecercise_loader function.
        exercise_loader = self._default_exercise_loader
        if "exercise_loader" in data:
            exercise_loader = import_named(data, data["exercise_loader"])

        self._courses[course_key] = course_root = {
            "meta": meta,
            "file": f,
            "mtime": t,
            "ptime": time.time(),
            "data": data,
            "lang": self._default_lang(data),
            "exercise_loader": exercise_loader,
            "exercises": {}
        }
        symbolic_link(settings.COURSES_PATH, data)
        return course_root


    def _default_lang(self, data):
        l = data.get('language')
        if type(l) == list:
            data['lang'] = l[0]
        elif l == str:
            data['lang'] = l
        return data.get('lang', DEFAULT_LANG)


    def _exercise_root(self, course_root, exercise_key):
        '''
        Gets exercise dictionary root (meta and data).

        @type course_root: C{dict}
        @param course_root: a course root dictionary
        @type exercise_key: C{str}
        @param exercise_key: an exercise key
        @rtype: C{dict}
        @return: exercise root or None
        '''

        include_file_timestamp = 0
        # Try cached version.
        if exercise_key in course_root["exercises"]:
            exercise_root = course_root["exercises"][exercise_key]
            course_dir = self._conf_dir(settings.COURSES_PATH, course_root["data"]["key"], course_root["meta"])
            include_ok, include_file_timestamp = self._check_include_file_timestamps(
                exercise_root,
                course_dir,
            )
            try:
                if (exercise_root["mtime"] >= os.path.getmtime(exercise_root["file"])
                        and include_ok):
                    return exercise_root
            except OSError:
                pass

        LOGGER.debug('Loading exercise "%s/%s"', course_root["data"]["key"], exercise_key)
        file_name = exercise_key
        if "config_files" in course_root["data"]:
            file_name = course_root["data"]["config_files"].get(exercise_key, exercise_key)
        if file_name.startswith("/"):
            f, t, data = course_root["exercise_loader"](
                course_root,
                file_name[1:],
                self._conf_dir(settings.COURSES_PATH, course_root["data"]["key"], {})
            )
        else:
            f, t, data = course_root["exercise_loader"](
                course_root,
                file_name,
                self._conf_dir(settings.COURSES_PATH, course_root["data"]["key"], course_root["meta"])
            )
        if not data:
            return None

        # Save the latest modification time of the exercise in the cache.
        # If there is an included base template, its modification time may be later.
        t = max(t, include_file_timestamp)

        # Process key modifiers and create language versions of the data.
        data = self._process_exercise_data(course_root, data)
        for version in data.values():
            self._check_fields(f, version, ["title", "view_type"])
            version["key"] = exercise_key
            version["mtime"] = t

        course_root["exercises"][exercise_key] = exercise_root = {
            "file": f,
            "mtime": t,
            "ptime": time.time(),
            "data": data
        }
        return exercise_root


    def _check_fields(self, file_name, data, field_names):
        '''
        Verifies that a given dict contains a set of keys.

        @type file_name: C{str}
        @param file_name: a file name for targeted error message
        @type data: C{dict}
        @param data: a configuration entry
        @type field_names: C{tuple}
        @param field_names: required field names
        '''
        for name in field_names:
            if name not in data:
                raise ConfigError('Required field "%s" missing from "%s"' % (name, file_name))


    def _conf_dir(self, directory, course_key, meta):
        '''
        Gets configuration directory for the course.

        @type directory: C{str}
        @param directory: courses directory
        @type course_key: C{str}
        @param course_key: course key (directory name)
        @type meta: C{dict}
        @param meta: course meta data
        @rtype: C{str}
        @return: path to the course config directory
        '''
        if 'grader_config' in meta:
            return os.path.join(directory, course_key, meta['grader_config'])
        return os.path.join(directory, course_key)


    def _get_config(self, path):
        '''
        Returns the full path to the config file identified by a path.

        @type path: C{str}
        @param path: a path to a config file, possibly without a suffix
        @rtype: C{str}
        @return: the full path to the corresponding config file
        @raises ConfigError: if multiple rivalling configs or none exist
        '''

        # Check for complete path.
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1]
            if len(ext) > 0 and ext[1:] in self.FORMATS:
                return path

        # Try supported format extensions.
        config_file = None
        if os.path.isdir(os.path.dirname(path)):
            for ext in self.FORMATS.keys():
                f = "%s.%s" % (path, ext)
                if os.path.isfile(f):
                    if config_file != None:
                        raise ConfigError('Multiple config files for "%s"' % (path))
                    config_file = f
        if not config_file:
            raise ConfigError('No supported config at "%s"' % (path))
        return config_file


    def _parse(self, path, loader=None):
        '''
        Parses a dict from a file.

        @type path: C{str}
        @param path: a path to a file
        @type loader: C{function}
        @param loader: a configuration file stream parser
        @rtype: C{dict}
        @return: an object representing the configuration file or None
        '''
        if not loader:
            try:
                loader = self.FORMATS[os.path.splitext(path)[1][1:]]
            except:
                raise ConfigError('Unsupported format "%s"' % (path))
        data = None
        with open(path) as f:
            try:
                data = loader(f)
            except (ValueError, yaml.YAMLError) as e:
                raise ConfigError("Configuration error in %s" % (path), e)
        return data


    def _check_include_file_timestamps(self, exercise_root: Dict[str, Any], course_dir: str) -> Tuple[bool, int]:
        """Check the exercise modification time against the modification timestamps
        of the included configuration templates.

        Included configuration templates are set in the data["include] field
        (if they are used).

        @param exercise_root: root dict of the exercise configuration
        @param course_dir: file path to the course
        @return: 2-tuple (boolean, int) True if the exercise is up-to-date
            (not older than the latest modification in included files), and
            the latest included file modification timestamp
        """
        max_include_timestamp = 0
        for data in exercise_root["data"].values():
            for include_data in data.get("include", []):
                include_file = self._get_config(os.path.join(course_dir, include_data["file"]))
                try:
                    include_timestamp = os.path.getmtime(include_file)
                    if include_timestamp > max_include_timestamp:
                        max_include_timestamp = include_timestamp
                except OSError:
                    return False, 0
        return exercise_root["mtime"] >= max_include_timestamp, max_include_timestamp


    def _include(self, data, target_file, course_dir):
        '''
        Includes the config files defined in data["include"] into data.

        @type data: C{dict}
        @param data: target dict to which new data is included
        @type target_file: C{str}
        @param target_file: path to the include target, for error messages only
        @type course_dir: C{str}
        @param course_dir: a path to the course root directory
        @rtype: C{dict}
        @return: updated data
        '''
        return_data = data.copy()
        include_data_list = data.get("include")
        if not isinstance(include_data_list, list):
            raise ConfigError(
                f'The value of the "include" field in the file "{target_file}" should be a list of dictionaries.',
            )

        for include_data in include_data_list:
            try:
                self._check_fields(target_file, include_data, ("file",))

                include_file = self._get_config(os.path.join(course_dir, include_data["file"]))
                loader = self.FORMATS[os.path.splitext(include_file)[1][1:]]

                if "template_context" in include_data:
                    # Load new data from rendered include file string
                    render_context = include_data["template_context"]
                    template_name = os.path.join(course_dir, include_file)
                    template_name = template_name[len(settings.COURSES_PATH)+1:] # FIXME: XXX: NOTE: TODO: Fix this hack
                    rendered = django_template_loader.render_to_string(
                                template_name,
                                render_context
                            )
                    new_data = loader(io.StringIO(rendered))
                else:
                    # Load new data directly from the include file
                    with open(include_file, 'r') as f:
                        new_data = loader(f)
            except (OSError, KeyError, ValueError, yaml.YAMLError, TemplateDoesNotExist, TemplateSyntaxError) as e:
                raise ConfigError(
                    f'Error in parsing the config file to be included into "{target_file}".', error=e,
                ) from e

            if not new_data:
                raise ConfigError(f'Included config file is empty: "{target_file}"')
            if not isinstance(new_data, dict):
                raise ConfigError(f'Included config is not of type dict: "{target_file}"')

            if include_data.get('force', False):
                return_data.update(new_data)
            else:
                for new_key, new_value in new_data.items():
                    if new_key not in return_data:
                        return_data[new_key] = new_value
                    else:
                        raise ConfigError(
                            "Key {0!r} with value {1!r} already exists in config file {2!r}, cannot overwrite with key {0!r} with value {3!r} from config file {4!r}, unless 'force' option of the 'include' key is set to True."
                            .format(
                                new_key,
                                return_data[new_key],
                                target_file,
                                new_value,
                                include_file))
        return return_data


    def _default_exercise_loader(self, course_root, exercise_key, course_dir):
        '''
        Default loader to find and parse file.

        @type course_root: C{dict}
        @param course_root: a course root dictionary
        @type exercise_key: C{str}
        @param exercise_key: an exercise key
        @type course_dir: C{str}
        @param course_dir: a path to the course root directory
        @rtype: C{str}, C{dict}
        @return: exercise config file path, modified time and data dict
        '''
        config_file = self._get_config(os.path.join(course_dir, exercise_key))
        data = self._parse(config_file)
        if "include" in data:
            data = self._include(data, config_file, course_dir)
        return config_file, os.path.getmtime(config_file), data


    def _process_exercise_data(self, course_root, data):
        '''
        Processes a data dictionary according to embedded processor flags
        and creates a data dict version for each language intercepted.

        @type course_root: C{dict}
        @param course_root: a course root dictionary
        @type data: C{dict}
        @param data: a config data dictionary to process (in-place)
        '''
        default_lang = course_root['lang']
        lang_keys = []
        tags_processed = []

        def recursion(n, lang, collect_lang=False):
            t = type(n)
            if t == dict:
                d = {}
                for k in sorted(n.keys(), key=lambda x: (len(x), x)):
                    v = n[k]
                    m = self.PROCESSOR_TAG_REGEX.match(k)
                    while m:
                        k, tag = m.groups()
                        tags_processed.append(tag)
                        if collect_lang and tag == 'i18n' and type(v) == dict:
                            lang_keys.extend(v.keys())
                        if tag not in self.TAG_PROCESSOR_DICT:
                            raise ConfigError('Unsupported processor tag "%s"' % (tag))
                        v = self.TAG_PROCESSOR_DICT[tag](d, n, v, lang=lang)
                        m = self.PROCESSOR_TAG_REGEX.match(k)
                    d[k] = recursion(v, lang, collect_lang)
                return d
            elif t == list:
                return [recursion(v, lang, collect_lang) for v in n]
            else:
                return n

        default = recursion(data, default_lang, True)
        root = { default_lang: default }
        for lang in (set(lang_keys) - set([default_lang])):
            root[lang] = recursion(data, lang)

        LOGGER.debug('Processed %d tags.', len(tags_processed))
        return root


# An object that holds on to the latest exercise configuration.
config = ConfigParser()

# We are probably developing a course if only single course is detected. Pre-read configuration in the case.
if len(next(os.walk(settings.COURSES_PATH))[1]) == 1:
    LOGGER.info('Only single course detected. Pre-reading course configuration.')
    config.courses()
