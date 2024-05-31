from flask import request, jsonify
from functools import wraps

AUTHPROXY_CLIENT_ID_COOKIE_NAME = "authproxy-clientid"

def valid_client():

    def wrapper(fn):

        @wraps(fn)
        def decorator(*args, **kwargs):
            client_id = get_client_id()

            if client_id:
                return fn(*args, **kwargs)
            else:
                return jsonify(msg="Client required"), 400

        return decorator

    return wrapper


def get_client_id():
    return request.cookies.get(AUTHPROXY_CLIENT_ID_COOKIE_NAME, "")