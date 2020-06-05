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
import copy
import json
import logging
import os
import re
from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.utils import translation

from util.files import create_submission_dir, save_submitted_file, \
    clean_submission_dir, write_submission_file, write_submission_meta
from util.http import cached_view_type
from util.personalized import select_generated_exercise_instance, \
    user_personal_directory_path
from util.shell import invoke
from util.templates import render_configured_template, render_template
from .auth import make_hash, get_uid
from ..config import ConfigError, DIR


LOGGER = logging.getLogger('main')


def _parse_fields_and_files(exercise):
    fields = OrderedDict()

    for i, field in enumerate(exercise.get('fields', ())):
        try:
            name = field['name']
        except KeyError:
            raise ConfigError("Invalid field, missing name at index %d." % (i,))
        while name in fields:
            # NOTE: this is an ugly hack. The problem of duplicate names will
            # be fixed when yaml files are validated at the course compile time
            name += '_'

        ftype = field.get('type', None)
        if ftype is None:
            ftype = 'text' if 'rows' in field else 'string'
        if ftype not in ('file', 'number', 'integer', 'string', 'text'):
            raise ConfigError("Invalid field type '%s' for field '%s'." % (ftype, name))

        fields[name] = entry = {
            k: field[k] for k in (
                'title',
                'more',
                'required',
                'pattern',
                'rows',
                'filename',
                'accept',
            ) if k in field
        }
        entry['name'] = name
        entry['type'] = ftype

    for i, field in enumerate(exercise.get('files', ())):
        try:
            filename = field['name']
        except KeyError:
            raise ConfigError("Invalid file, missing name at index %d." % (i,))
        name = field.get('field', filename)
        entry = fields.setdefault(name, {})
        entry['name'] = name
        entry['type'] = 'file'
        entry['filename'] = filename
        for k in ('title', 'required', 'accept'):
            if k in field:
                entry[k] = field[k]

    seen_filenames = set()
    duplicate_filenames = []
    for name, field in fields.items():
        ftype = field['type']

        filename = field.setdefault('filename', name)
        if filename in seen_filenames:
            duplicate_filenames.append('(%s -> %s)' % (name, filename))
        else:
            seen_filenames.add(filename)

        if field.get('required', None) is None:
            field['required'] = ftype == 'file'

        pattern = field.get('pattern', None)
        if pattern is None:
            if ftype == 'number':
                pattern = r'[-+]?[0-9]*(\.[0-9]+)?([eE][-+]?[0-9]+)?'
            elif ftype == 'integer':
                pattern = r'[-+]?[0-9]*'
        field['pattern'] = pattern
        field['pattern_re'] = re.compile(r'^' + pattern + r'$') if pattern else None

        if ftype == 'file' and not field.get('accept', None):
            ext = field['filename'].rpartition('.')[2]
            if ext:
                field['accept'] = '.' + ext

    if not fields:
        raise ConfigError("No fields parsed from `fields` or `files`. Have you configured either?")
    if duplicate_filenames:
        raise ConfigError("Multiple fields point to the same filename: %s" % (', '.join(duplicate_filenames),))
    return tuple(fields.values())


def _parse_post_and_validate(request, fields):
    # gather result used by templates, non-empty means there are errors!
    result = {}
    # gather list of tuples (error, value), used like: zip(values, fields)
    values = []
    # gather list of tuples (filename, file object)
    files = []

    # Parse POST fields
    for field in fields:
        name = field['name']
        ftype = field['type']
        error = None
        if ftype == 'file':
            value = name in request.FILES
            if value:
                files.append((field['filename'], request.FILES[name]))
            elif field['required']:
                error = 'missing'
        else:
            value = request.POST.get(name, '').strip()
            if value:
                if ftype == 'number':
                    try:
                        value = float(value)
                    except ValueError:
                        error = 'invalid'
                elif ftype == 'integer':
                    try:
                        value = int(value)
                    except ValueError:
                        error = 'invalid'
                elif field['pattern'] and field['pattern_re'].match(value) is None:
                    error = 'invalid'
            elif field['required']:
                error = 'missing'
        values.append((error, value))
        if error:
            # error -> post should be rejected
            if ftype == 'file':
                result['missing_files'] = True
            else:
                result['invalid_fields'] = True

    return result, values, files


@cached_view_type
def acceptAsync(request, course, exercise, post_url, *, template=None):
    if template is None:
        template = 'access/accept_async_default.html'

    if '__fields__' in exercise:
        field_defs = exercise['__fields__']
    else:
        exercise['__fields__'] = field_defs = _parse_fields_and_files(exercise)

    # for GET and HEAD return cached form
    if request.method != "POST":
        result = {'fields': field_defs}
        return render_configured_template(
            request, course, exercise, post_url, template, result)

    # for POST, validate data: valid -> asyncjob; invalid -> non-cached form
    result, values, files = _parse_post_and_validate(request, field_defs)

    if exercise.get('required_number_of_files', 0) > len(files):
        result['missing_files'] = True

    # When form data is invalid, return the form (no cache)
    if result:
        result['rejected'] = True
        # merge field definitions and posted values..
        result['fields'] = [
            dict(error=error, value=value, **field)
            for field, (error, value) in zip(field_defs, values)
        ]
        return render_configured_template(
            request, course, exercise, post_url, template, result)

    # When form data is valid, proceed
    sdir = create_submission_dir(course, exercise)
    for field, (error, value) in zip(field_defs, values):
        if field['type'] != 'file':
            write_submission_file(sdir, field['filename'], str(value))
    for filename, fileobj in files:
        save_submitted_file(sdir, filename, fileobj)

    return _acceptSubmission(request, course, exercise, post_url, sdir)


# Old interfaces merged by acceptAsync
acceptFiles = acceptAsync
acceptGeneralForm = acceptAsync
acceptPost = acceptAsync


@cached_view_type
def acceptGitAddress(request, course, exercise, post_url):
    '''
    Presents a template and accepts Git URL for grading.
    '''
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
            sdir = create_submission_dir(course, exercise)
            write_submission_file(sdir, "gitsource", source)
            return _acceptSubmission(request, course, exercise, post_url, sdir)

    return render_configured_template(
        request, course, exercise, post_url,
        "access/accept_git_default.html", result)


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
        sdir = create_submission_dir(course, exercise)
        write_submission_file(sdir, "gitsource", source)
        return _acceptSubmission(request, course, exercise, post_url, sdir)

    return render_configured_template(request, course, exercise, post_url,
        "access/accept_git_user.html", {
            "user": user,
            "hash": make_hash(auth_secret, user)
        })


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
    sdir = create_submission_dir(course, exercise)
    write_submission_file(sdir, "data.json", data)
    for name,uploaded in files.items():
        save_submitted_file(sdir, name, uploaded)
    return _acceptSubmission(request, course, exercise, post_url, sdir)


def _acceptSubmission(request, course, exercise, post_url, sdir):
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
        surl = request.build_absolute_uri(reverse('test-result'))
        surl_missing = True

    # Order container for grading.
    c = _requireContainer(exercise)

    course_extra = {
        "key": course["key"],
        "name": course["name"],
    }
    exercise_extra = {
        "key": exercise["key"],
        "title": exercise.get("title", None),
        "resources": c.get("resources", {}), # Unofficial param, implemented differently later
        "require_constant_environment": c.get("require_constant_environment", False) # Unofficial param, implemented differently later
    }
    if exercise.get("personalized", False):
        exercise_extra["personalized_exercise"] \
            = select_generated_exercise_instance(course, exercise, uids, attempt)

    sid = os.path.basename(sdir)
    write_submission_meta(sid, {
        "url": surl,
        "dir": sdir,
        "course_key": course["key"],
        "exercise_key": exercise["key"],
        "lang": translation.get_language(),
    })
    r = invoke([
        settings.CONTAINER_SCRIPT,
        sid,
        request.scheme + "://" + request.get_host(),
        c["image"],
        os.path.join(DIR, course["key"], c["mount"]),
        sdir,
        c["cmd"],
        json.dumps(course_extra),
        json.dumps(exercise_extra),
    ])
    LOGGER.debug("Container order exit=%d out=%s err=%s",
        r["code"], r["out"], r["err"])
    qlen = 1

    return render_template(request, course, exercise, post_url,
        "access/async_accepted.html", {
            "error": r['code'] != 0,
            "accepted": True,
            "wait": True,
            "missing_url": surl_missing,
            "queue": qlen
        })
