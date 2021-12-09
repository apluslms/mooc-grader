'''
Utility functions for exercise files.

'''
from django.conf import settings
import datetime, random, string, os, shutil, json
from pathlib import Path
import tempfile
from typing import Iterable, Optional, Tuple, Union

from util.typing import PathLike

META_PATH = os.path.join(settings.SUBMISSION_PATH, "meta")
if not os.path.exists(META_PATH):
    os.makedirs(META_PATH)


def random_ascii(length, rng=None):
    if not rng:
        # Use the functions in the random module without manually creating
        # an instance of the random.Random class.
        rng = random
    return ''.join([rng.choice(string.ascii_letters) for _ in range(length)])

class SubmissionDir:
    def __init__(self, course, exercise):
        '''
        Creates a directory for a submission.

        @type course: C{dict}
        @param course: a course configuration
        @type exercise: C{dict}
        @param exercise: an exercise configuration
        @rtype: C{str}
        @return: directory path
        '''
        # Create a unique directory name for the submission.
        self.sid = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f") + random_ascii(5)
        self.subdir = Path(course["key"], exercise["key"], self.sid)

        # Create empty directory.
        self.dir().mkdir(parents=True, exist_ok=True)

    def dir(self, base_path=settings.SUBMISSION_PATH) -> Path:
        return Path(base_path, self.subdir)

    def save_file(self, file_name, post_file):
        '''
        Saves a submitted file to a submission directory.

        @type file_name: C{str}
        @param file_name: a file name to write
        @type post_file: C{django.core.files.uploadedfile.UploadedFile}
        @param post_file: an uploaded file to save
        '''
        file_path = self.file_path(file_name)
        with open(file_path, "wb+") as f:
            for chunk in post_file.chunks():
                f.write(chunk)

    def write_file(self, file_name, content):
        '''
        Writes a submission file to a submission directory.

        @type file_name: C{str}
        @param file_name: a file name to write
        @type content: C{str}
        @param content: content to write
        '''
        file_path = self.file_path(file_name)
        with open(file_path, "w+") as f:
            f.write(content)

    def read_file(self, file_name):
        file_path = self.file_path(file_name)
        with open(file_path, "r") as f:
            return f.read()

    def file_path(self, file_name):
        '''
        Creates a submission file path.

        @type file_name: C{str}
        @param file_name: a file name to write
        @rtype: C{str}
        @return: a submission file path
        '''
        if not is_safe_file_name(file_name):
            raise ValueError("Unsafe file name detected")
        file_path = self.dir() / 'user' / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path


def clean_submission_dir(submission_dir):
    '''
    Cleans a submission directory after grading.

    @type submission_dir: C{str}
    @param submission_dir: directory path
    '''
    if submission_dir.startswith(settings.SUBMISSION_PATH):
        shutil.rmtree(submission_dir)


def is_safe_file_name(file_name):
    '''
    Checks that a file name is safe for concatenating to some path.

    @type file_name: C{str}
    @param file_name: a file name
    @rtype: C{boolean}
    @return: True if file name is safe
    '''
    if file_name == "" or file_name == "." or file_name.startswith("/") or ".." in file_name:
        return False
    return True


def read_meta(file_path):
    '''
    Reads a meta file comprised of lines in format: key = value.

    @type file_path: C{str}
    @param file_path: a path to meta file
    @rtype: C{dict}
    @return: meta keys and values
    '''
    meta = {}
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            for key,val in [l.split('=') for l in f.readlines() if '=' in l]:
                meta[key.strip()] = val.strip()
    return meta


def _meta_dir(sid):
    return os.path.join(META_PATH, sid)


def write_submission_meta(sid, data):
    with open(_meta_dir(sid), "w") as f:
        f.write(json.dumps(data))


def read_and_remove_submission_meta(sid):
    p = _meta_dir(sid)
    try:
        with open(p, "r") as f:
            data = json.loads(f.read())
        os.unlink(p)
    except (OSError, ValueError):
        return None
    return data


def rm_path(path: Union[str, Path]) -> None:
    path = Path(path)
    if path.is_symlink():
        path.unlink()
    elif not path.exists():
        return
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _tmp_path(path) -> str:
    """
    returns a path to a temporary file/directory (same as <path>) in the same
    place as <path> with the name prefixed with <path>s name.

    May raise OSError.
    """
    dir, name = os.path.split(path)
    if os.path.isdir(path):
        tmp = tempfile.mkdtemp(prefix=name, dir=dir)
    else:
        fd, tmp = tempfile.mkstemp(prefix=name, dir=dir)
        os.close(fd)
    return tmp


def rename(src: PathLike, dst: PathLike, keep_tmp=False) -> Optional[str]:
    """
    renames a file or directory while making sure that the destination will only be removed if successful.
    Otherwise, returns a tmp path to dst (None if dst does not exist). Note that this file won't exist
    if keep_tmp = False.

    May raise OSError.
    """
    tmpdst = None

    src, dst = os.fspath(src), os.fspath(dst)
    if not os.path.exists(dst) or (os.path.isfile(dst) and os.path.isfile(src)):
        if keep_tmp and os.path.exists(dst):
            tmpdst = _tmp_path(dst)
            os.rename(dst, tmpdst)

        try:
            os.rename(src, dst)
        except OSError:
            if tmpdst:
                os.rename(tmpdst, dst)
            raise
    else:
        tmpdst = _tmp_path(dst)
        try:
            os.rename(dst, tmpdst)
            os.rename(src, dst)
        except OSError:
            os.rename(tmpdst, dst)
            raise
        else:
            if not keep_tmp:
                rm_path(tmpdst)

    return tmpdst


def renames(pairs: Iterable[Tuple[PathLike, PathLike]]) -> None:
    """
    Renames multiple files and directories while making sure that either all or none succeed.

    May raise OSError.
    """
    done = set()
    try:
        for src, dst in pairs:
            tmpdst = rename(src, dst, True)
            done.add((src, dst, tmpdst))
    except OSError:
        for src, dst, tmp in done:
            rename(dst, src)
            if os.path.exists(tmp):
                rename(tmp, dst)
        raise
    else:
        for _, _, tmp in done:
            if tmp is not None:
                rm_path(tmp)
