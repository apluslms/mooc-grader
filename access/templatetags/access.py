from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def ajax_url(context):
    request = context["request"]
    context["submission_url"] = request.GET.get('submission_url')
    context["submit_url"] = request.build_absolute_uri(reverse(
        'access.views.exercise_ajax',
        args=[context['course']['key'], context['exercise']['key']]
    ))
    return ""


@register.filter
def find_checkbox_hints(list_of_hints, value):
    return list_of_hints.get(value)


@register.filter
def find_common_hints(list_of_hints, checked):
    hints = []
    hints_seen = set()

    if list_of_hints:
        for hint_key, hint_value in list_of_hints.items():
            # 'multiple' and 'not' are special values (see GradedForm.grade_field).
            if hint_key == 'multiple':
                if len(checked) == 1:
                    hints.append(hint_value)
            elif hint_key == 'not':
                for not_hint_key, not_hint_value in hint_value.items():
                    if not_hint_key not in hints_seen and not_hint_key not in checked:
                        hints_seen.add(not_hint_key)
                        hints.append(not_hint_value)
            else:
                if hint_key not in hints_seen and hint_key in checked:
                    hints_seen.add(hint_key)
                    hints.append(hint_value)

    return hints
