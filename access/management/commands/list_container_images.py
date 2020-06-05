from django.core.management.base import BaseCommand, CommandError
from access.views import config

class Command(BaseCommand):
    help = "List all used container images from course exercise configurations"

    def handle(self, *args, **options):
        images = {}
        for course in config.courses():
            course_name = course['key']
            (_, exercises) = config.exercises(course_name, lang='_root')
            for exercise_root in exercises:
                for lang, exercise in exercise_root.items():
                    container = exercise.get('container', {})
                    image = container.get("image")
                    if image:
                        base, has_tag, tag = image.rpartition(':')
                        if not has_tag:
                            base, tag = tag, 'latest'
                        course_counts = images.setdefault(base, {}).setdefault(tag, {})
                        if course_name in course_counts:
                            course_counts[course_name] += 1
                        else:
                            course_counts[course_name] = 1
        image_counts = []
        for image, tags in images.items():
            image_count = 0
            tag_counts = []
            for tag, courses in tags.items():
                course_counts = [(count, course) for course, count in courses.items()]
                course_counts.sort(reverse=True)
                tag_count = sum((x for x, _ in course_counts))
                tag_counts.append((tag_count, tag, course_counts))
                image_count += tag_count
            tag_counts.sort(reverse=True)
            image_counts.append((image_count, image, tag_counts))
        image_counts.sort(reverse=True)
        for image_count, image, tag_counts in image_counts:
            for tag_count, tag, course_counts in tag_counts:
                print("%s:%s  %d:" % (image, tag, tag_count))
                for count, course in course_counts:
                    print("  - %s: %d" % (course, count))
