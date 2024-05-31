from flask import request, current_app, Response, abort
import json

def config_parameter(contextRoot, parameterName):
    if parameterName in current_app.config.get(contextRoot):
        return current_app.config.get(contextRoot)[parameterName]

    return ""

def request_parameter(contextRoot, parameterName, defaultValue=None, required=False):
    if not defaultValue:
        defaultValue = config_parameter(contextRoot, parameterName)
        parameterValue = request.args.get(parameterName, defaultValue)

    if not parameterValue and required:
        print("abording...")
        abort(400, f"Missing required request parameter '{parameterName}'.")

    return parameterValue

def json_to_dict(json_text: str) -> dict:
    try:
        return json.loads(json_text)
    except Exception as e:
        raise Exception(f"json_to_dict with input: {json_text}", e)

def object_to_json(object):
    return json.dumps(object, ensure_ascii=False, indent=2, sort_keys=True)

def response_jsonp(json):
    callbackFunctionName = request.args.get('callback', 'jsonp_callback')
    jsonp = f"{callbackFunctionName}({json});"

    response = Response(jsonp.encode(encoding='utf-8'), mimetype='application/javascript')
    response.headers["Content-Type"] = "application/javascript; charset=utf-8"

    return response

def response_json(json):
    response = Response(json.encode(encoding='utf-8'), mimetype='application/json')
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

def response_csv(csv):
    response = Response(csv.encode(encoding='utf-8'), mimetype='text/csv', content_type='"text/csv; charset=utf-16"')
    return response

def response_jsonp_error(error_code: int, exception):
    callbackFunctionName = request.args.get('callback', 'callback')
    error_json =  { "error" : str(exception), "error_code": error_code }
    jsonp = f"{callbackFunctionName}({error_json});"

    response = Response(jsonp.encode(encoding='utf-8'), mimetype='application/javascript')
    response.headers["Content-Type"] = "application/javascript; charset=utf-8"

    return response

def response_error(error_code: int, text: str):
    response = Response(text, mimetype='text/plain')
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response, error_code
