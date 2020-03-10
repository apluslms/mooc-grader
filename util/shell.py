'''
Utility functions to handle shell processes.

'''
from django.conf import settings
from access.config import ConfigError
import subprocess
import logging
import os.path


LOGGER = logging.getLogger('main')


def invoke(cmd_list, cwd=None):
    '''
    Invokes a shell command.

    @type cmd_list: C{list}
    @param cmd_list: command line arguments
    @type cwd: C{str}
    @param cwd: set current working directory for the command, None if not used
    @rtype: C{dict}
    @return: code = process return code, out = standard out, err = standard error
    '''
    LOGGER.debug('Subprocess %s', cmd_list)
    p = subprocess.Popen(cmd_list, universal_newlines=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    out, err = p.communicate()
    return {"code": p.returncode, "out": out.strip(), "err": err.strip()}


def invoke_script(script, arguments, dirarg=None):
    '''
    Invokes a named shell script.

    @type script: C{str}
    @param script: a script file name
    @type arguments: C{dict}
    @param arguments: arguments to pass for the script
    @type dirarg: C{str}
    @param dirarg: a submission directory to grade
    @rtype: C{dict}
    @return: code = process return code, out = standard out, err = standard error
    '''
    cmd = [ script ]
    for key, value in arguments.items():
        cmd.append("--%s" % (key))
        cmd.append("%s" % (value))
    if dirarg is not None:
        cmd.append("--dir")
        cmd.append(dirarg)
    return invoke(cmd)

