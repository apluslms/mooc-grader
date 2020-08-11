import math
import random
import re
import json
import difflib
from collections import OrderedDict

from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.forms.utils import ErrorDict
from django.forms.widgets import CheckboxSelectMultiple, RadioSelect, Textarea
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from util.templates import template_to_str
from util import forms as custom_forms
from .auth import make_hash
from .auth import user_ids_from_string
from ..config import ConfigError


class GradedForm(forms.Form):
    '''
    A dynamically build form class for an exercise.
    '''

    def __init__(self, *args, **kwargs):
        '''
        Constructor. Requires keyword argument "exercise".
        '''
        if "exercise" not in kwargs:
            raise ConfigError("Missing exercise configuration from form arguments.")
        self.exercise = kwargs.pop("exercise")
        self.model_answer = kwargs.pop('model_answer', False)
        self.reveal_correct = kwargs.pop('reveal_correct', False)
        if not self.exercise.get('reveal_model_at_max_submissions', False):
            self.reveal_correct = False
        self.request = kwargs.pop('request') if 'request' in kwargs else None
        kwargs['label_suffix'] = ''

        # Set form-field ids to be random strings
        random_id = get_random_string(length=8)
        kwargs.setdefault("auto_id", "exercise-{}-%s".format(random_id))

        super(forms.Form, self).__init__(*args, **kwargs)

        if "fieldgroups" not in self.exercise:
            raise ConfigError("Missing required \"fieldgroups\" in exercise configuration")

        self.form_id = "exercise-{}-form".format(random_id)
        self.form_nonce = random_id
        self.disabled = self.model_answer
        self.randomized = False
        self.rng = random.Random()
        self.multipart = False
        samples = []
        g = 0
        i = 0

        # Travel each fields froup.
        for group in self.exercise["fieldgroups"]:
            if "fields" not in group:
                raise ConfigError("Missing required \"fields\" in field group configuration")

            # Group errors to hide the errorneous fields.
            group_errors = group.get("group_errors", False)
            if group_errors:
                self.group_errors = True

            # Randomly pick fields to include.
            if "pick_randomly" in group:
                self.randomized = True
                # Multiple different fieldgroups may use pick_randomly, so set
                # the question_key for each fieldgroup in self.current_sample()
                # in order to generate different random samples.
                indexes = self.current_sample(False, int(group["pick_randomly"]),
                    len(group["fields"]), question_key="_fieldgroup" + str(g),
                    resample_after_attempt=group.get('resample_after_attempt', True))
                if args[0] is not None:
                    # Check that sample is unmodified in a randomized form when the user submits.
                    # The sample is stored in the POST data for only debugging purposes.
                    # The random sample used in grading is computed again
                    # deterministically in the server.
                    sample = args[0].get('_sample', '')
                    checksum = args[0].get('_checksum', '')
                    if self.samples_hash(sample) != checksum or (
                        not sample or not checksum
                    ):
                        raise PermissionDenied('Invalid checksum')
                    self.disabled = True
                else:
                    samples.append('-'.join([str(i) for i in indexes]))
                group["_fields"] = [group["fields"][i] for i in indexes]
            else:
                group["_fields"] = group["fields"]

            j = 0
            l = len(group["_fields"]) - 1

            # Travel each field in group.
            for field in group["_fields"]:
                if "type" not in field:
                    raise ConfigError("Missing required \"type\" in field configuration for: %s" % (group["name"]))
                t = field["type"]

                # Create a field by type.
                choices, initial, correct, neutral = self.create_choices(field)
                if t == "checkbox":
                    if 'randomized' in field and args[0] is not None:
                        # grading a randomized question
                        self.disabled = True

                    i, f = self.add_field(i, field,
                        forms.MultipleChoiceField, forms.CheckboxSelectMultiple,
                        initial, correct, neutral, choices, True, {}, args[0])
                elif t == "radio":
                    i, f = self.add_field(i, field,
                        forms.ChoiceField, forms.RadioSelect,
                        initial, correct, neutral, choices, False, {})
                elif (t == "dropdown" or t == "select"):
                    i, f = self.add_field(i, field,
                        forms.ChoiceField, forms.Select,
                        initial, correct, neutral, choices, False)
                elif t == "text":
                    i, f = self.add_field(i, field,
                        self._get_text_field_type(field), forms.TextInput)
                elif t == "textarea":
                    attrs = {'class': 'form-control'}
                    for key in ['rows','cols']:
                        if key in field:
                            attrs[key] = field[key]
                    i, f = self.add_field(i, field,
                        self._get_text_field_type(field), forms.Textarea,
                        widget_attrs=attrs)
                elif t == "table-radio":
                    i, f = self.add_table_fields(i, field,
                        forms.ChoiceField, forms.RadioSelect)
                elif t == "table-checkbox":
                    i, f = self.add_table_fields(i, field,
                        forms.MultipleChoiceField, forms.CheckboxSelectMultiple, True)
                elif t == "static":
                    i, f = self.add_field(i, field,
                        forms.CharField, custom_forms.PlainTextWidget)
                elif t == "file":
                    self.multipart = True
                    i, f = self.add_field(i, field,
                        forms.FileField, forms.ClearableFileInput)
                else:
                    raise ConfigError("Unknown field type: %s" % (t))

                for fi in f:
                    fi.group_errors = group_errors

                if j == 0:
                    f[0].open_set = "exercise-{}-set-{}".format(self.form_nonce, self.group_name(g))
                    if "title" in group:
                        f[0].set_title = group["title"]
                if j >= l:
                    f[-1].close_set = True
                j += 1

            g += 1

        if 'lang' in self.exercise:
            self.add_field(i, {
                'type': 'hidden',
                'initial': self.exercise['lang'],
                'key': '__grader_lang',
            }, forms.CharField, forms.HiddenInput)

        # Protect sample used in a randomized form.
        if len(samples) > 0:
            self.sample = '/'.join(samples)
            self.checksum = self.samples_hash(self.sample)


    def _get_text_field_type(self, field):
        # Field is a dictionary from the exercise config.yaml.
        input_type = field.get('compare_method', '').split('-')[0]
        # Integer and float fields validate that the input is numeric.
        if input_type == 'int':
            return forms.IntegerField
        elif input_type == 'float':
            return forms.FloatField
        else:
            return forms.CharField

    def samples_hash(self, sample):
        return make_hash(
            self.exercise.get('secret') or settings.AJAX_KEY,
            sample
        )

    def add_table_fields(self, i, config, field_class, widget_class, multiple=False):
        fields = []
        choices, initial, correct, neutral = self.create_choices(config)
        for row in config.get('rows', []):

            if self.model_answer:
                correct = []
                corr = self.row_options(config, row)['options']
                for i,choice in enumerate(choices):
                    if corr[i]['correct']:
                        correct.append(choice[0])

            row_config = config.copy()
            if 'key' in row:
                row_config['key'] = row['key']
            i, fi = self.add_field(i, row_config,
                field_class, widget_class, initial, correct, choices, multiple, {})
            fi[0].row_label = row.get('label', None)
            fields += fi

            if 'more_text' in config:
                fi[0].more_text = config['more_text']
                more_config = config.copy()
                more_config['key'] = self.field_name(i, row_config) + '_more'
                i, fm = self.add_field(i, more_config,
                    forms.CharField, forms.TextInput)
                fm[0].row_label = row.get('label', None)
                fm[0].table_more = True
                fields += fm

        fields[0].open_table = True
        fields[-1].close_table = True
        return i, fields

    def add_field(self, i, config, field_class, widget_class,
            initial=None, correct=None, neutral=None, choices=None, multiple=False,
            widget_attrs={'class': 'form-control'}, post_data=None):
        args = {
            'widget': widget_class(attrs=widget_attrs),
            'required': 'required' in config and config['required'],
        }
        if self.disabled:
            args['widget'].attrs['disabled'] = 'disabled'

        name = self.field_name(i, config)
        selected_choices = choices
        correct_choices = correct
        neutral_choices = neutral
        initial_choices = initial
        random_attributes = None

        if choices is not None:
            if 'randomized' in config and multiple:
                selected_choices, correct_choices, initial_choices, random_attributes = (
                    self.get_randomized_checkbox_attributes(i, config, initial,
                            correct, name, choices, post_data)
                )
            args['choices'] = selected_choices

        if self.model_answer:
            # Checks the correct fields in a model answer
            if neutral_choices and correct_choices:
                combined = correct_choices + neutral_choices
                args['initial'] = combined
            elif correct_choices:
                args['initial'] = correct_choices if multiple else correct_choices[0]
            elif config.get('model', False):
                args['initial'] = config['model']
            elif config.get('correct', False):
                args['initial'] = config['correct']
        else:
            if initial:
                args['initial'] = initial_choices if multiple else initial_choices[0]
            elif config.get('initial', False):
                args['initial'] = config['initial']

        field = field_class(**args)
        field.type = config['type']
        field.name = name
        if 'title' in config:
            field.label = mark_safe(config['title'].replace('{#}', str(i + 1)))
        field.more = self.create_more(config)
        field.points = config.get('points', 0)
        field.choice_list = choices is not None and widget_class != forms.Select
        field.neutral = neutral

        if correct:
            field.correct = correct
        elif config.get('model', False):
            field.correct = config['model']
        elif config.get('correct', False):
            field.correct = config['correct']

        if random_attributes:
            field.randomized = True
            field.random_sample = random_attributes['sample']
            field.random_checksum = random_attributes['checksum']
        else:
            field.random_sample = ''

        if 'extra_info' in config and 'class' in config['extra_info']:
            field.html_class = config['extra_info']['class']
        else:
            field.html_class = 'form-group'

        self.fields[field.name] = field
        return (i + 1, [field])

    def create_more(self, configuration):
        '''
        Creates more instructions by configuration.
        '''
        more = ""
        if "more" in configuration:
            more += configuration["more"]
        if "include" in configuration:
            more += template_to_str(None, None, configuration["include"])
        return more or None

    def create_choices(self, configuration):
        '''
        Creates choices for dropdown, select, radio and checkbox-type questions.
        Create also the lists of correct, neutral and initially selected options.
        '''
        choices = []
        initial = []
        correct = []
        neutral = []
        if "options" in configuration:
            i = 0
            for opt in configuration["options"]:
                label = opt.get('label', "")
                value = self.option_name(i, opt)
                choices.append((value, mark_safe(label)))
                if opt.get('correct') == "neutral":
                    neutral.append(value)
                elif opt.get('correct', False) is True:
                    correct.append(value)
                if opt.get('selected', False) or opt.get('initial', False):
                    initial.append(value)
                i += 1

        return choices, initial, correct, neutral

    def group_name(self, i):
        return "group_{:d}".format(i)

    def field_name(self, i, config):
        return config.get("key", "field_{:d}".format(i))

    def option_name(self, i, config):
        return config.get("value", "option_{:d}".format(i))

    def append_hint(self, hints, configuration):
        # The old definition of hint per option.
        hint = str(configuration.get('hint', ''))
        if hint and not hint in hints:
            hints.append(hint)

    def is_enrollment_exercise(self):
        return self.exercise.get('status', '') in ('enrollment', 'enrollment_ext')

    def current_sample(self, is_checkbox_question, how_many, index_range,
                correct_count=None, correct_indexes=None, incorrect_indexes=None,
                question_key='', resample_after_attempt=True):
        '''Calculate a random sample (selection of choices) for a pick_randomly
        questionnaire or a randomized checkbox question.

        The parameter resample_after_attempt controls whether the sample changes
        after each submission attempt or whether it remains the same.
        '''
        # Model answers show all questions
        if not self.request:
            return range(index_range)

        # Set a deterministic random seed based on the user IDs, the ordinal number,
        # and the exercise key so that the random choices change for different
        # users, exercises, and submissions, but they do not change when the user
        # just reloads the exercise description.
        # If resample_after_attempt is False, then the submission ordinal number
        # does not affect the random sample. Thus, the same random questions
        # are used for multiple submission attempts.
        # Use a Random instance so that the seed does not affect other uses of
        # the random module elsewhere in the code.
        self.rng.seed(self.exercise['key'] + question_key + self.request.GET.get('uid', '1'))
        calculated_seed = self.rng.randrange(10000000000)
        if resample_after_attempt:
            calculated_seed += int(self.request.GET.get('ordinal_number', 1))
        self.rng.seed(calculated_seed)

        if is_checkbox_question:
            if correct_count is not None:
                random_sample = self.rng.sample(correct_indexes, correct_count) \
                    + self.rng.sample(incorrect_indexes, how_many - correct_count)
                # Shuffle the list so that the correct choices are not always listed first.
                self.rng.shuffle(random_sample)
            else:
                random_sample = self.rng.sample(range(index_range), how_many)
        else:
            random_sample = self.rng.sample(range(index_range), how_many)
        return random_sample

    def bind_initial(self):
        '''
        Binds form using initial values.
        '''
        self.is_bound = True
        self._errors = ErrorDict()
        self.cleaned_data = {}
        for name, field in self.fields.items():
            value = self.initial.get(name, field.initial)
            try:
                self.cleaned_data[name] = field.clean(value)
            except ValidationError as e:
                self.add_error(name, e)
            field.disabled = True

    def grade(self):
        '''
        Grades form answers.
        '''
        points = 0
        error_fields = []
        error_groups = []
        g = 0
        i = 0
        for group in self.exercise["fieldgroups"]:
            for field in group["_fields"]:
                prev = i
                i, ok, p = self.grade_field(i, field)
                points += p
                if not ok:
                    error_fields.append(self.field_name(prev, field))
                    gname = self.group_name(g)
                    if gname not in error_groups:
                        error_groups.append(gname)
            g += 1

        return (points, error_groups, error_fields)

    def compare_values(self, method, val, cmp):
        # Note: when adding new compare methods or modifiers, remember to update
        # _validate_compare_method in a-plus-rst-tools/directives/questionnaire.py
        parts = method.split("-")
        t = parts[0]
        mods = parts[1:]

        if t == "array":
            return cmp in val
        elif t == "int":
            if val is None or val == '':
                return False
            return int(val) == int(cmp)
        elif t == "float":
            if val is None or val == '':
                return False
            return math.isclose(float(val), float(cmp), rel_tol=0.02)

        def good_strip(v):
            return v.strip().replace("\r","")
        val = good_strip(val)
        cmp = good_strip(cmp)

        if "ignorerepl" in mods:
            p = re.compile('(^\w+:\s[\w\.\[\]]+\s=)')
            m = p.match(val)
            if m:
                val = val[len(m.group(1)):].strip()

        if "ignorews" in mods or t == "unsortedchars":
            def strip_ws(v):
                return ''.join(v.split())
            val = strip_ws(val)
            cmp = strip_ws(cmp)

        if "ignorequotes" in mods:
            def strip_quotes(v):
                if v.startswith("\"") and v.endswith("\""):
                    return v[1:len(v)-1]
                return v
            val = strip_quotes(val)
            cmp = strip_quotes(cmp)

        if "ignoreparenthesis" in mods:
            def strip_parenthesis(v):
                return v.replace("(","").replace(")","")
            if t == "regexp":
                val = strip_parenthesis(val)
            else:
                val = strip_parenthesis(val)
                cmp = strip_parenthesis(cmp)

        if t == "unsortedchars":
            return set(val) == set(cmp)
        if t == "string":
            if "\n" in cmp:
                cmp_a = [l.strip() for l in cmp.strip().split("\n")]
                val_a = [l.strip() for l in val.strip().split("\n")]
                if len(cmp_a) != len(val_a):
                    return False
                if "requirecase" in mods:
                    return all(c==v for c,v in zip(cmp_a,val_a))
                else:
                    return all(c.lower()==v.lower() for c,v in zip(cmp_a,val_a))
            elif "requirecase" in mods:
                return val == cmp
            else:
                return val.lower() == cmp.lower()
        elif t == "regexp":
            if cmp.startswith('/') and cmp.endswith('/'):
                cmp = cmp[1:-1]
            p = re.compile(cmp)
            return bool(p.search(val))
        else:
            raise ConfigError("Unknown compare method in form: %s" % (t))

    def grade_field(self, i, configuration):
        t = configuration["type"]

        if t == "table-radio" or t == "table-checkbox":
            all_ok = True
            names = []
            hints = []
            points = configuration.get("points", 0)
            max_points = points
            for row in configuration.get("rows", []):
                name = self.field_name(i, row)
                names.append(name)
                value = self.cleaned_data.get(name, None)
                if t == "table-radio":
                    ok, hints, method = self.grade_radio(
                        self.row_options(configuration, row), value, hints)
                else:
                    ok, correct_count, hints, method = self.grade_checkbox(
                        self.row_options(configuration, row), value, hints, name=name)
                if self.exercise.get("feedback") or self.is_enrollment_exercise():
                    points += row.get("points", 0)
                    max_points += row.get("points", 0)
                elif self.row_options(configuration, row).get("partial_points"):
                    points += max(int(row.get("points", 0) * ok), 0)
                    max_points += row.get("points", 0)
                    if not points == max_points:
                        all_ok = False
                elif ok:
                    points += row.get("points", 0)
                    max_points += row.get("points", 0)
                else:
                    all_ok = False
                    max_points += row.get("points", 0)
                i += 1
            self.fields[names[0]].grade_points = points
            self.fields[names[0]].max_points = max_points
            self.fields[name].hints = ' '.join(hints)
            return i, all_ok, points

        name = self.field_name(i, configuration)
        value = self.cleaned_data.get(name, None)

        if t == "checkbox":
            ok, correct_count, hints, method = self.grade_checkbox(configuration, value, name=name)
            if not hints:
                # checkbox-hints are in an OrderedDict to enable linking
                # the hints efficiently to the related option
                hints = OrderedDict()
        elif t == "radio" or t == "dropdown" or t == "select":
            ok, hints, method = self.grade_radio(configuration, value)
        elif t == "text" or t == "textarea":
            ok, hints, method = self.grade_text(configuration, value)
        elif t in ("static", "file"):
            ok, hints, method = True, [], 'string'
        else:
            raise ConfigError("Unknown field type for grading: %s" % (t))

        points = configuration.get('points', 0)
        if self.exercise.get("feedback", False) or self.is_enrollment_exercise():
            # Feedback questionnaires grant full points unless they are rejected.
            # The partial_points is not meant to be used in feedback questionnaires.
            # However, if they both exist, the grader should not crash.
            ok = True
            earned_points = points
        elif configuration.get('partial_points'):
            # grade_checkbox returns ok as float instead of a boolean, if
            # 'partial points' is set
            earned_points = max(int(points * ok), 0)
            ok = (earned_points == points)
        elif ok:
            earned_points = points
        else:
            earned_points = 0

        # Check if the field is fully correct
        answer_correct = (earned_points==points)

        # Apply new feedback definitions.
        methods = method.split("-")
        mods = methods[1:]

        for fb in configuration.get("feedback", []):
            new_hint = fb.get('label', None)
            comparison = fb.get('value', '')
            if not new_hint:
                continue
            add = False
            if comparison == "%100%":
                add = ok
            else:
                # Freetext questions with 'string', 'subdiff' or 'regexp'
                # compare method can have reqular expression based hints.
                if methods[0] in ('string', 'regexp', 'subdiff'):
                    if fb.get('compare_regexp', False):
                        methods_used = 'regexp'
                    else:
                        methods_used = 'string'
                    methods_used = '-'.join([methods_used] + mods)
                else:
                    methods_used = method
                r = self.compare_values(methods_used, value, comparison)
                add = not r if fb.get('not', False) else r

            # Checkbox-hints should be linkable with their options:
            if t == "checkbox" and add:
                if fb.get('not'):
                    hints['not'] = hints.get('not') or OrderedDict()
                    hints['not'][fb.get('value', '')] = new_hint
                else:
                    hints[fb.get('value', '')] = new_hint

            if t != "checkbox" and add:
                for j in range(len(hints)):
                    if new_hint.startswith(hints[j]):
                        hints[j] = new_hint
                        add = False
                        break
                    elif hints[j].startswith(new_hint):
                        add = False
                        break

            if t != "checkbox" and add:
                hints.append(new_hint)

        if t == "checkbox" and correct_count > 1:
            hints['multiple'] = _('Multiple choices are selectable')

        if name in self.fields:
            self.fields[name].grade_points = earned_points
            self.fields[name].max_points = points
            self.fields[name].hints = hints
            self.fields[name].answer_correct = answer_correct

        return i + 1, ok, earned_points

    def row_options(self, configuration, row):
        hint = row.get('hint', '')
        correct = row.get('correct_options', [])
        opt = []
        for i, srcopt in enumerate(configuration.get('options', [])):
            trgopt = srcopt.copy()
            trgopt.update({
                'hint': hint,
                'correct': correct[i] if i < len(correct) else False,
            })
            opt.append(trgopt)
        return { 'options': opt }

    def grade_checkbox(self, configuration, value, hints=None, name=''):
        hints = hints or []
        correct_count = 0
        wrong_answers = 0
        non_neutral_count = 0
        # Non-random checkbox questions have empty string as random_sample.
        randomized_sample = self.fields[name].random_sample if name else ''
        sample = [int(x) for x in randomized_sample.split('-')] if randomized_sample else []
        is_randomized = bool(sample)
        # If partial points is not set, all options must be answered correctly
        # in order to gain points.
        # If no correct answers are set in configuration, points are granted to
        # an empty answer only.
        correct = True
        i = 0
        for opt in configuration.get("options", []):
            if not is_randomized or i in sample:
                name = self.option_name(i, opt)
                correct_answer = opt.get("correct", False)
                # correct_answer may be boolean or string "neutral"
                if correct_answer is True:
                    correct_count += 1
                    non_neutral_count += 1
                    if name not in value:
                        wrong_answers += 1
                        correct = False
                        self.append_hint(hints, opt)
                elif correct_answer is False:
                    non_neutral_count += 1
                    if value is not None and name in value:
                        correct = False
                        wrong_answers += 1
                        self.append_hint(hints, opt)
                elif correct_answer == "neutral":
                    if value is not None and name in value:
                        self.append_hint(hints, opt)
            i += 1

        # If partial_points are set, the variable 'correct' becomes a float
        # less than one instead of a boolean. It will be used to multiply
        # the max points.
        if configuration.get("partial_points"):
            if wrong_answers == 0 or non_neutral_count == 0:
                correct = 1
            else:
                correct = (non_neutral_count / 2.0 - wrong_answers) / (non_neutral_count / 2.0)

        return correct, correct_count, hints, 'array'

    def grade_radio(self, configuration, value, hints=None):
        hints = hints or []

        # There may be several correct options, but only one of them needs to
        # be selected in the submission in order to gain points.
        correct = False
        i = 0
        for opt in configuration.get("options", []):
            name = self.option_name(i, opt)
            if opt.get("correct", False):
                if name == value:
                    correct = True
                else:
                    self.append_hint(hints, opt)
            elif name == value:
                self.append_hint(hints, opt)
            i += 1
        return correct, hints, 'string'

    def grade_text(self, configuration, value, hints=None):
        hints = hints or []
        correct = False
        accept = None
        method = configuration.get('compare_method', 'string')
        if "regex" in configuration:
            accept = configuration["regex"]
            method = "regexp"
        elif "correct" in configuration:
            accept = configuration["correct"]
            # subdiff method may have multiple correct answers.
            if method.startswith('subdiff'):
                mods = method[7:]
                correct_answers = accept.split('|')
                for model in correct_answers:
                    ok = self.compare_values('string' + mods, value, model)
                    if ok:
                        correct = True
                if not correct:
                    # Show matching parts in the feedback.
                    for hint in get_subdiff_hints(value, accept):
                        hints.append(hint)
                return correct, hints, method
        if accept is not None:
            correct = self.compare_values(method, value, accept)
        else:
            # Answer counts as correct if there is no model solution.
            correct = True
        if not correct:
            self.append_hint(hints, configuration)
        return correct, hints, method

    def json_and_files(self, post_url=None):
        data = {}
        files = {}
        for key,val in self.cleaned_data.items():
            if isinstance(val, UploadedFile):
                files[key] = val
            else:
                data[key] = val
        if post_url:
            data["__aplus_post_url"] = post_url
        return json.dumps(data), files

    def get_randomized_checkbox_attributes(self, i, config, initial, correct,
            name, choices, post_data):
        self.randomized = True
        index = 0
        correct_indexes = []
        initial_indexes = []
        for value, label in choices:
            if value in correct:
                correct_indexes.append(index)
            if value in initial:
                initial_indexes.append(index)
            index += 1
        incorrect_indexes = [x for x in range(len(choices)) if x not in correct_indexes]

        if post_data:
            # grading a submission
            field_sample = post_data.get(name + '_sample', '')
            field_checksum = post_data.get(name + '_checksum', '')
            if self.samples_hash(field_sample) != field_checksum or (
                not field_sample or not field_checksum
            ):
                raise PermissionDenied('Invalid checksum')

        # The sample is stored in the POST data for only debugging purposes.
        # The random sample used in grading is computed again
        # deterministically in the server.
        samples = self.current_sample(True, config.get('randomized'),
            len(choices), config.get('correct_count'),
            correct_indexes, incorrect_indexes, name,
            resample_after_attempt=config.get('resample_after_attempt', True))

        selected_choices = []
        correct_choices = []
        initial_choices = []
        for i in samples:
            selected_choices.append(choices[i])
            if i in correct_indexes:
                correct_choices.append(choices[i][0])
            if i in initial_indexes:
                initial_choices.append(choices[i][0])

        random_attributes = {
            'sample': '-'.join(str(x) for x in samples),
        }
        random_attributes['checksum'] = self.samples_hash(random_attributes['sample'])
        return selected_choices, correct_choices, initial_choices, random_attributes


def get_subdiff_hints(value, all_solutions):
    solutions = all_solutions.split('|')
    if len(solutions) > 1:
        matching_parts = [_("Multiple correct answers accepted.")]
    else:
        matching_parts = []
    for solution in solutions:
        parts = _("Correct parts in your answer: ")
        matches = difflib.SequenceMatcher(None, value, solution).get_matching_blocks()
        i = 0
        for match in matches:
            parts += '-' * (match.b - i)
            i = match.b + match.size
            parts += value[match.a:match.a + match.size]
        matching_parts.append(parts)
    return matching_parts
