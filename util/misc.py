def is_ajax(request):
    """
    Detect AJAX requests.
    Request object method is_ajax() was removed in Django 4.0, this can be used instead.
    """
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'
