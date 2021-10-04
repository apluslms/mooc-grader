from typing import Callable

from aplus_auth.auth.django import login_required as login_required_base
from django.http.response import HttpResponse


ViewType = Callable[..., HttpResponse]
login_required: Callable[[ViewType],ViewType] = login_required_base(redirect_url="/login?referer={url}")
