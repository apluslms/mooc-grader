from django.shortcuts import render
from django.http.response import HttpResponse, JsonResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from django.utils import translation
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.conf import settings
import copy
import os
import json

from access.config import DEFAULT_LANG, ConfigError, config
from util import export
from util.files import (
    clean_submission_dir,
    read_and_remove_submission_meta,
    write_submission_meta,
)
from util.http import post_data
from util.importer import import_named
from util.monitored_dict import MonitoredDict
from util.personalized import read_generated_exercise_file
from util.templates import template_to_str


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
        "manager": 'gitmanager' in settings.INSTALLED_APPS,
    })


def course(request, course_key):
    '''
    Signals that the course is ready to be graded and lists available exercises.
    '''
    (course, exercises) = config.exercises(course_key)
    if course is None:
        raise Http404()
    if request.is_ajax():
        return JsonResponse({
            "ready": True,
            "course_name": course["name"],
            "exercises": _filter_fields(exercises, ["key", "title"]),
        })
    render_context = {
        'course': course,
        'exercises': exercises,
        'plus_config_url': request.build_absolute_uri(reverse(
            'aplus-json', args=[course['key']])),
    }
    if "gitmanager" in settings.INSTALLED_APPS:
        render_context["build_log_url"] = request.build_absolute_uri(reverse("build-log-json", args=(course_key, )))
    return render(request, 'access/course.html', render_context)


def exercise(request, course_key, exercise_key):
    '''
    Presents the exercise and accepts answers to it.
    '''
    post_url = request.GET.get('post_url', None)
    lang = request.POST.get('__grader_lang', None) or request.GET.get('lang', None)
    (course, exercise, lang) = _get_course_exercise_lang(course_key, exercise_key, lang)

    # Try to call the configured view.
    try:
        return import_named(course, exercise['view_type'])(request, course, exercise, post_url)
    except ConfigError as error:
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
    (course, exercise, lang) = _get_course_exercise_lang(course_key, exercise_key, lang)

    if course is None or exercise is None or 'ajax_type' not in exercise:
        raise Http404()

    # jQuery does not send "requested with" on cross domain requests
    #if not request.is_ajax():
    #    return HttpResponse('Method not allowed', status=405)

    response = import_named(course, exercise['ajax_type'])(request, course, exercise)

    # No need to control domain as valid submission_url is required to submit.
    response['Access-Control-Allow-Origin'] = '*'
    return response


def exercise_model(request, course_key, exercise_key, parameter=None):
    '''
    Presents a model answer for an exercise.
    '''
    lang = request.GET.get('lang', None)
    (course, exercise, lang) = _get_course_exercise_lang(course_key, exercise_key, lang)

    response = None
    path = None

    if 'model_files' in exercise:
        def find_name(paths, name):
            models = [(path,path.split('/')[-1]) for path in paths]
            for path,name in models:
                if name == parameter:
                    return path
            return None
        path = find_name(exercise['model_files'], parameter)

    if path:
        try:
            with open(os.path.join(course['dir'], path)) as f:
                content = f.read()
        except FileNotFoundError:
            pass
        else:
            response = HttpResponse(content, content_type='text/plain')
    else:
        try:
            response = import_named(course, exercise['view_type'] + "Model")(request, course, exercise, parameter)
        except ImportError:
            pass

    if response:
        return response
    else:
        raise Http404()


def exercise_template(request, course_key, exercise_key, parameter=None):
    '''
    Presents the exercise template.
    '''
    lang = request.GET.get('lang', None)
    (course, exercise, lang) = _get_course_exercise_lang(course_key, exercise_key, lang)

    response = None
    path = None

    if 'template_files' in exercise:
        def find_name(paths, name):
            templates = [(path,path.split('/')[-1]) for path in paths]
            for path,name in templates:
                if name == parameter:
                    return path
            return None
        path = find_name(exercise['template_files'], parameter)

    if path:
        with open(os.path.join(course['dir'], path)) as f:
            content = f.read()
        response = HttpResponse(content, content_type='text/plain')
    else:
        try:
            response = import_named(course, exercise['view_type'] + "Template")(request, course, exercise, parameter)
        except ImportError:
            pass

    if response:
        return response
    else:
        raise Http404()


def aplus_json(request, course_key):
    '''
    Delivers the configuration as JSON for A+.
    '''
    course = config.course_entry(course_key)
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

    def children_recursion(parent):
        if not "children" in parent:
            return []
        result = []
        for o in [o for o in parent["children"] if "key" in o]:
            of = _type_dict(o, course.get("exercise_types", {}))
            if "config" in of:
                _, exercise = config.exercise_entry(course["key"], str(of["key"]), '_root')
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

    if "gitmanager" in settings.INSTALLED_APPS:
        data["build_log_url"] = request.build_absolute_uri(reverse("build-log-json", args=(course_key, )))
    return JsonResponse(data)


def test_result(request):
    '''
    Accepts and displays a result from a test submission.
    '''
    file_path = os.path.join(settings.SUBMISSION_PATH, 'test-result')

    if request.method == 'POST':
        vals = request.POST.copy()
        vals['time'] = str(timezone.now())
        with open(file_path, 'w') as f:
            f.write(json.dumps(vals))
        return JsonResponse({ "success": True })

    result = None
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            result = f.read()
    return HttpResponse(result or 'No test result received yet.')


def generated_exercise_file(request, course_key, exercise_key, exercise_instance, filename):
    '''
    Delivers a generated file of the exercise instance.
    '''
    # Fetch the corresponding exercise entry from the config.
    (course, exercise) = config.exercise_entry(course_key, exercise_key)
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
    (course, exercise) = config.exercise_entry(course_key, exercise_key, lang=lang_code)
    if course is None or exercise is None:
        raise Http404()
    if not lang_code:
        lang_code = course.get('lang', DEFAULT_LANG)
    translation.activate(lang_code)
    return (course, exercise, lang_code)


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
