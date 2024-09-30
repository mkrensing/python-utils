import os
import yaml
from python_utils.file import lookup_file

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

    env_vars = {}
    for key, value in config.items():
        env_vars[key] = str(value)

    for key, value in env_vars.items():
        env_vars[key] = replace_placeholders(value, env_vars)

    for key, value in env_vars.items():
        os.environ[key] = value