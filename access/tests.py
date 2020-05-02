# -*- coding: utf-8 -*-
'''
This module holds unit tests. It has nothing to do with the grader tests.
'''
import time, os
from django.conf import settings
from django.test import TestCase

from access.config import ConfigParser
from util.shell import invoke_script


class ConfigTestCase(TestCase):

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
        access.config.DIR = os.path.join(os.path.dirname(__file__), 'test_data')
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

