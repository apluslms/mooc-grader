DEBUG = True
#SECRET_KEY = 'not a very secret key'
ADMINS = (
)
#ALLOWED_HOSTS = ["*"]
BASE_URL = 'http://localhost:8080'

COURSES_PATH = '/srv/courses'
COURSE_STORE = '/srv/course_store'

STATIC_ROOT = '/local/grader/static/'
MEDIA_ROOT = '/local/grader/media/'
SUBMISSION_PATH = '/local/grader/uploads'
PERSONALIZED_CONTENT_PATH = '/local/grader/ex-meta'
STATIC_URL_HOST_INJECT = 'http://localhost:8080'
HOST_TMP = '/tmp/aplus'

def local_path_to_data(local_path):
    # The container has a symbolic link /local -> /data/grader
    return local_path.replace('/local/', '/data/grader/')

RUNNER_MODULE = '/srv/docker_compose_run.py'
RUNNER_MODULE_SETTINGS = {
    "network": "aplus_default",
    "mounts": {
        COURSES_PATH:                                  HOST_TMP + '/_courses',
        # The symlink /local -> /data/grader seems to be missing somehow nowadays.
        # Add path mapping for both with and without the symlink.
        local_path_to_data(SUBMISSION_PATH):           HOST_TMP + '/_submissions',
        local_path_to_data(PERSONALIZED_CONTENT_PATH): HOST_TMP + '/_personalized',
        SUBMISSION_PATH:                               HOST_TMP + '/_submissions',
        PERSONALIZED_CONTENT_PATH:                     HOST_TMP + '/_personalized',
    },
}

APLUS_AUTH_LOCAL = {
    "UID": "grader",
    "PRIVATE_KEY": """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAweaxw/6dSfIWegPg6y9wrsjSNDZaShQzH9/HsOjcPeIrO8Zu
xT5iZfaPji7y5m+VYaG+76q0harls9uvYdcpdRD8inrUutd6LvMUInyD6h/OVhlO
xvwMzh+UVpE9OnzignGCVpWVqsepJ5/IMf+H4OhOg+O7b28eGIYcyfkkrLviNAoT
8Ml7itQnOzePn+3IvuoEX+3CGXNTt6S7Mm/j2W6vZ8/ZtQuoQhbe3wkDCk2PAQaP
uXlLvbQnQyYkRiIntUQexaokfOwXjSoBzOaScGBcQ7A3ua3NPAiQl5mI+tj2yOg+
qljUIAEmUXbrrEGqGvYDX0VXlP9TtCU8EP/F6wIDAQABAoIBAQDBYud69a9D99no
+YNSrS7yc8IKZwcoCPtwV80fKS+33KGH7YG+4VhcH0vP4A1MPI+9HweCmzuOcQLF
nl5N870aT8XAC3+tlYj72F4FgzBBylUNVBJYrTvMPHzC1fo+Ih37QWBgILJz8MxJ
g7ez/go0Cx17tx7Spf1bMi72VbD5QG2B8uH/9kwHNNJwkL2U44YbGynODTOYiHx5
crKBTcdLwNV89mYprUk6Ac3AOU1485Wqwk/YAnSLw53X4wdYJr/6JTTODrOLHmcV
ZuhCMZ09HZAirAX6b35aXRXxXL00wxm3/V91QONY8l0o/aKkecrWiLXjfBdCfoQV
qONMF0oxAoGBAP8BVo0MNAH26WfZgGVPyLzzUwsuUM0h2eYcZXtMqJuMerkZUB/G
FWByLvpENov4k3gzrfs8G6PK8jkzLuiwLzqIc/JLxZ1geTg4nc0/cCk+Zz9wWqp3
P1ZIFOeXOfWLr1LzQNiG/Z0lbMDbww7iHSLqQDt1epC0KOHEUcKHs+NJAoGBAMKo
VaF9tqkDeEhh6R3sJFxWY4B/1c+9tTliBWfax5DkejrM/VGubzmkCTdduR8/H7Xb
fSibI3oTieuazS7wONZKdAVAHvsC87IvO/+wo08anIYBLV91BS4Dze8zXVpdGB+E
JTm4ts1FTy+U8CzqLb4afjfxTd+6C3QuKqF6TyuTAoGADME2YQuxNj/xYL5iS673
7WuGRdLlO71rtrTI5qfo7w7RvJxlg5FW1GIhs2biC5I9Xg/Hrf9Nqp2mC/JhcEYP
tq/IjN/5XGvM5GEAk5mOtKFobKXkAw6/3kLwuLy5q2x3MoD0R2BJIykSDXtwgDgT
GQH6gH7ZyI8aVGCLbl13Q/ECgYEAqbeDEY4+GBZCZTmYutIM0cUwc/UBQmMxApsI
A4iovxe1yla39uOTbjorHu7EXQ34Y+K+uQyqXeFzOsx5YRdpNs0rYviJCmmEeDLe
qQwlFu8o0V1tZfDtVzVR8+Bg4EySn8fjfPQjzc1EQUQmM8LppvoKWlQ1hX78RYuK
98dgB6kCgYA2XvWlNc9InItYHs40k7NZ29tTwYsEHSO14knBjdSwjnH5GXxrJcQa
MYKJWPxR+xfClOSsEkXSDNmEVp1vHdsEI71u6sm945i2l1NIV/knF5jeL09iePRt
U+SxTmgzsX7dmVrbhQMtzCol/ED8tkmLJb45E4Z09P7p8JJodbG5FQ==
-----END RSA PRIVATE KEY-----""",
    "PUBLIC_KEY": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAweaxw/6dSfIWegPg6y9w
rsjSNDZaShQzH9/HsOjcPeIrO8ZuxT5iZfaPji7y5m+VYaG+76q0harls9uvYdcp
dRD8inrUutd6LvMUInyD6h/OVhlOxvwMzh+UVpE9OnzignGCVpWVqsepJ5/IMf+H
4OhOg+O7b28eGIYcyfkkrLviNAoT8Ml7itQnOzePn+3IvuoEX+3CGXNTt6S7Mm/j
2W6vZ8/ZtQuoQhbe3wkDCk2PAQaPuXlLvbQnQyYkRiIntUQexaokfOwXjSoBzOaS
cGBcQ7A3ua3NPAiQl5mI+tj2yOg+qljUIAEmUXbrrEGqGvYDX0VXlP9TtCU8EP/F
6wIDAQAB
-----END PUBLIC KEY-----""",
    "REMOTE_AUTHENTICATOR_KEY": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnME9k+VaxbUD2fGDgpKH
Ri6cE4T6HZzqWDpvtOShhoHSYQ6VlX0YnDQYwdDoTTK+XIBG2uS8W+3CsvpxjpHF
8Ny5xzxNGZTeqSn8A08BvoQ5cX7bnXOYUb4x2Pp/00WwaQseumUNP+ep/jCV+aqv
iWzOmX9p8zZGdFghvplbt9A173df4t6kICK11hUm14mpUtL/bCQ2xsUEmPGX+zw8
V1kynwJp2AaBuFVpkKDjHyHQJ+yotou01Vksp1kYoX21odjoZCivArEjuwzDEoHt
6WHPLnwvkBYouNA9jgR63mS1rW1PiloDlNNMFW1nR+AHjTfVSKKatnswO3JVLxYe
qwIDAQAB
-----END PUBLIC KEY-----""",
    "REMOTE_AUTHENTICATOR_URL": "http://plus:8000/api/v2/get-token/",
    "REMOTE_AUTHENTICATOR_UID": "aplus",
    "DISABLE_LOGIN_CHECKS": False,
    "DISABLE_JWT_SIGNING": False,
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    },
}

LOGGING['loggers'].update({
    '': {
        'level': 'INFO',
        'handlers': ['console'],
        'propagate': True,
    },
    #'django.db.backends': {
    #    'level': 'DEBUG',
    #},
})

# kate: space-indent on; indent-width 4;
# vim: set expandtab ts=4 sw=4:
