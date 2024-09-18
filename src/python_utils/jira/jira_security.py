import json
import uuid
from functools import wraps
from typing import Dict

from flask import jsonify, request
from python_utils.flask.shared import shared_dict
from python_utils.file import file_exists

authenticated_tokens = shared_dict()


def token_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            if not is_logged_in():
                return jsonify(msg=f"Access denied without valid token."), 403
            return fn(*args, **kwargs)

        return decorator

    return wrapper


def is_logged_in() -> bool:
    auth_id = get_auth_id_from_header_or_cookie()
    return auth_id and auth_id in authenticated_tokens


def logout():
    auth_id = get_auth_id_from_header_or_cookie()
    if not auth_id or auth_id not in authenticated_tokens:
        raise Exception("Logout failed: Not logged in?")

    del authenticated_tokens[auth_id]


def get_access_token() -> str:
    auth_id = get_auth_id_from_header_or_cookie()
    token = authenticated_tokens[auth_id]
    return token


def get_auth_id_from_header_or_cookie() -> str:
    auth_id = request.headers.get("Authorization")
    if not auth_id:
        auth_id = request.cookies.get("auth_id")

    return auth_id


def register_token(token: str) -> str:
    if not token:
        raise Exception("Missing token")

    auth_id = str(uuid.uuid4())
    authenticated_tokens[auth_id] = token

    return auth_id


def read_tokens(filename: str) -> Dict:
    if not file_exists(filename):
        return {}

    with open(filename, "r") as file:
        persistent_tokens = json.load(file)
        for auth_id in persistent_tokens:
            authenticated_tokens[auth_id] = persistent_tokens[auth_id]


def write_tokens(filename: str):
    persistent_tokens = {}
    for auth_id in authenticated_tokens:
        persistent_tokens[auth_id] = authenticated_tokens[auth_id]

    with open(filename, "w") as file:
        json.dump(persistent_tokens, file)
