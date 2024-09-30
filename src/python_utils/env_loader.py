import os
import yaml
from python_utils.file import lookup_file
from typing import Dict

def replace_placeholders(value, env_vars):

    while any(f"{{{key}}}" in value for key in env_vars):
        for key, val in env_vars.items():
            value = value.replace(f"{{{key}}}", val)

    return value


def load_from_file(relative_filename: str, ignore_not_found=False):

    filename = lookup_file(relative_filename)

    if not os.path.isfile(filename):
        if ignore_not_found:
            return
        raise Exception(f"File not found: {filename}")

    with open(filename, 'r') as file:
        config = yaml.safe_load(file)
        load_from_dict(config)


def load_from_dict(yaml_dict: Dict):

    env_vars = {}
    for key, value in yaml_dict.items():
        env_vars[key] = str(value)

    for key, value in env_vars.items():
        os.environ[key] = value

    for key, value in env_vars.items():
        env_vars[key] = replace_placeholders(value, os.environ)

    for key, value in env_vars.items():
        if value.startswith("file:"):
            filename = value.split("file:")[1]
            with open(filename, 'r') as file:
                os.environ[key] = file.read()
        else:
            os.environ[key] = value