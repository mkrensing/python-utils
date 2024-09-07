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

    def create_batch_config(self) -> List[Dict]:
        batch_configs = [{"jql": "project = Test AND ...", "use_cache": True, "description": "Some Description"}] and []

        # historical queries:
        for start_of_month, end_of_month, month_name in iterate_months(self.get_start_date()):
            jql = self.get_batch_jql()
            jql = jql.replace("{start_of_month}", start_of_month)
            jql = jql.replace("{end_of_month}", end_of_month)
            batch_configs.append({"jql": jql, "use_cache": True, "description": f"Fetching data for {month_name}"})

        # current month:
        jql = self.get_jql()
        start_of_month, end_of_month, month_name = get_first_and_last_day_of_current_month()
        jql = jql.replace("{start_of_month}", start_of_month.strftime("%Y-%m-%d"))
        jql = jql.replace("{end_of_month}", end_of_month.strftime("%Y-%m-%d"))
        batch_configs.append({"jql": jql, "use_cache": False, "description": f"Fetching data for {month_name}"})

        return batch_configs

    def __repr__(self) -> str:
        return str(self.__dict__())

    def __dict__(self) -> Dict:
        return self.jira_config


class JiraBatchProcessor:

    def __init__(self, jira_client: JiraClient):
        self.active_batches = shared_dict()
        self.jira_client = jira_client

    def create_batch(self, config: JiraBatchConfig) -> str:
        batch_id = str(uuid.uuid4())
        self.active_batches[batch_id] = {
            "config": config.__dict__(),
            "batch": config.create_batch_config(),
        }

        return batch_id

    def get_batch_size(self, batch_id: str) -> int:

        if not self.is_valid(batch_id):
            return -1

        return len(self.active_batches[batch_id]["batch"])

    def get_batch_config(self, batch_id: str) -> Dict:
        if not self.is_valid(batch_id):
            return []

        return self.active_batches[batch_id]["batch"]

    def get_user_config(self, batch_id: str) -> Dict:
        if not self.is_valid(batch_id):
            return []

        return self.active_batches[batch_id]["config"]

    def is_valid(self, batch_id: str) -> bool:
        return batch_id and batch_id in self.active_batches

    def close_batch(self, batch_id: str):
        del self.active_batches[batch_id]

    @profiling()
    def get_batch(self, batch_id: str, index: int, start_at: int, access_token: str, initial_page_size=50, page_size=250) -> JiraPageResult:

        if batch_id not in self.active_batches:
            raise Exception(f"Batch not found with id: {batch_id}")

        active_batch = self.active_batches[batch_id]

        if not 0 <= index < len(active_batch["batch"]):
            raise Exception(f"Invalid batch index: {index}")

        batch = active_batch["batch"][index]

        return self.jira_client.get_issues(jql=batch["jql"],
                                            access_token=access_token,
                                            use_cache=batch["use_cache"],
                                            page_size=self.get_page_size(start_at, initial_page_size, page_size),
                                            start_at=start_at)

    def get_page_size(self, start_at: int, initial_page_size: int, page_size: int):
        return initial_page_size if start_at == 0 else page_size