import os
import json
import shutil
import logging

from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest

from .course import Course
from .parser import yaml
from .utils import course_manage_required, update_course_index


from apluslms_file_transfer.server.action_general import files_to_update, publish_files
from apluslms_file_transfer.server.django import upload_files, convert_django_header
from apluslms_file_transfer.server.utils import tempdir_path

logger = logging.getLogger(__name__)

UPLOAD_FILE_TYPE = 'yaml'


@csrf_exempt
@require_http_methods(['POST'])
@course_manage_required
def files_select(request, *args, **kwargs):
    """
    Upload/Update a course
    """
    try:
        file = request.FILES['manifest_client'].read()
        manifest_client = json.loads(file.decode('utf-8'))
        res_data = {'course_instance': kwargs['auth']['sub']}  # init the response data
        res_data = files_to_update(upload_dir=settings.COURSES_PATH,
                                   course_name=kwargs['course_name'],
                                   upload_file_type=UPLOAD_FILE_TYPE,
                                   manifest_client=manifest_client,
                                   data=res_data)
    except Exception as e:
        logger.info(e)
        return HttpResponseBadRequest(str(e))

    # print(res_data)
    return JsonResponse(res_data, status=200)


@csrf_exempt
@require_http_methods(['POST'])
@course_manage_required
def files_upload(request, *args, **kwargs):
    res_data = {'course_instance': kwargs['auth']['sub']}
    try:
        res_data = upload_files(request, settings.COURSES_PATH, kwargs['course_name'], res_data)
    except Exception as e:
        return HttpResponseBadRequest(e)

    return JsonResponse(res_data, status=200)


@csrf_exempt
@require_http_methods(['GET'])
@course_manage_required
def files_publish(request, *args, **kwargs):
    print(json.loads(request.body.decode('utf-8')))
    process_id = json.loads(request.body.decode('utf-8')).get("process_id")
    if process_id is None:
        return HttpResponseBadRequest("Invalid finalizer of the uploading process")

    temp_course_dir = tempdir_path(settings.COURSES_PATH, kwargs['course_name'], process_id)
    if not os.path.exists(os.path.join(temp_course_dir, 'manifest.json')):  # the uploading is not completed
        return HttpResponseBadRequest("The upload is not completed")

    res_data = {'course_instance': kwargs['auth']['sub']}

    res_data = publish_files(upload_dir=settings.COURSES_PATH,
                             course_name=kwargs['course_name'],
                             file_type=UPLOAD_FILE_TYPE,
                             temp_course_dir=temp_course_dir,
                             res_data=res_data)
    return JsonResponse(res_data, status=200)


@csrf_exempt
@require_http_methods(['DELETE'])
@course_manage_required
def course_delete(request, *args, **kwargs):
    """ Delete a course
    """
    # the absolute path of the course in mooc-grader
    auth = kwargs['auth']
    courses_path = settings.COURSES_PATH
    course_name = kwargs['course_name']
    course_directory = os.path.join(courses_path, course_name)

    # if the course does not exist
    if not os.path.exists(course_directory):
        return HttpResponseBadRequest("error: The course folder does not exist")

    # delete the course
    shutil.rmtree(course_directory)
    message = 'Delete the course {} successfully'.format(course_name)

    return JsonResponse({
        'course_instance': auth['sub'],
        'status': 'success',
        'message': message
    }, status=200)


@csrf_exempt
@require_http_methods(['DELETE'])
@course_manage_required
def file_delete(request, *args, **kwargs):
    """ Delete a file of a course directory
    """
    # get the path of the course directory
    auth = kwargs['auth']
    courses_path = settings.COURSES_PATH
    course_name = kwargs['course_name']
    course_directory = os.path.join(courses_path, course_name)
    if not os.path.exists(course_directory):
        return HttpResponseBadRequest('The course directory {} does not exist'.format(course_name))

    # get the path of the file
    rel_file_path = kwargs.get('file_path', None)
    if not rel_file_path:
        return HttpResponseBadRequest('No valid file_path provided')

    file_path = os.path.join(course_directory, rel_file_path)
    if not os.path.exists(file_path):
        return HttpResponseBadRequest('{} does not exist'.format(file_path))

    # remove the file
    os.remove(file_path)
    message = 'Delete the file {} of the course {} successfully'.format(file_path, course_name)

    return JsonResponse({
        'status': 'success',
        'message': message
    }, status=200)


@csrf_exempt
@require_http_methods(['POST'])
@course_manage_required
def course_index_update(request, *args, **kwargs):
    """ Update the index.yaml of a course
    """
    # check the path of the course in mooc-grader
    auth = kwargs['auth']
    courses_path = settings.COURSES_PATH
    course_key = auth['sub'].strip()
    course_directory = os.path.join(courses_path, course_key)

    try:
        # parse index.yaml
        course = Course(course_directory)
        course.load('index.yaml')
        index_data = course.get_data()

        # update the url fields
        updated_data = update_course_index(request, index_data, course_key)

        # save the updated index.yaml
        updated_index = os.path.join(course_directory, 'updated_index.yaml')
        with open(updated_index, 'w', encoding='utf8') as update_yaml:
            yaml.dump(updated_data, update_yaml)
    except Exception as e:
        logger.info(str(e))
        return HttpResponseBadRequest(str(e))

    return JsonResponse({
        'course_instance': auth['sub'],
        'message': 'index.yaml is updated successfully',
        'updated_index': updated_data
    }, status=200)
