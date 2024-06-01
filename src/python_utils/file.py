import os
from pathlib import Path
from python_utils.env import inject_environment
import sys


def lookup_application_path() -> str:
    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)

    this_script_directory = os.path.dirname(os.path.realpath(__file__))
    return f"{this_script_directory}/../../"


@inject_environment({"APPLICATION_PATH": lookup_application_path()})
def get_application_path(application_path: str) -> str:
    return application_path


def lookup_file(relative_path: str) -> str:
    application_path = get_application_path()
    return os.path.abspath(f"{application_path}/{relative_path}")


def lookup_directory(relative_path: str):
    directory = lookup_file(relative_path)
    if not os.path.isdir(directory):
        raise Exception(f"Directory not found: {directory}")

    return directory


def file_exists(path: str) -> bool:
    return Path(path).is_file()
