* For installation, see /README.md
* For exercise configuration, see /exercises/README.md

# Grader Filesystem Walkthrough

* `/doc`: Description of the system and material for system administrators.

* `/grader`: Django project settings, urls and wsgi accessor.

* `/templates`: Base templates for default grader pages.

* `/static`: Statical files for default grader pages.

* `/access`: Django application presenting exercises and accepting submissions.

	* `templates`: Default view and grading task templates.

	* `types`: Implementations for different exercise view types.

	* `management`: Commandline interface for testing configured exercises.

* `/util`: Utility modules for HTTP, shell, filesystem access etc.

* `/exercises`: Course directories holding exercise configuration and material.

	* `sample_course`: Different exercise types sampled.

* `/scripts`: Shell scripts that different grading actions utilize.

* `/uploads`: Asynchronous graders store submission data in unique directories here.
	After accepting submission a `user` subdirectory holds the user data.
	Grading actions get this directory as a parameter and can change the
	contents. When grading is finished and feedback sent the submission
	data is removed and submission is completely forgotten.
