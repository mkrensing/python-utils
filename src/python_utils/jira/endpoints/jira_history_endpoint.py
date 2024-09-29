import traceback

from flask import Blueprint, request
from typing import Dict, List
from python_utils.jira.jira_client import JiraClient
from python_utils.jira.jira_history import JiraHistory
from python_utils.flask.endpoint import response_json, destroy_endpoint
from python_utils.env import inject_environment
from python_utils.file import lookup_file
from python_utils.jira.jira_security import token_required, get_access_token

jira_history_endpoint = Blueprint('jira_history_endpoint', __name__, url_prefix='/rest/jira/history')

class JiraHistoryConfig:

    def __init__(self, jira_config: Dict):
        self.jira_config = jira_config

    def is_valid(self) -> bool:
        return "jql" in self.jira_config and \
            "useCache" in self.jira_config and \
            "pageSize" in self.jira_config and \
            "fields" in self.jira_config

    def get_jql(self):
        return self.jira_config["jql"]

    def is_use_cache(self) -> bool:
        return bool(self.jira_config["useCache"])

    def get_page_size(self) -> int:
        return self.jira_config["pageSize"]

    def get_fields(self) -> Dict[str, str]:
        return self.jira_config["fields"]


@inject_environment(
    {"JIRA_HOSTNAME": "",
     "QUERY_CACHE_FILENAME": lambda: lookup_file("storage/query_cache.json"),
     "SPRINT_CACHE_FILENAME": lambda: lookup_file("storage/sprint_cache.json"),
     "TEST_MODE": "False"})
def create_jira_client(hostname: str, query_cache_filename: str, sprint_cache_filename, test_mode: str) -> JiraClient:
    return JiraClient(hostname=hostname, query_cache_filename=query_cache_filename, sprint_cache_filename=sprint_cache_filename,
                      test_mode=test_mode.lower() in ["true", "1"])


jira_client = create_jira_client()

@jira_history_endpoint.route('/search/<int:start_at>', methods=["POST"])
@token_required()
def post_search_history(start_at: int):
    try:
        config = JiraHistoryConfig(request.json)
        if not config.is_valid():
            return response_json({"error": f"Invalid request body. Expected JiraHistoryConfig"}), 400

        jira_page = jira_client.get_issues(jql=config.get_jql(), access_token=get_access_token(), use_cache=config.is_use_cache(), start_at=start_at, page_size=config.get_page_size())
        issues = jira_page.get_issues()
        history_issues = convert_to_history_issues(issues, config.get_fields())

        return response_json({ "nextStartAt": jira_page.get_next_start_at(), "hasNext": jira_page.has_next(), "total": jira_page.get_total(), "timestamp": jira_page.get_timestamp(), "issues": history_issues })

    except Exception as e:
        print(e)
        print(traceback.format_exc())
        return response_json({"error": str(e)}), 400


def convert_to_history_issues(issues: List[Dict], issues_fields: Dict[str, str]) -> List[Dict]:
    return JiraHistory(issues_fields=issues_fields).get_histories(issues)
