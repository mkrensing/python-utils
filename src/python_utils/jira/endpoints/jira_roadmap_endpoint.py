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


jira_roadmap_endpoint = Blueprint('jira_endpoint', __name__, url_prefix='/rest/jira')

@inject_environment(
    {"JIRA_HOSTNAME": "",
     "CACHE_DIRECTORY": "",
     "TEST_MODE": "False"},
    required=True)
def create_jira_client(hostname: str, cache_directory: str, test_mode: str) -> JiraClient:
    return JiraClient(hostname=hostname, cache_directory=cache_directory,
                      test_mode=test_mode.lower() in ["true", "1"])


jira_client = create_jira_client()

@jira_roadmap_endpoint.route('/roadmap/<int: plan_id>/<int: scenario_id>', methods=["GET"])
@token_required()
def get_roadmap(project_id: str, plan_id: int, scenario_id: int):

    force_reload = (request.args["force_reload"] == "true") if "force_reload" in request.args else False
    versions_filters = request.args.getlist("fixVersions")

    print(f"get_roadmap: {versions_filters}")

    return response_json(
        jira_client.get_roadmap(project_id, plan_id=plan_id, scenario_id=scenario_id, fix_version_filters=versions_filters, access_token=get_access_token()))


