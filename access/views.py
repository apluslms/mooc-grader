import copy
import json
from json.decoder import JSONDecodeError
import logging
import os
from pathlib import Path
from shutil import rmtree
from tarfile import TarFile
from typing import List

from aplus_auth.payload import Permission
from django.shortcuts import render
from django.http.response import HttpResponse, JsonResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from django.utils import translation
from django.urls import reverse
from django.conf import settings
from django.views import View

from access.config import DEFAULT_LANG, EXTERNAL_EXERCISES_DIR, EXTERNAL_FILES_DIR, ConfigError, config
from util import export
from util.files import (
    read_and_remove_submission_meta,
    write_submission_meta,
)
from util.http import post_data
from util.importer import import_named
from util.login_required import login_required
from util.monitored_dict import MonitoredDict
from util.personalized import read_generated_exercise_file
from util.templates import template_to_str


LOGGER = logging.getLogger('main')


def index(request):
    '''
    Signals that the grader is ready and lists available courses.
    '''
    courses = config.courses()
    if request.is_ajax():
        return JsonResponse({
            "ready": True,
            "courses": _filter_fields(courses, ["key", "name"])
        })
    return render(request, 'access/ready.html', {
        "courses": courses,
    })


@login_required
def configure(request):
    '''
    Configure a course.
    '''
    if request.method != "POST":
        return HttpResponse(status=405)

    if "exercises" not in request.POST or "course_id" not in request.POST:
        return HttpResponse("Missing exercises or course_id", status=400)

    course_id = request.POST["course_id"]
    try:
        exercises = json.loads(request.POST["exercises"])
        course_id_int = int(course_id)
    except (JSONDecodeError, ValueError) as e:
        LOGGER.exception("Invalid exercises or course_id field")
        return HttpResponse(f"Invalid exercises or course_id field: {e}", status=500)

    if not request.auth.permissions.instances.has(Permission.WRITE, id=course_id_int):
        return HttpResponse(status=401)

    course_path = Path(settings.COURSES_PATH, course_id)
    if course_path.exists():
        try:
            rmtree(course_path)
        except OSError:
            LOGGER.exception("Failed to remove old stored course files")
            return HttpResponse("Failed to remove old stored course files", status=500)

    course_files_path = course_path / EXTERNAL_FILES_DIR
    course_exercises_path = course_path / EXTERNAL_EXERCISES_DIR
    course_files_path.mkdir(parents=True, exist_ok=True)
    course_exercises_path.mkdir(parents=True, exist_ok=True)

    if "files" in request.FILES:
        tar_file = request.FILES["files"].file
        tarh = TarFile(fileobj=tar_file)
        tarh.extractall(course_files_path)

    course_config = {
        "name": course_id,
        "exercises": [ex["key"] for ex in exercises],
        "exercise_loader": "access.config._ext_exercise_loader",
    }

    with open(course_path / "index.json", "w") as f:
        json.dump(course_config, f)

    for info in exercises:
        with open(course_exercises_path / (info["key"] + ".json"), "w") as f:
            json.dump(info["config"], f)

    defaults = {}
    for info in exercises:
        of = info["spec"]
        if info.get("config"):
            of["config"] = info["key"] + ".json"
            course, exercise = config.exercise_entry(course_id, info["key"], "_root")
            of = export.exercise(request, course, exercise, of)
        defaults[of["key"]] = of

    return JsonResponse(defaults)


@login_required
def course(request, course_key):
    '''
    Signals that the course is ready to be graded and lists available exercises.
    '''
    error = None
    try:
        (course, exercises) = config.exercises(course_key)
    except ConfigError as e:
        course = exercises = None
        error = str(e)
    else:
        if course is None:
            raise Http404()
    if request.is_ajax():
        if error:
            data = {
                "ready": False,
                "errors": [error],
            }
        else:
            data = {
                "ready": True,
                "course_name": course["name"],
                "exercises": _filter_fields(exercises, ["key", "title"]),
            }
        return JsonResponse(data)
    render_context = {
        'course': course,
        'exercises': exercises,
        'plus_config_url': request.build_absolute_uri(reverse(
            'aplus-json', args=[course_key])),
        'error': error,
    }
    return render(request, 'access/course.html', render_context)


@login_required
def exercise(request, course_key, exercise_key):
    '''
    Presents the exercise and accepts answers to it.
    '''
    post_url = request.GET.get('post_url', None)
    lang = request.POST.get('__grader_lang', None) or request.GET.get('lang', None)
    course = exercise = None

    try:
        (course, exercise, lang) = _get_course_exercise_lang(course_key, exercise_key, lang)
        # Try to call the configured view.
        return import_named(course, exercise['view_type'])(request, course, exercise, post_url)
    except (ConfigError, ImportError) as error:
        return render(request, 'access/exercise_config_error.html', {
            'course': course,
            'exercise': exercise,
            'config_error': str(error),
            'result': {
                'error': True,
            },
        })


def exercise_ajax(request, course_key, exercise_key):
    '''
    Receives an AJAX request for an exercise.
    '''
    lang = request.GET.get('lang', None)

    try:
        (course, exercise, lang) = _get_course_exercise_lang(course_key, exercise_key, lang)

        if course is None or exercise is None or 'ajax_type' not in exercise:
            raise Http404()

        # jQuery does not send "requested with" on cross domain requests
        #if not request.is_ajax():
        #    return HttpResponse('Method not allowed', status=405)

        response = import_named(course, exercise['ajax_type'])(request, course, exercise)
    except (ConfigError, ImportError) as e:
        return _error_response(exc=e)

    # No need to control domain as valid submission_url is required to submit.
    response['Access-Control-Allow-Origin'] = '*'
    return response


@login_required
def exercise_model(request, course_key, exercise_key, parameter=None):
    '''
    Presents a model answer for an exercise.
    '''
    lang = request.GET.get('lang', None)
    try:
        (course, exercise, lang) = _get_course_exercise_lang(course_key, exercise_key, lang)
    except ConfigError as e:
        return HttpResponse(str(e), content_type='text/plain')

    response = None
    path = None

    if 'model_files' in exercise and parameter:
        path = _find_file(exercise['model_files'], parameter)

    if path:
        try:
            with open(os.path.join(course['dir'], path)) as f:
                content = f.read()
        except FileNotFoundError as error:
            raise Http404(f'Model file "{parameter}" missing') from error
        except OSError as error:
            LOGGER.error(f'Error in reading the exercise model file "{path}".', exc_info=error)
            content = str(error)
        response = HttpResponse(content, content_type='text/plain')
    else:
        try:
            response = import_named(course, exercise['view_type'] + "Model")(request, course, exercise, parameter)
        except ImportError:
            pass
        except ConfigError as e:
            response = HttpResponse(str(e), content_type='text/plain')

    if response:
        return response
    else:
        raise Http404()


@login_required
def exercise_template(request, course_key, exercise_key, parameter=None):
    '''
    Presents the exercise template.
    '''
    lang = request.GET.get('lang', None)
    try:
        (course, exercise, lang) = _get_course_exercise_lang(course_key, exercise_key, lang)
    except ConfigError as e:
        return HttpResponse(str(e), content_type='text/plain')

    response = None
    path = None

    if 'template_files' in exercise and parameter:
        path = _find_file(exercise['template_files'], parameter)

    if path:
        try:
            with open(os.path.join(course['dir'], path)) as f:
                content = f.read()
        except FileNotFoundError as error:
            raise Http404(f'Template file "{parameter}" missing') from error
        except OSError as error:
            LOGGER.error(f'Error in reading the exercise template file "{path}".', exc_info=error)
            content = str(error)
        response = HttpResponse(content, content_type='text/plain')
    else:
        try:
            response = import_named(course, exercise['view_type'] + "Template")(request, course, exercise, parameter)
        except ImportError:
            pass
        except ConfigError as e:
            response = HttpResponse(str(e), content_type='text/plain')

    if response:
        return response
    else:
        raise Http404()


@login_required
def aplus_json(request, course_key):
    '''
    Delivers the configuration as JSON for A+.
    '''
    try:
        course = config.course_entry(course_key)
    except ConfigError as e:
        return _error_response(exc=e)
    if course is None:
        raise Http404()
    data = _copy_fields(course, [
        "archive_time",
        "assistants",
        "categories",
        "contact",
        "content_numbering",
        "course_description",
        "course_footer",
        "description",
        "end",
        "enrollment_audience",
        "enrollment_end",
        "enrollment_start",
        "head_urls",
        "index_mode",
        "lang",
        "lifesupport_time",
        "module_numbering",
        "name",
        "numerate_ignoring_modules",
        "start",
        "view_content_to",
    ])
    if "language" in course:
        data["lang"] = course["language"]

    errors = []

    def children_recursion(parent):
        if not "children" in parent:
            return []
        result = []
        for o in [o for o in parent["children"] if "key" in o]:
            of = _type_dict(o, course.get("exercise_types", {}))
            if "config" in of:
                try:
                    _, exercise = config.exercise_entry(course["key"], str(of["key"]), '_root')
                except ConfigError as e:
                    errors.append(str(e))
                    continue
                of = export.exercise(request, course, exercise, of)
            elif "static_content" in of:
                of = export.chapter(request, course, of)
            of["children"] = children_recursion(o)
            result.append(of)
        return result

    modules = []
    if "modules" in course:
        for m in course["modules"]:
            mf = _type_dict(m, course.get("module_types", {}))
            mf["children"] = children_recursion(m)
            modules.append(mf)
    data["modules"] = modules
    if errors:
        data["errors"] = errors

    return JsonResponse(data)


class LoginView(View):
    def get(self, request):
        response = render(request, 'access/login.html')
        response.delete_cookie("AuthToken")
        return response

    def post(self, request):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return HttpResponse("Invalid token", status=401)
        else:
            response = HttpResponse()
            response.set_cookie("AuthToken", str(request.auth))
            return response


def test_result(request):
    '''
    Accepts and displays a result from a test submission.
    '''
    file_path = os.path.join(settings.SUBMISSION_PATH, 'test-result')

    if request.method == 'POST':
        vals = request.POST.copy()
        vals['time'] = str(timezone.now())
        try:
            with open(file_path, 'w') as f:
                f.write(json.dumps(vals))
        except OSError as e:
            return _error_response(exc=e)
        return JsonResponse({ "success": True })

    result = None
    try:
        with open(file_path, 'r') as f:
            result = f.read()
    except FileNotFoundError:
        pass
    except OSError as e:
        return _error_response(exc=e)
    return HttpResponse(result or 'No test result received yet.')


def generated_exercise_file(request, course_key, exercise_key, exercise_instance, filename):
    '''
    Delivers a generated file of the exercise instance.
    '''
    # Fetch the corresponding exercise entry from the config.
    try:
        (course, exercise) = config.exercise_entry(course_key, exercise_key)
    except ConfigError as e:
        return HttpResponse(str(e), content_type='text/plain')
    if course is None or exercise is None:
        raise Http404()
    if "generated_files" in exercise:
        import magic
        for gen_file_conf in exercise["generated_files"]:
            if gen_file_conf["file"] == filename:
                if gen_file_conf.get("allow_download", False):
                    file_content = read_generated_exercise_file(course, exercise,
                                                                exercise_instance, filename)
                    response = HttpResponse(file_content,
                                            content_type=magic.from_buffer(file_content, mime=True))
                    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
                    return response
                else:
                    # hide file existence with 404
                    raise Http404()
    raise Http404()


def _get_course_exercise_lang(course_key, exercise_key, lang_code):
    # Keep only "en" from "en-gb" if the long language format is used.
    if lang_code:
        lang_code = lang_code[:2]
    (course, exercise) = config.exercise_entry(course_key, exercise_key, lang=lang_code)
    if course is None or exercise is None:
        raise Http404()
    if not lang_code:
        lang_code = course.get('lang', DEFAULT_LANG)
    translation.activate(lang_code)
    return (course, exercise, lang_code)


def _find_file(filepaths, name):
    file_paths_and_names = [(path, path.split('/')[-1]) for path in filepaths]
    for path, filename in file_paths_and_names:
        if filename == name:
            return path
    return None


def _filter_fields(dict_list, pick_fields):
    '''
    Filters picked fields from a list of dictionaries.

    @type dict_list: C{list}
    @param dict_list: a list of dictionaries
    @type pick_fields: C{list}
    @param pick_fields: a list of field names
    @rtype: C{list}
    @return: a list of filtered dictionaries
    '''
    result = []
    for entry in dict_list:
        new_entry = {}
        for name in pick_fields:
            new_entry[name] = entry[name]
        result.append(new_entry)
    return result


def _copy_fields(dict_item, pick_fields):
    '''
    Copies picked fields from a dictionary.

    @type dict_item: C{dict}
    @param dict_item: a dictionary
    @type pick_fields: C{list}
    @param pick_fields: a list of field names
    @rtype: C{dict}
    @return: a dictionary of picked fields
    '''
    result = {}
    for name in pick_fields:
        if name in dict_item:
            result[name] = copy.deepcopy(dict_item[name])
    return result

def _type_dict(dict_item, dict_types):
    '''
    Extends dictionary with a type reference.

    @type dict_item: C{dict}
    @param dict_item: a dictionary
    @type dict_types: C{dict}
    @param dict_types: a dictionary of type dictionaries
    @rtype: C{dict}
    @return: an extended dictionary
    '''
    base = {}
    if "type" in dict_item and dict_item["type"] in dict_types:
        base = copy.deepcopy(dict_types[dict_item["type"]])
    base.update(dict_item)
    if "type" in base:
        del base["type"]
    return base


def _error_response(errors: List[str] = None, exc: Exception = None):
    if exc:
        errors = [str(exc)]
    return JsonResponse({
        'success': False,
        'errors': errors,
    })


def container_post(request):
    '''
    Proxies the grading result from inside container to A+
    '''
    sid = request.POST.get("sid", None)
    if not sid:
        return HttpResponseForbidden("Missing sid")

    meta = read_and_remove_submission_meta(sid)
    if meta is None:
        return HttpResponseForbidden("Invalid sid")
    #clean_submission_dir(meta["dir"])


    data = {
        "points": int(request.POST.get("points", 0)),
        "max_points": int(request.POST.get("max_points", 1)),
    }
    for key in ["error", "grading_data"]:
        if key in request.POST:
            data[key] = request.POST[key]
    if "error" in data and data["error"].lower() in ("no", "false"):
        del data["error"]

    feedback = request.POST.get("feedback", "")
    # Fetch the corresponding exercise entry from the config.
    lang = meta["lang"]
    (course, exercise) = config.exercise_entry(meta["course_key"], meta["exercise_key"], lang=lang)
    if "feedback_template" in exercise:
        # replace the feedback with a rendered feedback template if the exercise is configured to do so
        # it is not feasible to support all of the old feedback template variables that runactions.py
        # used to have since the grading actions are not configured in the exercise YAML file anymore
        required_fields = { 'points', 'max_points', 'error', 'out' }
        result = MonitoredDict({
            "points": data["points"],
            "max_points": data["max_points"],
            "out": feedback,
            "error": data.get("error", False),
            "title": exercise.get("title", ""),
        })
        translation.activate(lang)
        feedback = template_to_str(course, exercise, None, exercise["feedback_template"], result=result)
        if result.accessed.isdisjoint(required_fields):
            alert = template_to_str(
                course, exercise, None,
                "access/feedback_template_did_not_use_result_alert.html")
            feedback = alert + feedback
        # Make unicode results ascii.
        feedback = feedback.encode("ascii", "xmlcharrefreplace")

    data["feedback"] = feedback

    if not post_data(meta["url"], data):
        write_submission_meta(sid, meta)
        return HttpResponse("Failed to deliver results", status=502)
    return HttpResponse("Ok")
