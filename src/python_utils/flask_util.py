import os
from functools import wraps
from flask import Flask, Response
import json

init_service_functions = []


def init_service(init_service_function):
    init_service_functions.append(init_service_function)


def init_services(app: Flask):
    for init_service_function in init_service_functions:
        init_service_function(app)


init_endpoint_functions = []


def init_endpoints(flask: Flask):
    with flask.app_context():
        for init_function in init_endpoint_functions:
            init_function()


def init_endpoint(init_function):
    init_endpoint_functions.append(init_function)


def inject_environment(environment_variables : {}, required=False):

    def wrapper(init_function):

        @wraps(init_function)
        def decorator(*args, **kwargs):
            environment_values = lookup_environment_variables(environment_variables, required)
            return init_function(*environment_values, **kwargs)

        return decorator

    return wrapper


def lookup_environment_variables(environment_variables : [], required: bool) -> []:

    values = []
    for environment_variable_name in environment_variables:
        value = os.getenv(key=environment_variable_name, default=environment_variables[environment_variable_name])
        if not value and required:
            raise Exception(f"Missing {environment_variable_name}")
        values.append(value)

    return values


def object_to_json(object):
    return json.dumps(object, ensure_ascii=False, indent=2, sort_keys=True).encode(encoding='utf-8')


def response_json(object):
    json = object_to_json(object)
    response = Response(json, mimetype='application/json')
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


def response_text(text: str):
    response = Response(text, mimetype='text/plain')
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


def response_cookie(cookie_name: str, cookie_value: str):
    response = Response()
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.set_cookie(key=cookie_name, value=cookie_value)
    return response


def lookup_file(relative_path: str) -> str:
    script_directory = os.path.dirname(os.path.realpath(__file__))
    return os.path.abspath(f"{script_directory}/{relative_path}")


def lookup_directory(relative_path: str, ignore_not_found=False):
    directory=lookup_file(relative_path)
    if not os.path.isdir(directory) and not ignore_not_found:
        raise Exception(f"Directory not found: {directory}")

    return directory



