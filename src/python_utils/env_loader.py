import os
import yaml
from python_utils.file import lookup_file

def load_from_file(relative_filename: str, ignore_not_found=False):

    filename = lookup_file(relative_filename)

    if not os.path.isfile(filename):
        if ignore_not_found:
            return
        raise Exception(f"File not found: {filename}")

    with open(filename, 'r') as file:
        config = yaml.safe_load(file)

    for key, value in config.items():
        os.environ[key] = str(value)