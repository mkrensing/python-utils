import os
from flask import Blueprint, request
from python_utils.jira.jira_client import JiraClient
from python_utils.flask.endpoint import response_json, destroy_endpoint, init_endpoint, response_cookie
from python_utils.env import inject_environment
from python_utils.file import lookup_file, file_exists
from python_utils.jira.jira_security import token_required, get_access_token
from python_utils.jira.jira_security import read_tokens, write_tokens, register_token, logout, is_logged_in

jira_endpoint = Blueprint('jira_endpoint', __name__, url_prefix='/rest/jira')


@inject_environment(
    {"JIRA_HOSTNAME": "",
     "QUERY_CACHE_FILENAME": lookup_file("storage/query_cache.json"),
     "SPRINT_CACHE_FILENAME": lookup_file("storage/sprint_cache.json"),
     "TEST_MODE": "False"})
def create_jira_client(hostname: str, query_cache_filename: str, sprint_cache_filename, test_mode: str) -> JiraClient:
    return JiraClient(hostname=hostname, query_cache_filename=query_cache_filename,
                      sprint_cache_filename=sprint_cache_filename, jira_backend_lock_filename="jira.lock",
                      test_mode=test_mode.lower() in ["true", "1"])


jira_client = create_jira_client()


@destroy_endpoint
def shutdown_endpoint():
    jira_client.close()


@jira_endpoint.route('/sprints/<project_id>/<name_filter>/<activated_date>', methods=["GET"])
@token_required()
def get_sprints_for_project(project_id: str, name_filter: str, activated_date: str):
    return response_json(
        jira_client.get_sprints_for_project(project_id, name_filter, activated_date, access_token=get_access_token()))


@init_endpoint
@inject_environment({"TOKEN_FILENAME": lookup_file("storage/token.json")})
def init_security(filename: str):
    print(f"init_security: {filename}")
    if file_exists(filename):
        read_tokens(filename)
        os.remove(filename)


@destroy_endpoint
@inject_environment({"TOKEN_FILENAME": lookup_file("storage/token.json")})
def shutdown_endpoint(filename: str):
    print(f"shutdown_endpoint: {filename}")
    if filename:
        write_tokens(filename)


@jira_endpoint.route("/login")
def get_login():
    token = request.args.get("token")
    auth_id = register_token(token)

    return response_cookie("auth_id", auth_id, {"message": "Token registered", "auth_id": auth_id })


@jira_endpoint.route("/logout")
def get_logout():
    if not is_logged_in():
        return response_json({"result": "SKIPPED"})

    logout()
    return response_json({"result": "OK"})