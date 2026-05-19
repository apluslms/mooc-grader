# This module is adapted from mooc-grader/scripts/docker-run.py.
# This module copies the directories, which should be mounted to
# the grading container, to the path /tmp/aplus. This is required because
# Docker does not support bind mounts from a container into another container.
# The bind mount directory must be located in the host (outside containers).
# The path /tmp/aplus must be mounted from the host into the run-mooc-grader
# container (in docker-compose.yml).

import logging
from typing import Any, Dict, Tuple
import os
import os.path
import shutil

import docker
docker_client = docker.from_env()

from access.config import ConfigError


logger = logging.getLogger("runner.docker")


def get_host_path_and_copy(mounts: Dict[str, str], path: str, submission_id: str):
    path = os.path.realpath(path)
    for k,v in mounts.items():
        if path.startswith(k):
            host_path = path.replace(k, v, 1)
            # host_path is under /tmp/aplus
            # submission_id is inserted into the host_path so that the path
            # does not collide with other submissions in case their grading
            # is running simultaneously.
            host_path = os.path.join(v, submission_id, os.path.relpath(host_path, v))
            if os.path.isfile(path):
                os.makedirs(os.path.dirname(host_path), mode=0o777, exist_ok=True)
                shutil.copy2(path, host_path)
            else:
                shutil.rmtree(host_path, ignore_errors=True)
                shutil.copytree(path, host_path, dirs_exist_ok=True)
            return host_path

    raise ConfigError(f"Could not find where {path} is mounted")


def run(
        submission_id: str,
        host_url: str,
        readwrite_mounts: Dict[str, str],
        readonly_mounts: Dict[str, str],
        image: str,
        cmd: str,
        settings: Dict[str, Any],
        **kwargs,
        ) -> Tuple[int, str, str]:
    """
    Grades the submission asynchronously and returns (return_code, out, err).
    out and err as in stdout and stderr output of a program.
    """
    network = settings.get("network")
    if "mounts" not in settings:
        return 1, "", 'Missing "mounts" in settings!'

    volumes = {
        get_host_path_and_copy(settings["mounts"], k, submission_id): {"bind": v, "mode": "rw"}
        for k,v in readwrite_mounts.items()
    }
    volumes.update({
        get_host_path_and_copy(settings["mounts"], k, submission_id): {"bind": v, "mode": "ro"}
        for k,v in readonly_mounts.items()
    })

    try:
        container = docker_client.containers.run(
            image,
            cmd,
            network = network if network else "bridge",
            remove = True,
            detach = True,
            environment = {
                "SID": submission_id,
                "REC": host_url,
            },
            volumes = volumes,
        )

        return 0, f"{', '.join(container.image.tags)} - {container.name} - {container.short_id}", ""
    except Exception as e:
        logger.exception("An exception while trying to run grading container")
        return 1, "", str(e)
