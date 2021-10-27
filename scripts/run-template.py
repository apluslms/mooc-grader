# Implement the run function below to create a submission grading script
# raise ConfigError in case of a configuration error (do not catch it)

import logging
from typing import Any, Dict, Optional, Tuple

from access.config import ConfigError


logger = logging.getLogger("runner.template")


def run(
        course: Dict[str, Any],
        exercise: Dict[str, Any],
        container_config: Dict[str, Any],
        submission_id: str,
        host_url: str,
        exercise_dir: str,
        submission_dir: str,
        personalized_dir: str,
        image: str,
        cmd: str,
        settings: Any,
        **kwargs,
        ) -> Tuple[int, str, str]:
    """
    Grades the submission asynchronously and returns (return_code, out, err).
    out and err as in stdout and stderr output of a program.

    **kwargs is recommended for the case that more arguments are added later.
    """
    try:
        # implement here
        ...
    except Exception as e:
        logger.exception("An exception while trying to run grading container")
        return 1, "", str(e)