# Orders a container using docker run command. Prerequisites:
# 1. Docker is installed on the computer.
# 2. Mooc-grader must listen at public IP (e.g. runserver 0.0.0.0:8080).
#
# The container must make an HTTP POST request including fields
# points, max_points, and feedback (HTML) to $REC/container-post.
#
# RUNNER_MODULE settings:
#   network: the network under which to run the container. Must be the same network
#       as mooc-grader is running on, if it is running in a container.
#   mount: dictionary of absolute container (mooc-grader) paths to absolute host paths. Must
#       contain enough information to determine locations of exercise, submission and
#       personalized directories. omit or set to {"/": "/"} if running mooc-grader outside a container

import logging
from typing import Any, Dict, Tuple
import os.path

import docker
docker_client = docker.from_env()

from access.config import ConfigError


logger = logging.getLogger("runner.docker")


def host_path(mounts: Dict[str, str], path: str):
    path = os.path.realpath(path)
    for k,v in mounts.items():
        if path.startswith(k):
            return path.replace(k, v)

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
        settings["mounts"] = {"/": "/"}

    volumes = {
        host_path(settings["mounts"], k): {"bind": v, "mode": "rw"}
        for k,v in readwrite_mounts.items()
    }
    volumes.update({
        host_path(settings["mounts"], k): {"bind": v, "mode": "ro"}
        for k,v in readonly_mounts.items()
    })

    try:
        docker_client.containers.run(
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

        return 0, "", ""
    except Exception as e:
        logger.exception("An exception while trying to run grading container")
        return 1, "", str(e)
