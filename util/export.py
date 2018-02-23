from django.conf import settings
from django.core.urlresolvers import reverse


def url_to_exercise(request, course_key, exercise_key):
    return request.build_absolute_uri(
        reverse('exercise', args=[course_key, exercise_key]))


def url_to_model(request, course_key, exercise_key, parameter=None):
    return request.build_absolute_uri(
        reverse('model', args=[course_key, exercise_key, parameter or ''])
    )


def url_to_template(request, course_key, exercise_key, parameter=None):
    return request.build_absolute_uri(
        reverse('exercise_template', args=[course_key, exercise_key, parameter or ''])
    )


def url_to_static(request, course_key, path):
    ''' Creates an URL for a path in static files '''
    return request.build_absolute_uri(
        '{}{}/{}'.format(settings.STATIC_URL, course_key, path))


def chapter(request, course, of):
    ''' Exports chapter data '''
    path = of.pop('static_content')
    if type(path) == dict:
        of['url'] = {
            lang: url_to_static(request, course['key'], p)
            for lang,p in path.items()
        }
    else:
        of['url'] = url_to_static(request, course['key'], path)
    return of


def exercise(request, course, exercise_root, of):
    ''' Exports exercise data '''
    of.pop('config')
    languages,exercises = zip(*exercise_root.items())
    exercise = exercises[0]

    if not 'title' in of and not 'name' in of:
        of['title'] = i18n(languages, exercises, 'title')
    if not 'description' in of:
        of['description'] = exercise.get('description', '')
    if 'url' in exercise:
        of['url'] = exercise['url']
    else:
        of['url'] = url_to_exercise(request, course['key'], exercise['key'])

    of['exercise_info'] = {
        'form_spec': form_fields(languages, exercises),
    }
    if 'radar_info' in exercise:
        of['exercise_info']['radar'] = exercise['radar_info']

    if 'model_answer' in exercise:
        of['model_answer'] = exercise['model_answer']
    elif 'model_files' in exercise:
        of['model_answer'] = i18n_urls(
            languages, exercises, 'model_files',
            url_to_model, request, course['key'], exercise['key']
        )
    elif exercise.get('view_type', None) == 'access.types.stdsync.createForm':
        of['model_answer'] = url_to_model(
            request, course['key'], exercise['key']
        )

    if 'exercise_template' in exercise:
        of['exercise_template'] = exercise['exercise_template']
    elif 'template_files' in exercise:
        of['exercise_template'] = i18n_urls(
            languages, exercises, 'template_files',
            url_to_template, request, course['key'], exercise['key']
        )

    return of


def form_fields(languages, exercises):
    ''' Describes a form that the configured exercise produces '''

    def field_spec(f, n):
        field = {
            'key': f.get('key', 'field_' + str(n)),
            'type': f.get('type'),
            'title': f.get('title', ''),
            'required': f.get('required', False),
        }

        mods = f.get('compare_method', '').split('-')
        if 'int' in mods:
            field['type'] = 'number'
        elif 'float' in mods:
            field['type'] = 'number'
        elif 'regexp' in mods:
            field['pattern'] = f.get('correct')

        if 'more' in f:
            field['description'] = f.get('more', '')

        if 'options' in f:
            titleMap = {}
            enum = []
            m = 0
            for o in f['options']:
                v = o.get('value', 'option_' + str(m))
                titleMap[v] = o.get('label', 'missing')
                enum.append(v)
                m += 1
            field['titleMap'] = titleMap
            field['enum'] = enum

        if 'extra_info' in f:
            field.update(f['extra_info'])

        if 'class' in field:
            field['htmlClass'] = field['class']
            del(field['class'])

        return field

    #TODO define form spec for language support
    exercise = exercises[0]
    t = exercise.get('view_type', None)
    form = []

    if t == 'access.types.stdsync.createForm':
        n = 0
        for fg in exercise.get('fieldgroups', []):
            for f in fg.get('fields', []):
                t = f.get('type')

                if t == 'table-radio' or t == 'table-checkbox':
                    for row in f.get('rows', []):
                        rf = f.copy()
                        rf['type'] = t[6:]
                        if 'key' in row:
                            rf['key'] = row['key']
                        if 'label' in row:
                            rf['title'] += ': ' + row['label']
                        form.append(field_spec(rf, n))
                        n += 1

                        if 'more_text' in rf:
                            form.append({
                                'key': rf.get('key', 'field_' + str(n)) + '_more',
                                'type': 'text',
                                'title': rf['more_text'],
                                'required': False,
                            })
                            n += 1
                else:
                    form.append(field_spec(f, n))
                    n += 1

    elif t == 'access.types.stdasync.acceptPost':
        for f in exercise.get('fields', []):
            form.append({
                'key': f.get('name'),
                'type': 'textarea',
                'title': f.get('title'),
                'requred': f.get('required', False),
            })

    elif t == 'access.types.stdasync.acceptFiles':
        for f in exercise.get('files', []):
            form.append({
                'key': f.get('field'),
                'type': 'file',
                'title': f.get('name'),
                'required': f.get('required', True),
            })
    return form


def i18n(languages, values, key):
    if len(languages) == 1:
        return values[0].get(key)
    return {
        l: values[i].get(key)
        for i,l in enumerate(languages)
    }


def i18n_urls(languages, values, key, mapper, request, course_key, exercise_key):
    def urls(paths):
        return ' '.join([
            mapper(request, course_key, exercise_key, path.split('/')[-1])
            for path in paths
        ])
    if len(languages) == 1:
        return urls(values[0].get(key, []))
    return {
        l: urls(values[i].get(key, []))
        for i,l in enumerate(languages)
    }
