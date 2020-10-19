Course and exercise configuration
=================================

## Configuration files

Configuration is written as JSON or YAML inside subdirectories.
Each subdirectory holding an `index.json` or `index.yaml` is a
valid active course.

Dates will be parsed as '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S',
'%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d %H' or '%Y-%m-%d'.
Durations are given in (int)(unit), where units are y, m, d, h or w.

1. ### course_key/index.[json|yaml]
	* The directory name acts as a course key, which is used in
		* URLs: `/course_key`
	* `name`: A public complete course name
	* `description` (optional): A private course description
	* `lang` (optional/a+): The default language.
	* `contact`: (optional/a+) A private contact email for course configuration
	* `contact_phone`: (optional) A private contact phone number for course responsible
	* `assistants`: (optional/a+) A list of assistant student ids
	* `start`: (optional/a+) The course instance start date
	* `end`: (optional/a+) The course instance end date
	* `static_dir`: (optional) This subdirectory will be linked to URL /static/course_key
	* `head_urls`: (optional/a+) A list of URLs to JS and CSS files that A+ includes
		on all course pages. For example, a common JavaScript library could be included
		this way without adding it separately to each exercise description.
	* `enrollment_start`: The enrollment start date
	* `enrollment_end`: The enrollment end date
	* `lifesupport_time`: The lifesupport date (model answers are hidden from students)
	* `archive_time`: The archive date (no submissions allowed after it)
	* `enrollment_audience`: Selects the user group that is allowed to enroll in the course. One of the following:
		* `internal`: only internal students
		  (they have a student number and should log-in with internal accounts)
		* `external`: only external students (no student number and login with Google accounts)
		* `all`: internal and external students
	* `view_content_to`: Selects the user group that may view course contents. One of the following:
		* `enrolled`: only enrolled students
		* `enrollment_audience`: logged-in users in the enrollment audience (the audience is set separately)
		* `all_registered`: all logged-in users
		* `public`: all anonymous and authenticated users
	* `index_mode`: Selects the display mode for the course front page. One of the following:
		* `results`: exercise results
		* `toc`: table of contents
		* `last`: opens the page that the user viewed last time
		* `experimental`: do not use this
	* `content_numbering`: numbering mode for the course contents (chapters and exercises). One of the following:
		* `none`: no numbers shown
		* `arabic`: arabic numbers (1, 2, 3)
		* `roman`: roman numbers (I, II, III)
		* `hidden`: no numbers, but child objects may show the hierarchy in numbering.
			If there are children (e.g., exercises are children of the module) and
			the parent has hidden numbering, then the children may have numbers
			such as "1.2" instead of just "2" (exercise 2 in the round 1).
			The hidden setting is more sensible in `module_numbering` than `content_numbering`.
	* `module_numbering`: numbering mode for the modules (exercise rounds).
		The options are the same as for `content_numbering`.
	* `course_description`: HTML text for the course front page
	* `course_footer`: HTML text for the footer of the front page
	* `exercises`: (deprecated, see modules) A list of active exercise keys
	* `modules`: a list of
		* `key`: part of the url
		* `name`,`title`: (optional/a+) The name of the course module
		* `status`: (optional/a+) ready/hidden/maintenance
		* `points_to_pass`: (optional/a+) limit to get passed marks
		* `introduction`: (optional/a+) introduction
		* `open`: (optional/a+) first access date
		* `close`: (optional/a+) deadline date
		* `duration`: (optional/a+) deadline in duration from open
		* `late_close`: (optional/a+) late deadline date
		* `late_duration`: (optional/a+) late deadline in duration from first deadline
		* `late_penalty`: (optional/a+) factor of points worth for late submission
		* `type`: (optional/a+) a key name in 'module_types'
		* `children`: a list of
			* `key`: part of the url
			* `config`: a path to exercise configuration OR
			* `static_content`: a path inside static directory
			* `category`: a key name in 'categories'
			* `name`,`title`: (optional/a+) The name of the learning object
			* `status`: (optional/a+) ready/unlisted/hidden/maintenance
			* `max_submissions`: (optional/a+)
			* `max_points`: (optional/a+)
			* `points_to_pass`: (optional/a+) limit to get passed marks
			* `min_group_size`: (optional/a+)
			* `max_group_size`: (optional/a+)
			* `allow_assistant_viewing`: (optional/a+) true or false
			* `allow_assistant_grading`: (optional/a+) true or false
			* `use_wide_column`: (optional/a+) true to loose third column
			* `generate_table_of_contents`: (optional/a+) show index of children
			* `type`: (optional/a+) a key name in 'exercise_types'
			* `children`: list recursion
	* `categories`: a list of
		* `name`: (optional/a+)
		* `status`: (optional/a+) ready/hidden
		* `points_to_pass`: (optional/a+) limit to get passed marks
	* `module_types`,`exercise_types`: keyed maps of default values
	* `numerate_ignoring_modules`: (optional/a+) true to numerate I:1...n, II:n+1...m

2. ### course_key/exercise_key.[json|yaml]
	* The file name acts as an exercise key, which is used in
		* URLs: `/course_key/exercise_key`
		* Must match the exercise list in `index.[json|yaml]`
	* `title`: A title of the exercise
	* `description` (optional): An exercise description (Dublin Core metadata)
	* `include` (optional): Include configuration files rendered from templates.
		* `file`: A path to an exercise configuration file. May contain optional Django template syntax, which allows passing of parameters with the `template_context` key.
		* `force` (optional): Defaults to false. If true, all keys and their contents in the file where the `include` key is located will be overwritten with the corresponding keys and contents from the file which is being included. If false, a ConfigError is thrown if the include file contains keys which already exist in the file where the keys are being included.
		* `template_context` (optional): Context dictionary containing key value pairs for rendering the included file.
	* `instructions` (optional): Most default templates will print given
		instructions HTML before the exercise widgets.
	* `instructions_file` (optional): Like above but is a path to an HTML file to be included.
    If the path starts with `./`, it will be prepended with the course key.
    If both `instructions` and `instructions_file` are given,
		`instructions` will be placed before the content of `instructions_file`.
	* `max_points` (optional): The maximum exercise points (positive int).
		Overrides any maximum points reported by test actions.
	* `feedback`: If true, the exercise is a feedback exercise/questionnaire.
	* `view_type`: A dotted name for an exercise implementation
	* `submission_file_max_size`: (optional/Moodle frontend only) maximum accepted file size
		for submissions (in bytes). The limit is checked for each file separately if
		there are multiple files in a submission. Set zero for no limit.
		Default value is 1048576 (1 MB). Moodle has sitewide configuration for
		the maximum upper limit which cannot be exceeded.
	* `personalized`: (optional) if true, personalized exercise instances must
		be pregenerated and each user is then assigned an instance of the exercise
	* `generated_files`: (required if personalized) set a list of generated files
		for a personalized exercise. Each list item defines the following settings:
		* `file`: filename of the generated file
		* `key`: key for accessing the file in HTML templates
		* `url_in_template`: if true, template variable includes a URL to download
		   the generated file
		* `content_in_template`: if true, template variable includes the content
		   of the generated file
		* `allow_download`: if true, the generated file can be downloaded from the web
	* `generator`: (required if personalized) settings for the generator program that
		creates one new instance of the exercise. At least `cmd` must be set. The generator
		cmd will be run from course_key dir (course_key is the cwd).
		* `cmd`: command line as an ARRAY that is used to run the generator.
			Eg. ["generator_script.sh"] will run generator_script.sh from course_key dir
			and ["python3", "script_dir/generator.py"] will run generator.py from
			course_key/script_dir but keep course_key as cwd.
			Mooc-grader appends the instance directory path to the argument list and
			the generator is expected to write files into the directory. The file names
			should be listed under `generated_files` setting so that mooc-grader is aware
			of them. The Django command used to pregenerate exercises is
			`python manage.py pregenerate_exercises course_key <exercise_key>`
			(`--help` option prints all possible arguments).
		* `cwd`: if set, this sets the current working directory for the generator
			program. Since the default cwd is course_key, this applies to directories
			in course_key. Eg. cwd: "script_dir" will change the cwd to course_key/script_dir
			and only after that run cmd.
	* `max_submissions_before_regeneration`: (optional, only usable in personalized exercises)
		defines how many times the student may submit before the personalized exercise is
		regenerated (the exercise instance is changed to another one). If unset,
		the exercise is never regenerated.
	* `model_files`: It is a list of model answers that are available only after the deadline has passed.
		The `model_files` take file paths as input. These paths are relative to the root of the course repository,
		e.g., `exercises/hello_world/model.py`.

	Rest of the attributes are exercise type specific.

## Exercise view types

Common exercise views are implemented in `access.types` and they should fit most
purposes by configuration and templating. However, it is possible to implement a
course specific exercise view in a course specific Python module.

1. ### access.types.stdasync.acceptFiles
	Accepts named files for asynchronous grading queue. Extended attributes:
	* `files`: list of expected files
		* `field`: file field name
		* `name`: actual file name, may include subdirectories
		* `required`: (optional, default true) if true, the user must submit this file,
			otherwise it can be left empty
	* `required_number_of_files`: (optional, integer) if not all files are required,
		define how many files must be submitted. The number should be less than the
		length of the `files` list.
	* `template` (default `access/accept_files_default.html`):
		name of a template to present
	* `accepted_message` (optional): overrides the default message displayed when
		asynchronous submission is accepted
	* `never_wait` (optional): true stops the automatic feedback polling for
		asynchronous submissions (normally occurs if queue is shorter than 3)
	* `feedback_template` (default `access/task_success.html`):
		name of a template used to format the feedback
	* `container`: A dictionary for configuring attributes of the grading container
		* `image`: Container image to use
		* `mount`: Directory to mount to the container
		* `cmd`: Command to execute inside the grading container - typically along the lines of `/exercise/run.sh`

	Additional fields can be defined in the `container` dictionary, and they're given to the **site-specific** container creation script. **Aalto's installation** currently accepts the following fields:

	*   * `resources` (optional): A dictionary defining resource limits for the container, with the following keys:
			* `cpu` (optional, default `2`): Number of CPU cores to allocate
			* `memory` (optional, default `4Gi`): Amount of memory to allocate
		* `enable_network` (optional, default `False`): Whether the container should have generic network access
		* `require_constant_environment` (optional, default `False`): Generally used for timed exercises where the number of points received depends on code execution time. Setting this to `True` causes the containers to end up in an environment where only one submission is run at a time, and all the grading nodes have identical hardware, so the variance in execution times should be minimal.
		* `privileged` (optional, default `False`): Setting this to `True` essentially grants root access to the grading node where the container is run. This can be needed e.g. in exercises requiring access to `/dev/kvm` or docker-in-docker exercises. Privileged submissions are run on a separate node entirely dedicated to them. This should generally be used as a **last resort**, and the exercise creator should make sure that student code cannot escape the container.

2. ### access.types.stdasync.acceptPost
	Accepts form text for asynchronous grading queue. Extended attributes:
	* `fields`: list of text fields
		* `name`: field name and written file name
		* `title` (optional): field title or label
		* `more` (optional): more instructions
		* `required` (optional): `true` to require an answer
	* `template` (default `access/accept_post_default.html`):
		name of a template to present
	* `accepted_message` etc as in type 1.

3. ### access.types.stdasync.acceptGitAddress
	Writes the Git address into user/gitsource file for asynchronous grading
	queue. See grader.actions.git*. Extended attributes:
	* `require_gitlab` (optional):
		a host name for a Gitlab installation.
		Makes sure that the address is an SSH repo path or any HTTP URL
		in given Gitlab host. Stores the standard SSH path for key access.
	* `template` (default: `access/accept_git_default.html`):
		name of a template to present
	* `accepted_message` etc as in type 1.

5. ### access.types.stdsync.acceptGeneralForm
	Accepts a general form submission (can also include files) asynchronous
	grading queue. Extended attributes:
	* `files`: list of expected files as in type 1
	* `fields`: list of text fields as in type 2
	* `template` (default `access/accept_general_default.html`):
		name of a template to present
	* `accepted_message` etc as in type 1.

6. ### access.types.stdsync.createForm
	Synchronous form checker. Requires `max_points` in the
	exercise configuration. If form has no points configured then maximum
	points are granted on errorless submission. Extended attributes:
	* `fieldgroups`: list of field groups
		* `name` (optional): group name (fieldset legend)
		* `pick_randomly` (optional): number of fields to randomly sample
		* `resample_after_attempt` (optional): boolean. Should the questions be
			resampled or preserved after a submission attempt in a `pick_randomly`
			questionnaire? `true` by default, which means that the questions are
			resampled after attempts.
		* `group_errors` (optional): `true` to hide individual failed fields
		* `fields`: list of fields
			* `title` (optional): field title or label
			* `more` (optional): more instructions
			* `include` (optional): template name to include
				as content in more instructions
			* `type`: `radio`/`checkbox`/`dropdown`/`text`/`textarea`
			* `key` (optional): a field key used in the form post
			* `initial` (optional): an initial value for the field
			* `points` (optional): number of points to grant
			* `required` (optional): `true` to require an answer
			* `correct` (optional): correct answer for text fields
			* `compare_method` (optional): `int`/`float`/`string`/`regexp`/`string-(modifier)`/`subdiff-(modifier)`
				Decides how posted value is compared to correct and feedback. The `subdiff`
				method works like `string`, but it can have multiple correct solutions delimited
				with `|` and it shows the difference of the submission compared
				to the correct solutions as feedback.
				Modifiers include:
				* `ignorews`: ignore white space
				* `ignorequotes`: iqnore "quotes" around
				* `requirecase`: require identical lower and upper cases
				* `ignorerepl`: ignore REPL prefixes
			* `regex` (deprecated): regex to match correct answer for text fields (use compare_method instead)
			* `options` list of options for choice fields
				* `label`: option label
				* `value` (optional): the unique value for the option in the form post
				* `selected` (optional): `true` to make this initial selection
				* `correct` (optional): `true` for correct option. "neutral" for neutral
					options that do not affect grading (in checkbox questions).
					Checkbox requires all and only correct
					options selected. Radio requires one of
					the correct options selected.
			* `partial_points`: if true, a checkbox question awards some points for partially correct answers
			* `feedback` (optional): list of feedback messages
				* `label`: the message
				* `value`: show when this value is posted
				* `not`: `true` to show when given value is NOT posted
				* `compare_regexp`: `true` to match the posted answer to the `value` as regexp
			* `randomized` (optional): int. The number of answer choices that are randomly
				selected out of all choices in a checkbox question.
			* `correct_count` (optional): int. Used with `randomized`. The number of
				correct answer choices that are randomly selected in a checkbox question.
			* `resample_after_attempt` (optional): boolean. Should the answer choices be
				resampled or preserved after a submission attempt in a `randomized`
				question? `true` by default, which means that the choices are resampled
				after attempts.
	* `template` (default `access/create_form_default.html`): name of a template to present
	* `accepted_message` (optional): overrides the default message displayed when
		submission is accepted
	* `reveal_model_at_max_submissions` (optional): if false, the questionnaire feedback
		does not reveal model solutions after the user has consumed all submission
		attempts. By default false.
	* `show_model_answer` (optional): if false, A+ does not show the model solution
		to students after the module deadline. (In other words, mooc-grader does
		not export a link to the model solution in aplus-json.) By default true.

7. ### access.types.stdsync.comparePostValues
	Synchronous check against posted values. Requires `max_points` in the
	exercise configuration. If values have no points configured then maximum
	points are granted on errorless submission. Extended attributes:
	* `values`: map of POST field names to rules:
		* `accept`: list of accepted values, [ False ] for no value, [ True ]
			for any value
		* `points` (optional): number of points to grant or negative to deduct
	* `template`: name of a template to present. Template should manually
		include a form that produces the expected POST values.

8. ### access.types.stdsync.noGrading
	Presents a template and does not grade anything. Extended attributes:
	* `template`: name of a template to present
	
## Templates

Many type views can use a named template. The templates can be placed in
exercise directory and use subdirectories. The available variables are
listed below.

1. ### All templates
	* `course`: course configuration dictionary
	* `exercise`: exercise configuration dictionary
	* If the exercise is personalized and the exercise settings include
		`generated_files`:
		* `generated_files`: dictionary with the keys defined in the settings,
			for each key there is the value for `file`, and with the enabled
			settings also `url` and `content`

	Note that you can add any new keys to configuration and utilize them in templates.

2. ### Templates for asynchronous submissions
	* `result`: object holding POST results or None
		* `error`: True on failed POST
		* `missing_url`: True if no submission_url provided
		* `missing_files`: True if files missing
		* `invalid_address`: True if Gitlab address is rejected
		* `accepted`: True if accepted for grading
		* `wait`: True if the grading should be finished in a moment
	A default file submission form can be included with

		{% include 'access/accept_files_form.html' %}

3. ### Feedback templates for asynchronous submissions
	* `result`: object holding test results
		* `points`: total points granted
		* `max_points`: total maximum points
		* `tests`: entry for each test action
			* `points`: points granted
			* `max_points`: maximum points
			* `out`: test output
			* `err`: test errors
			* `stop`: True when rest of the actions
				were cancelled

4. ### Templates for createForm
	* `result`: object holding form and results
		* `form`: a Django form object
		* `accepted`: True if valid form POST was graded
		* `points`: granted points
		* `error_groups`: list of group_N names having errors
		* `error_fields`: list of field_N names having errors
	A default form can be included with

		{% include 'access/graded_form.html' %}

5. ### Templates for comparePostValues
	* `result`: object holding POST results or None
		* `accepted`: True
		* `received`: map of received POST fields => values
		* `points`: granted points
		* `failed`: list of failed field names
