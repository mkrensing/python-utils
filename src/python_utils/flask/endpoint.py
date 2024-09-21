import atexit
import logging
from flask import Flask, Response, Blueprint, send_from_directory, request
from typing import Dict, Tuple
from python_utils.file import lookup_directory
import datetime
import json

init_service_functions = []
registered_endpoints = []
init_endpoint_functions = []
destroy_endpoint_functions = []

logger = logging.getLogger(__name__)

class Endpoint(Blueprint):

    def __init__(self, url_prefix: str, static_folder: str = ""):

        endpoint_name = self.get_endpoint_name(url_prefix)
        logger.debug(f"Loading Endpoint {endpoint_name}")

        if static_folder:
            static_folder = lookup_directory(static_folder)

        super().__init__(name=endpoint_name, import_name=__name__, url_prefix=url_prefix, static_folder=static_folder)
        register_endpoint(self)

    def send_file(self, sub_directory: str, filename: str) -> Response:
        return send_from_directory(directory=f"{self.static_folder}/{sub_directory}", path=filename)

    @staticmethod
    def get_endpoint_name(url_prefix: str) -> str:
        return f"{Endpoint.get_endpoint_id(url_prefix)}_endpoint"

    @staticmethod
    def get_endpoint_id(url_prefix: str) -> str:
        return url_prefix.replace('/', '_') or "main"


def init_service(init_service_function):
    init_service_functions.append(init_service_function)


def init_services(app: Flask):
    for init_service_function in init_service_functions:
        init_service_function(app)


def register_endpoints(flask: Flask):
    with flask.app_context():
        for endpoint in registered_endpoints:
            flask.register_blueprint(endpoint)


def register_endpoint(endpoint: Blueprint):
    registered_endpoints.append(endpoint)


def init_endpoints(flask: Flask):
    with flask.app_context():
        for init_function in init_endpoint_functions:
            init_function()


def init_endpoint(init_function):
    init_endpoint_functions.append(init_function)


def destroy_endpoints_on_exit(flask: Flask):
    import signal
    signal.signal(signal.SIGTERM, lambda *x: destroy_endpoints(flask))
    signal.signal(signal.SIGINT, lambda *x: destroy_endpoints(flask))
    atexit.register(lambda *x: destroy_endpoints(flask))


def destroy_endpoints(flask: Flask):
    print(f"destroy_endpoints: {destroy_endpoint_functions}")
    with flask.app_context():
        for destroy_function in destroy_endpoint_functions:
            destroy_function()


def destroy_endpoint(destroy_function):
    destroy_endpoint_functions.append(destroy_function)


def response_json(some_object) -> Response:
    response = Response(object_to_json(some_object), mimetype='application/json')
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


def response_text(text: str) -> Response:
    response = Response(text, mimetype='text/plain')
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


def response_cookie(cookie_name: str, cookie_value: str, object: dict):
    json = object_to_json(object)
    response = Response(json, mimetype='application/json')
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.set_cookie(key=cookie_name, value=cookie_value, expires=get_expire_date(90))
    return response

def get_expire_date(days: int) -> datetime:
    return datetime.datetime.now() + datetime.timedelta(days=days)


def object_to_json(some_object: Dict) -> bytes:
    return json.dumps(some_object, ensure_ascii=False, indent=2, sort_keys=True).encode(encoding='utf-8')


def response_error(error_code, text) -> Tuple[Response, int]:
    response = Response(text, mimetype='text/plain')
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:4210"
    return response, error_code


def response_html(html):
    response = Response(html, mimetype='text/html')
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:4210"
    return response


def response_csv(csv):
    response = Response(csv, mimetype='text/csv', content_type='"text/csv; charset=utf-16"')
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:4210"
    return response


def response_jsonp(json_text: str):
    callback_function_name = request.args.get('callback', 'jsonp_callback')
    jsonp = f"{callback_function_name}({json_text});"

    response = Response(jsonp.encode(encoding='utf-8'), mimetype='application/javascript')
    response.headers["Content-Type"] = "application/javascript; charset=utf-8"

    return response


def response_jsonp_error(error_code: int, exception):
    callback_function_name = request.args.get('callback', 'callback')
    error_json = {"error": str(exception), "error_code": error_code}
    jsonp = f"{callback_function_name}({error_json});"

    response = Response(jsonp.encode(encoding='utf-8'), mimetype='application/javascript')
    response.headers["Content-Type"] = "application/javascript; charset=utf-8"

    return response
