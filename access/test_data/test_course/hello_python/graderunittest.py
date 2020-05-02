"""
This is a small unit test extension to ease grading with unit tests.
A more complete set of grading tools could be included in a container
so it doesn't have to be repeated for different python exercises.
"""
from unittest import _TextTestResult, TextTestRunner
import re


class _PointsTestResult(_TextTestResult):
    """
    Adds storing of successes for text result.
    """

    def __init__(self, stream, descriptions, verbosity):
        _TextTestResult.__init__(self, stream, descriptions, verbosity)
        self.successes = []

    def addSuccess(self, test):
        _TextTestResult.addSuccess(self, test)
        self.successes.append(test)


class PointsTestRunner(TextTestRunner):
    """
    Prints out test grading points in addition to normal text test runner.
    Passing a test will grant the points added to the end of the test
    docstring in following format. (10p)
    """

    def _makeResult(self):
        return _PointsTestResult(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        result = TextTestRunner.run(self, test)

        point_re = re.compile('.*\((\d+)p\)$')
        def parse_points(case):
            match = point_re.search(case.shortDescription().strip())
            return int(match.group(1)) if match else 0

        points = sum(parse_points(case) for case in result.successes)
        max_points = points\
            + sum(parse_points(case) for case, exc in result.failures)\
            + sum(parse_points(case) for case, exc in result.errors)

        print('TotalPoints: {:d}\nMaxPoints: {:d}\n'.format(
            points, max_points))
        return result
