from django.db import models


class CourseRepo(models.Model):
    '''
    A course repository served out for learning environments.
    '''
    SPHINX_VERSION_OLD = 'old'
    SPHINX_VERSION_NEW = 'new'
    SPHINX_VERSION_CHOICES = [
        (SPHINX_VERSION_OLD, 'old'),
        (SPHINX_VERSION_NEW, 'new'),
    ]

    key = models.SlugField(unique=True)
    git_origin = models.CharField(max_length=255)
    git_branch = models.CharField(max_length=40)
    update_hook = models.URLField(blank=True)
    sphinx_version = models.CharField(
        max_length=3,
        choices=SPHINX_VERSION_CHOICES,
        default=SPHINX_VERSION_OLD,
    )

    class META:
        ordering = ['key']


class CourseUpdate(models.Model):
    '''
    An update to course repo from the origin.
    '''
    course_repo = models.ForeignKey(CourseRepo, on_delete=models.CASCADE, related_name='updates')
    request_ip = models.CharField(max_length=40)
    request_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)
    updated = models.BooleanField(default=False)
    log = models.TextField(default='')

    class META:
        ordering = ['-request_time']

    def log_nl(self):
        log = self.log
        if isinstance(log, bytes):
            log = log.decode('utf-8')
        return log.replace('\\n', '\n').replace('\\t', '\t')
