import os
from pathlib import Path
from python_utils.env import inject_environment
import sys

FOUND_APPLICATION_PATH: str = ""

def lookup_application_path() -> str:
    global FOUND_APPLICATION_PATH

    if FOUND_APPLICATION_PATH:
        return FOUND_APPLICATION_PATH

    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        FOUND_APPLICATION_PATH = os.path.dirname(sys.executable)
    else:
        this_script_directory = os.path.dirname(os.path.realpath(__file__))
        FOUND_APPLICATION_PATH = os.path.realpath(path_until_last_match(this_script_directory, "venv"))

    return FOUND_APPLICATION_PATH


def path_until_last_match(path: str, match: str) -> str:
    position = path.rfind(match)
    if position == -1:
        raise Exception(f"'{match}' not found in path: '{path}'")
    return path[:position]


@inject_environment({"APPLICATION_PATH": ""})
def get_application_path(application_path: str) -> str:
    return application_path or lookup_application_path()


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
