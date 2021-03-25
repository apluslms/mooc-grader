from django.core.management.base import BaseCommand, CommandError
from access.views import config

class Command(BaseCommand):
    help = "List all used container images from course exercise configurations"

    def handle(self, *args, **options):
        view_types = {}
        for course in config.courses():
            course_name = course['key']
            (_, exercises) = config.exercises(course_name)
            for exercise in exercises:
                view_type = exercise.get('view_type', None)
                if view_type == 'access.types.stdsync.createForm' and ('container' in exercise or 'actions' in exercise):
                    view_type += " [async]"
                view_types.setdefault(view_type, []).append((course_name, exercise['key']))

        for view_list in view_types.values():
            view_list.sort()

        summary = [(key, len(courses)) for key, courses in view_types.items()]
        summary.sort(key=lambda x: (x[1], x[0]), reverse=True)

        print("\n  ALL:")
        for key, count in summary:
            courses = view_types[key]
            print("%s (%d)" % (key, count))
            for course, exercise in courses:
                print("  - %s/%s" % (course, exercise))

        print("\n  SUMMARY:")
        for key, count in summary:
            print("%s (%d)" % (key, count))
