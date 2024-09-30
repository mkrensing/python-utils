import os

from python_utils.env_loader import load_from_dict

config = {
    "APPLICATION_PATH": "./",
    "TOKEN": "file:{APPLICATION_PATH}/token.txt",
    "MY_HOME": "{HOME}"
}

load_from_dict(config)
assert os.environ["TOKEN"] == "<geheim>"
assert os.environ["MY_HOME"] == os.environ["HOME"]
