from flask import request, jsonify
from functools import wraps
from python_utils.env import inject_environment


@inject_environment({"CLIENT_TOKEN": ""}, required=True)
def get_correct_client_token(client_token: str):
    return client_token


def valid_token():
    def wrapper(fn):

        @wraps(fn)
        def decorator(*args, **kwargs):
            if verify_client_token():
                return fn(*args, **kwargs)
            else:
                return jsonify(msg="Access Denied"), 403

        return decorator

    return wrapper


def verify_client_token() -> bool:
    return get_client_token() == get_correct_client_token()


def get_client_token():
    return request.headers.get("Authorization", "")
