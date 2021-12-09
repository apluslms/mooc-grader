'''
Views configurable for usual asynchronous exercises that receive data
and queue the grading task. The `grader.tasks` module will grade the
task in time following the exercise configuration and respond with a
separate HTTP post to the received submission URL. Typically the
submitted data is stored in a submission directory.

Functions take arguments:

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type post_url: C{str}
    @param post_url: the exercise post URL
    @rtype: C{django.http.response.HttpResponse}
    @return: a response

'''
import logging
import copy
import os
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.utils import translation

from util.files import SubmissionDir, write_submission_meta
from util.http import not_modified_since, not_modified_response, cache_headers
from util.importer import import_path
from util.personalized import select_generated_exercise_instance
from util.shell import invoke
from util.templates import render_configured_template, render_template, \
    template_to_str
from .auth import make_hash, get_uid
from ..config import ConfigError


LOGGER = logging.getLogger('main')


runner_module = import_path(settings.RUNNER_MODULE)
if not hasattr(runner_module, "run"):
    raise AttributeError(f"settings.RUNNER_MODULE ({settings.RUNNER_MODULE}) does not have a run function")
runner_func = runner_module.run
if not callable(runner_func):
    raise AttributeError(f"run attribute in settings.RUNNER_MODULE ({settings.RUNNER_MODULE}) is not callable")


def acceptPost(request, course, exercise, post_url):
    '''
    Presents a template and accepts post value for grading queue.
    '''
    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    fields = copy.deepcopy(exercise.get("fields", []))
    if request.method == "POST":

        # Parse submitted values.
        miss = False
        for entry in fields:
            entry["value"] = request.POST.get(entry["name"], "").strip()
            if "required" in entry and entry["required"] and not entry["value"]:
                entry["missing"] = True
                miss = True
        if miss:
            result = { "fields": fields, "rejected": True }
        else:

            # Store submitted values.
            sdir = SubmissionDir(course, exercise)
            for entry in fields:
                sdir.write_file(entry["name"], entry["value"])
            return _acceptSubmission(request, course, exercise, post_url, sdir)
    else:
        result = { "fields": fields }

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url,
            'access/accept_post_default.html', result
        ),
        request,
        exercise
    )


def acceptFiles(request, course, exercise, post_url):
    '''
    Presents a template and accepts files for grading queue.
    '''
    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    result = None

    # Receive post.
    if request.method == "POST" and "files" in exercise:

        # Confirm that all required files were submitted.
        files_submitted = [] # exercise["files"] entries for the files that were really submitted
        for entry in exercise["files"]:
            # by default, all fields are required
            required = ("required" not in entry or entry["required"])
            if entry["field"] not in request.FILES:
                if required:
                    result = { "rejected": True, "missing_files": True }
                    break
            else:
                files_submitted.append(entry)

        if result is None:
            if "required_number_of_files" in exercise and \
                    exercise["required_number_of_files"] > len(files_submitted):
                result = { "rejected": True, "missing_files": True }
            else:
                # Store submitted files.
                sdir = SubmissionDir(course, exercise)
                for entry in files_submitted:
                    sdir.save_file(entry["name"], request.FILES[entry["field"]])
                return _acceptSubmission(request, course, exercise, post_url, sdir)

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url,
            "access/accept_files_default.html", result
        ),
        request,
        exercise
    )


def acceptGitAddress(request, course, exercise, post_url):
    '''
    Presents a template and accepts Git URL for grading.
    '''
    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    result = None

    # Receive post.
    if request.method == "POST" and "git" in request.POST and request.POST["git"].strip():
        source = request.POST["git"]

        # Safe gitlab addresses.
        if "require_gitlab" in exercise:
            if not source.startswith("git@%s:" % (exercise["require_gitlab"])):
                url_start = "https://%s/" % (exercise["require_gitlab"])
                if source.startswith(url_start):
                    url_start_len = len(url_start)
                    url_parts = source[url_start_len:].split("/")
                    if len(url_parts) > 1:
                        source = "git@%s:%s/%s" % (exercise["require_gitlab"], url_parts[-2], url_parts[-1])
                        if not source.endswith(".git"):
                            source += ".git"
                    else:
                        result = { "error": True, "invalid_address": True }
                else:
                    result = { "error": True, "invalid_address": True }

        # Try to prevent shell injections.
        elif "\"" in source or ";" in source:
            result = { "error": True, "invalid_address": True }

        if result is None:
            sdir = SubmissionDir(course, exercise)
            sdir.write_file("gitsource", source)
            return _acceptSubmission(request, course, exercise, post_url, sdir)

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url,
            "access/accept_git_default.html", result
        ),
        request,
        exercise
    )


def acceptGitUser(request, course, exercise, post_url):
    '''
    Presents a template and expects a user id to create Git URL for grading.
    '''
    auth_secret = "*AYVhD'b5,hKzf/6"

    if not "git_address" in exercise:
        raise  ConfigError("Missing \"git_address\" in exercise configuration.")

    user = get_uid(request)
    if request.method == "POST":
        if "user" in request.POST and "hash" in request.POST:
            user = request.POST["user"]
            if make_hash(auth_secret, user) != request.POST["hash"]:
                raise PermissionDenied()
        source = exercise["git_address"].replace("$USER", user)
        sdir = SubmissionDir(course, exercise)
        sdir.write_file("gitsource", source)
        return _acceptSubmission(request, course, exercise, post_url, sdir)

    return render_configured_template(request, course, exercise, post_url,
        "access/accept_git_user.html", {
            "user": user,
            "hash": make_hash(auth_secret, user)
        })


def acceptGeneralForm(request, course, exercise, post_url):
    '''
    Presents a template and accepts form containing any input types
    (text, file, etc) for grading queue.
    '''
    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    fields = copy.deepcopy(exercise.get("fields", []))
    result = None
    miss = False

    if request.method == "POST":
        # Parse submitted values.
        for entry in fields:
            entry["value"] = request.POST.get(entry["name"], "").strip()
            if "required" in entry and entry["required"] and not entry["value"]:
                entry["missing"] = True
                miss = True

        files_submitted = []
        if "files" in exercise:
            # Confirm that all required files were submitted.
            #files_submitted = [] # exercise["files"] entries for the files that were really submitted
            for entry in exercise["files"]:
                # by default, all fields are required
                required = ("required" not in entry or entry["required"])
                if entry["field"] not in request.FILES:
                    if required:
                        result = { "rejected": True, "missing_files": True }
                        break
                else:
                    files_submitted.append(entry)

        if miss:
            result = { "fields": fields, "rejected": True }
        elif result is None:
            # Store submitted values.
            sdir = SubmissionDir(course, exercise)
            for entry in fields:
                sdir.write_file(entry["name"], entry["value"])

            if "files" in exercise:
                if "required_number_of_files" in exercise and \
                        exercise["required_number_of_files"] > len(files_submitted):
                    result = { "rejected": True, "missing_files": True }
                else:
                    # Store submitted files.
                    for entry in files_submitted:
                        sdir.save_file(entry["name"], request.FILES[entry["field"]])
            return _acceptSubmission(request, course, exercise, post_url, sdir)

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url,
            "access/accept_general_default.html", result
        ),
        request,
        exercise
    )

def _requireContainer(exercise):
    c = exercise.get("container", {})
    a = exercise.get("actions", {})

    if c and a:
        LOGGER.warning("The `actions` parameter defined in your config.yaml is no longer used by the mooc-grader."
        "Therefore, you should remove it from your config.yaml and make use of the `container`.")
    if not c or not "image" in c or not "mount" in c or not "cmd" in c:
        raise ConfigError("Missing or invalid \"container\" in exercise configuration.")

    return c


def _saveForm(request, course, exercise, post_url, form):
    data,files = form.json_and_files(post_url)
    sdir = SubmissionDir(course, exercise)
    sdir.write_file("data.json", data)
    for name,uploaded in files.items():
        sdir.save_file(name, uploaded)
    return _acceptSubmission(request, course, exercise, post_url, sdir)


def _acceptSubmission(request, course, exercise, post_url, sdir: SubmissionDir):
    '''
    Queues the submission for grading.
    '''
    uids = get_uid(request)
    attempt = int(request.GET.get("ordinal_number", 1))

    if "submission_url" in request.GET:
        surl = request.GET["submission_url"]
        surl_missing = False
    else:
        LOGGER.warning("submission_url missing from a request")
        surl = f'http://{request.META["HOSTNAME"]}:{request.META["SERVER_PORT"]}{reverse("test-result")}'
        surl_missing = True

    # Order container for grading.
    c = _requireContainer(exercise)

    ro_mounts = c.get("mounts", {}).copy()
    if not isinstance(ro_mounts, dict):
        raise ConfigError("'container'->'mounts' must be a <path on course>-<mount path> dictionary or omitted altogether")
    for k,v in ro_mounts.items():
        if not os.path.isabs(v):
            raise ConfigError(f"Mount path must be absolute: {v}")
        if any(v == p or v.startswith(p + "/") for p in ("/exercise", "/submission", "/personalized_exercise")):
            raise ConfigError("/exercise, /submission and /personalized_exercise are reserved mounts, you cannot mount to them in 'mounts'")
        if os.path.isabs(k) or os.path.normpath(k).startswith(".."):
            raise ConfigError(f"Mounted path on course must be a relative subpath: {k}")

    ro_mounts[c["mount"]] = "/exercise"

    ro_mounts = {
        os.path.join(settings.COURSES_PATH, course["key"], k): v
        for k,v in ro_mounts.items()
    }

    if len(set(ro_mounts.values())) != len(ro_mounts):
        raise ConfigError("Mount paths must be distinct")

    if exercise.get("personalized", False):
        personalized_dir = select_generated_exercise_instance(course, exercise, uids, attempt)
        ro_mounts[personalized_dir] = "/personalized_exercise"

    write_submission_meta(sdir.sid, {
        "url": surl,
        "dir": str(sdir.dir()),
        "course_key": course["key"],
        "exercise_key": exercise["key"],
        "lang": translation.get_language(),
    })
    return_code, out, err = runner_func(
        course=course,
        exercise=exercise,
        container_config=c,
        submission_id=sdir.sid,
        host_url=request.scheme + "://" + request.get_host(),
        readwrite_mounts={str(sdir.dir()): "/submission"},
        readonly_mounts=ro_mounts,
        image=c["image"],
        cmd=c["cmd"],
        settings=settings.RUNNER_MODULE_SETTINGS,
    )
    LOGGER.debug(f"Container order exit={return_code} out={out} err={err}")
    qlen = 1

    return render_template(request, course, exercise, post_url,
        "access/async_accepted.html", {
            "error": return_code != 0,
            "accepted": True,
            "wait": True,
            "missing_url": surl_missing,
            "queue": qlen
        })
