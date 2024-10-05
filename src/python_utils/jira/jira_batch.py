from typing import List, Dict
import uuid

from python_utils.profiler import profiling
from python_utils.timestamp import get_first_and_last_day_of_current_month, iterate_months
from python_utils.jira.jira_client import JiraClient, JiraPageResult
from python_utils.flask.shared import shared_dict


class JiraBatchConfig:

    def __init__(self, jira_config: Dict):
        self.jira_config = jira_config

    def is_valid(self) -> bool:
        return "jql" in self.jira_config and \
            "batch_jql" in self.jira_config and \
            "start_date" in self.jira_config

    def get_jql(self):
        return self.jira_config["jql"]

    def get_batch_jql(self):
        return self.jira_config["batch_jql"]

    def get_start_date(self) -> str:
        return self.jira_config["start_date"]

    def create_batch_config(self, reload_all=False, reload_current=True) -> List[Dict]:
        batch_configs = [{"jql": "project = Test AND ...", "use_cache": True, "description": "Some Description"}] and []

        # historical queries:
        for start_of_month, end_of_month, month_name in iterate_months(self.get_start_date()):
            jql = self.get_batch_jql()
            jql = jql.replace("{start_of_month}", start_of_month)
            jql = jql.replace("{end_of_month}", end_of_month)
            batch_configs.append({"jql": jql, "use_cache": not reload_all, "description": f"Fetching data for {month_name}"})

        # current month:
        jql = self.get_jql()
        start_of_month, end_of_month, month_name = get_first_and_last_day_of_current_month()
        jql = jql.replace("{start_of_month}", start_of_month.strftime("%Y-%m-%d"))
        jql = jql.replace("{end_of_month}", end_of_month.strftime("%Y-%m-%d"))
        batch_configs.append({"jql": jql, "use_cache": not reload_current, "description": f"Fetching data for {month_name}"})

        return batch_configs

    def __repr__(self) -> str:
        return str(self.__dict__())

    def __dict__(self) -> Dict:
        return self.jira_config


class JiraBatchProcessor:

    def __init__(self, jira_client: JiraClient):
        self.jira_client = jira_client

    def get_batch(self, batch_config: List[Dict], jira_access_token: str) -> (List[Dict[str, str]], str):
        overall_issues = []
        overall_timestamp = ""
        for batch_query in batch_config:
            print(batch_query["description"])
            (issues, timestamp) = self.jira_client.paginate(jql=batch_query["jql"], access_token=jira_access_token, use_cache=batch_query["use_cache"])
            overall_issues.extend(issues)
            overall_timestamp = timestamp

        return overall_issues, overall_timestamp


