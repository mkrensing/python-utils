import os
import traceback
from flask import Blueprint, request
from python_utils.jira.jira_client import JiraClient
from python_utils.flask.endpoint import response_json, destroy_endpoint, init_endpoint, response_cookie
from python_utils.env import inject_environment
from python_utils.file import lookup_file, file_exists
from python_utils.jira.jira_security import token_required, get_access_token
from python_utils.jira.jira_security import read_tokens, write_tokens, register_token, logout, is_logged_in
from typing import Dict


jira_endpoint = Blueprint('jira_endpoint', __name__, url_prefix='/rest/jira')

class JiraSearchConfig:

    def __init__(self, jira_config: Dict):
        self.jira_config = jira_config

    def is_valid(self) -> bool:
        return "jql" in self.jira_config and \
            "useCache" in self.jira_config and \
            "pageSize" in self.jira_config

    def get_jql(self):
        return self.jira_config["jql"]

    def is_use_cache(self) -> bool:
        return bool(self.jira_config["useCache"])

    def get_page_size(self) -> int:
        return self.jira_config["pageSize"]



@inject_environment(
    {"JIRA_HOSTNAME": "",
     "QUERY_CACHE_FILENAME": "",
     "SPRINT_CACHE_FILENAME": "",
     "TEST_MODE": "False"},
    required=True)
def create_jira_client(hostname: str, query_cache_filename: str, sprint_cache_filename, test_mode: str) -> JiraClient:
    return JiraClient(hostname=hostname, query_cache_filename=query_cache_filename,
                      sprint_cache_filename=sprint_cache_filename,
                      test_mode=test_mode.lower() in ["true", "1"])


jira_client = create_jira_client()

@jira_endpoint.route('/sprints/<project_id>/<name_filter>/<activated_date>', methods=["GET"])
@token_required()
def get_sprints_for_project(project_id: str, name_filter: str, activated_date: str):

    force_reload = (request.args["force_reload"] == "true") if "force_reload" in request.args else False

    return response_json(
        jira_client.get_sprints_for_project(project_id, name_filter, activated_date, access_token=get_access_token(), force_reload=force_reload))


@jira_endpoint.route('/search', methods=["POST"])
@token_required()
def post_search():
    try:
        config = JiraSearchConfig(request.json)
        if not config.is_valid():
            return response_json({"error": f"Invalid request body. Expected JiraSearchConfig"}), 400

        (issues, timestamp) = jira_client.paginate(jql=config.get_jql(), access_token=get_access_token(), use_cache=config.is_use_cache(), page_size=config.get_page_size())
        return response_json({ "timestamp": timestamp, "issues": issues })

    except Exception as e:
        print(e)
        print(traceback.format_exc())
        return response_json({"error": str(e)}), 400

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
