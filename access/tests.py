# -*- coding: utf-8 -*-
'''
This module holds unit tests. It has nothing to do with the grader tests.
'''
import hashlib
import time, os
from unittest.mock import patch

from django.conf import settings
from django.test import RequestFactory
from django.test import SimpleTestCase
import yaml

from access.config import ConfigParser, _exercise_content_hash
from access.views import container_post
from util.http import post_result
from util.shell import invoke_script


class ConfigTestCase(SimpleTestCase):

    TEST_DATA = {
        'key': 'value',
        'title|i18n': {'en': 'A Title', 'fi': 'Eräs otsikko'},
        'text|rst': 'Some **fancy** text with ``links <http://google.com>`` and code like ``echo "moi"``.',
        'nested': {
            'number|i18n': {'en': 1, 'fi': 2},
            'another': 10
        }
    }

    def setUp(self):
        import access
        settings.COURSES_PATH = os.path.join(os.path.dirname(__file__), 'test_data')
        self.config = ConfigParser()

    def get_course_key(self):
        courses = self.config.courses()
        self.assertGreater(len(courses), 0, "No courses configured")
        return courses[0]['key']

    def test_rst_parsing(self):
        from access.config import get_rst_as_html
        self.assertEqual(get_rst_as_html('A **foobar**.'), '<p>A <strong>foobar</strong>.</p>\n')

    def test_parsing(self):
        course_root = {'lang': 'en'}
        data = self.config._process_exercise_data(course_root, self.TEST_DATA)
        self.assertEqual(data["en"]["text"], data["fi"]["text"])
        self.assertEqual(data["en"]["title"], "A Title")
        self.assertEqual(data["en"]["nested"]["number"], 1)
        self.assertEqual(data["fi"]["title"], "Eräs otsikko")
        self.assertEqual(data["fi"]["nested"]["number"], 2)

    def test_cache(self):
        course_key = self.get_course_key()

        root = self.config._course_root(course_key)
        mtime = root["mtime"]
        ptime = root["ptime"]
        self.assertGreater(ptime, mtime)

        # Ptime changes if cache is missed.
        root = self.config._course_root(course_key)
        self.assertEqual(root["mtime"], mtime)
        self.assertEqual(root["ptime"], ptime)

    def test_cache_reload(self):
        course_key = self.get_course_key()

        root = self.config._course_root(course_key)
        mtime = root["mtime"]
        ptime = root["ptime"]
        self.assertGreater(ptime, mtime)

        time.sleep(0.01)
        os.utime(root["file"])
        root = self.config._course_root(course_key)
        self.assertGreater(root["ptime"], root["mtime"])
        self.assertGreater(root["mtime"], mtime)
        self.assertGreater(root["ptime"], ptime)

    def test_exercise_hash_ignores_file_timestamp(self):
        course_key = self.get_course_key()
        course_root = self.config._course_root(course_key)
        _, exercise = self.config.exercise_entry(course_root, 'arithmetic', 'en')
        exercise_root = course_root['exercises']['arithmetic']
        stat = os.stat(exercise_root['file'])

        try:
            os.utime(exercise_root['file'], (stat.st_atime, stat.st_mtime + 1))
            _, reloaded = self.config.exercise_entry(course_root, 'arithmetic', 'en')
            self.assertEqual(reloaded['content_hash'], exercise['content_hash'])
        finally:
            os.utime(exercise_root['file'], ns=(stat.st_atime_ns, stat.st_mtime_ns))

    def test_exercise_hash_serializes_yaml_sets_deterministically(self):
        version = yaml.safe_load("values: !!set {bravo: null, alpha: null}")
        expected_serialized = (
            '{"values": {"__type__": "set", "items": ["alpha", "bravo"]}}'
        )
        self.assertEqual(
            _exercise_content_hash(version),
            hashlib.sha256(expected_serialized.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(
            _exercise_content_hash(version),
            _exercise_content_hash({"values": ["alpha", "bravo"]}),
        )

    def test_exercise_hash_serializes_yaml_timestamps(self):
        version = yaml.safe_load("value: 2026-07-10")
        expected_serialized = '{"value": "2026-07-10"}'

        self.assertEqual(
            _exercise_content_hash(version),
            hashlib.sha256(expected_serialized.encode("utf-8")).hexdigest(),
        )

    def test_exercise_hash_rejects_unsupported_values(self):
        with self.assertRaises(TypeError):
            _exercise_content_hash({"value": object()})


class HttpTestCase(SimpleTestCase):

    @patch('util.http.post_data')
    @patch('util.http.template_to_str', return_value='feedback')
    def test_post_result_includes_exercise_version(self, _template_to_str, post_data):
        post_result(
            'https://aplus.example/submission',
            {},
            {'content_hash': 'version'},
            'feedback.html',
            {'points': 1, 'max_points': 1},
        )

        data = post_data.call_args.args[1]
        self.assertEqual(data['exercise_version'], 'version')

    @patch('access.views.post_data', return_value=True)
    @patch('access.views.config.exercise_entry', return_value=({}, {}))
    @patch('access.views.read_and_remove_submission_meta')
    def test_container_result_uses_queued_exercise_version(
            self,
            read_meta,
            _exercise_entry,
            post_data,
            ):
        read_meta.return_value = {
            'url': 'https://aplus.example/submission',
            'dir': '/submission',
            'course_key': 'course',
            'exercise_key': 'exercise',
            'lang': 'en',
            'exercise_version': 'queued version',
        }
        request = RequestFactory().post('/container-post', {
            'sid': 'submission',
            'points': '1',
            'max_points': '1',
            'feedback': 'feedback',
        })

        response = container_post(request)

        self.assertEqual(response.status_code, 200)
        data = post_data.call_args.args[1]
        self.assertEqual(data['exercise_version'], 'queued version')
