from .parser import Parser


class Course:

    def __init__(self, course_dir):
        self._DIR = course_dir
        self._data = dict()
        self._config_files = dict()
        self._exercise_keys = list()
        self._default_lang = None

    def load(self, index_rel_path):
        parser = Parser(self._DIR)
        index = parser.parse(index_rel_path)
        index = parser.process_include(index)
        keys, configs = parser.collect_exercise_keys(index)

        config_files = {
            key: parser.parse(path)
            for key, path in configs.items()
            }

        self._data = index
        self._config_files = config_files
        self._exercise_keys = keys
        default_lang = index.get("language", None)
        if isinstance(default_lang, list):
            default_lang = default_lang[0]
        self._default_lang = default_lang

    def get_data(self):
        return self._data

    def get_exercise_keys(self):
        return self._exercise_keys

    def get_config_files(self):
        return self._config_files

    def get_def_lang(self):
        return self._default_lang
