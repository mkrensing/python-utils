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
        FOUND_APPLICATION_PATH = find_directory_containing_file(os.path.dirname(sys.argv[0]), "requirements.txt")
        if not FOUND_APPLICATION_PATH:
            FOUND_APPLICATION_PATH = os.path.dirname(sys.argv[0])

    return FOUND_APPLICATION_PATH

def find_directory_containing_file(current_path: str, filename: str) -> str:
    while True:
        file_candidate = os.path.join(current_path, filename)
        if os.path.isfile(file_candidate):
            return current_path
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:
            return None # Root reached

def contains(path: str, match: str) -> bool:
    return path.rfind(match) > -1

def path_until_last_match(path: str, match: str) -> str:
    position = path.rfind(match)
    if position == -1:
        return ""

    return path[:position]


@inject_environment({"APPLICATION_PATH": ""})
def get_application_path(application_path: str) -> str:
    return application_path or lookup_application_path()


def lookup_file(relative_path: str) -> str:
    application_path = get_application_path()
    return os.path.abspath(f"{application_path}/{relative_path}")


def lookup_directory(relative_path: str, ignore_not_found=False):
    directory = lookup_file(relative_path)
    if not os.path.isdir(directory) and not ignore_not_found:
        raise Exception(f"Directory not found: {directory}")

    return directory


def file_exists(path: str) -> bool:
    return Path(path).is_file()
