from functools import wraps
import flask_jwt_extended
from flask_jwt_extended import get_jwt
from flask import jsonify
import logging
from util.flask_util import inject_environment
from flask import request
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_jwt_extended.exceptions import InvalidHeaderError
from re import split

REGISTERED_ACCESS_DECORATORS = {}


@inject_environment({"SSO_ENABLED": "True" })
def is_sso_enabled(sso_enabled: str) -> bool:
    return sso_enabled in [ "True", "TRUE", "true" ]

def get_rules(blueprint):
    from flask import Flask
    temp_app = Flask(__name__)
    temp_app.register_blueprint(blueprint)
    return [p for p in temp_app.url_map.iter_rules()]


def get_urls(blueprint):
    rules = get_rules
    return [str(p) for p in rules]


def has_jwt_group(group_name):
    jwt = get_jwt()
    logging.debug(f"JWT: {jwt}")
    return group_name in jwt['groups']


def is_user_in_request() -> bool:
    return bool(get_username())

def get_username():
    jwt = get_jwt()
    return jwt['winaccountname']

def get_user():
    jwt = get_jwt()
    return { "username": jwt['winaccountname'], "groups": jwt['groups'] }


def extract_jwt(parameter_name="access_token"):

    def wrapper(fn):

        @wraps(fn)
        def decorator(*args, **kwargs):
            print(request.args)

            return fn(*args, **kwargs)

        return decorator

    return wrapper


def verify_jwt_in_request():
    flask_jwt_extended.verify_jwt_in_request(optional=False, fresh=False, refresh=False, locations=None)


def user_required():

    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):

            if is_sso_enabled():
                verify_jwt_in_request()

            if not is_sso_enabled() or is_user_in_request():
                return fn(*args, **kwargs)
            else:
                return jsonify(msg=f"Keine Berechtigung."), 403

        return decorator

    return wrapper


def verify_username(username: str) -> bool:
    return not is_sso_enabled() or username == get_username()

def app_required(apptoken_list):

    def wrapper(fn):

        @wraps(fn)
        def decorator(*args, **kwargs):
            if not has_valid_apptoken_in_request(apptoken_list):
                return jsonify(msg=f"Keine Berechtigung."), 403

            return fn(*args, **kwargs)

        return decorator

    return wrapper


def has_valid_apptoken_in_request(apptoken_list):
    apptoken = _decode_apptoken_from_headers()
    return apptoken in apptoken_list


def _decode_apptoken_from_headers():
    header_name = "Authorization"
    header_type = "Bearer"

    # Verify we have the auth header
    auth_header = request.headers.get(header_name, "").strip().strip(",")
    if not auth_header:
        raise NoAuthorizationError(f"Missing {header_name} Header")

    # Make sure the header is in a valid format that we are expecting, ie
    # <HeaderName>: <HeaderType(optional)> <JWT>.
    #
    # Also handle the fact that the header that can be comma delimited, ie
    # <HeaderName>: <field> <value>, <field> <value>, etc...
    if header_type:
        field_values = split(r",\s*", auth_header)
        apptoken_headers = [s for s in field_values if s.split()[0] == header_type]
        if len(apptoken_headers) != 1:
            msg = (
                f"Missing '{header_type}' type in '{header_name}' header. "
                f"Expected '{header_name}: {header_type} <APPTOKEN>'"
            )
            raise NoAuthorizationError(msg)

        parts = apptoken_headers[0].split()
        if len(parts) != 2:
            msg = (
                f"Bad {header_name} header. "
                f"Expected '{header_name}: {header_type} <APPTOKEN>'"
            )
            raise InvalidHeaderError(msg)

        encoded_token = parts[1]
    else:
        parts = auth_header.split()
        if len(parts) != 1:
            msg = f"Bad {header_name} header. Expected '{header_name}: <APPTOKEN>'"
            raise InvalidHeaderError(msg)

        encoded_token = parts[0]

    return encoded_token
