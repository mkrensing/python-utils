from typing import List, Dict, Tuple
from python_utils.dynamic_execution import DynamicExecution
from python_utils.timestamp import now
import re
from datetime import datetime, UTC, timedelta, timezone

JIRA_SNAPSHOT_FIELD_CONFIGURATION_PATTERN = re.compile(r"([A-Za-z0-9_.]*)\(([A-Za-z0-9_.\s]*),?\s*(([\"\'A-Za-z0-9_.\s,]*))\)")


class JiraHistoryField:

    def __init__(self, backup_history_field_name: str, field_access_config: str):
        self.field_convert_method_name, self.history_field_name, self.field_convert_method_second_argument = JiraField.parse_field_access_config(
            field_access_config)
        self.field_convert_method = DynamicExecution.by_full_name(self.field_convert_method_name, __name__) if self.field_convert_method_name else None
        if not self.history_field_name:
            self.history_field_name = backup_history_field_name

    def is_present(self, issue_change_history: Dict) -> bool:
        return self.history_field_name in issue_change_history

    def get_history_field_name(self):
        return self.history_field_name

    def extract_value(self, issue_change_history: Dict):
        history_entries = issue_change_history[self.history_field_name]

        if not self.field_convert_method:
            return history_entries

        for timestamp in history_entries:
            value = history_entries[timestamp]
            history_entries[timestamp] = self.field_convert_method.execute(self.get_convert_method_arguments(value))

        return history_entries

    def get_convert_method_arguments(self, value):
        if self.field_convert_method_second_argument:
            return value, self.field_convert_method_second_argument
        else:
            return [value]


class JiraField:

    def __init__(self, field_name: str, field_access_config: str):
        self.field_name = field_name
        self.field_convert_method_name, self.field_property_path, self.field_convert_method_second_argument = self.parse_field_access_config(
            field_access_config)
        self.field_convert_method = DynamicExecution.by_full_name(self.field_convert_method_name, __name__) if self.field_convert_method_name else None

    def get_name(self):
        return self.field_name

    def get_current_value(self, issue: Dict):
        if not self.has_property_path(issue, self.field_property_path):
            return None

        value = self.extract_property_value(issue, self.field_property_path)
        parameters = [value]
        if self.field_convert_method_second_argument:
            parameters = (value, self.field_convert_method_second_argument)
        return self.field_convert_method.execute(parameters) if self.field_convert_method else value

    @staticmethod
    def has_property_path(issue: Dict, property_path: str) -> bool:
        value = issue
        for path_element in property_path.split("."):
            try:
                if isinstance(value, list):
                    if len(value) == 0:
                        # It's a list but without a value. If there would be an list element, the path_element could exist.
                        return True

                    value = value[0]

                if path_element not in value:
                    return False
                value = value[path_element]
                if value is None:
                    return False
            except Exception as e:
                raise Exception(f"Error in has_property_path with path {property_path} and element {path_element} for issue: {issue['key']}", e)

        return True

    @staticmethod
    def extract_property_value(issue: Dict, property_path: str):
        value = issue
        for path_element in property_path.split("."):
            if isinstance(value, list):
                list_values = []
                for item in value:
                    if path_element not in item:
                        raise Exception(f"field {path_element} of path {property_path} not found in issue: {issue}")
                    list_values.append(item[path_element])
                return list_values
            elif path_element not in value:
                raise Exception(f"field {path_element} of path {property_path} not found in issue: {issue}")
            value = value[path_element]
            if value is None:
                return None

        return value

    @staticmethod
    def parse_field_access_config(field_access_config: str) -> (str, str, str):

        match = JIRA_SNAPSHOT_FIELD_CONFIGURATION_PATTERN.match(field_access_config)
        convert_method_name = None
        second_method_argument = None

        if match:
            convert_method_name = match.group(1)
            property_path = match.group(2)
            if len(match.groups()) > 2:
                second_method_argument = match.group(3).replace('"', '').replace("'", '')

        else:
            property_path = field_access_config

        return convert_method_name, property_path, second_method_argument

    def __repr__(self) -> str:
        return str(self.__dict__())

    def __dict__(self) -> Dict:
        return {"field_name": self.field_name,
                "field_convert_method_name": self.field_convert_method_name,
                "field_convert_method_second_argument": self.field_convert_method_second_argument,
                "field_property_path": self.field_property_path}


class JiraHistoryConfig:

    def __init__(self, fields_config: Dict[str, str]):
        self.field_names, self.fields, self.history_fields = self.create_fields(fields_config)

    def get_field_names(self) -> List[str]:
        return self.field_names

    def get_field(self, field_name: str) -> JiraField:
        return self.fields[field_name]

    def get_history_field(self, field_name: str) -> JiraHistoryField:
        return self.history_fields[field_name]

    @staticmethod
    def create_fields(fields_config: Dict[str, str]) -> Tuple[List[str], Dict[str, JiraField], Dict[str, JiraHistoryField]]:
        field_names = []
        fields = {}
        history_fields = {}

        for field_name in fields_config:
            field_access_config, history_field_access_config = JiraHistoryConfig.extract_access_config(field_name, fields_config[field_name])
            field_names.append(field_name)
            fields[field_name] = JiraField(field_name, field_access_config)
            history_fields[field_name] = JiraHistoryField(field_name, history_field_access_config)

        return field_names, fields, history_fields

    @staticmethod
    def extract_access_config(field_name: str, field_config: str) -> (str, str):

        issue_and_history_access_config = field_config.split("/")
        field_access_config = issue_and_history_access_config[0]
        history_field_name = field_name

        if len(issue_and_history_access_config) > 1:
            history_field_name = issue_and_history_access_config[1]

        return field_access_config, history_field_name


class JiraHistory:

    def __init__(self, issues_fields: Dict[str, str]):
        self.config = JiraHistoryConfig(issues_fields)

    @staticmethod
    def get_created_timestamp(issue: Dict) -> str:
        return issue["fields"]["created"]

    @staticmethod
    def convert_dict_to_ordered_list(dict: Dict) -> List[Dict]:
        return [{key: dict[key]} for key in sorted(dict.keys())]

    def get_histories(self, issues: List[Dict]):

        history_issues = []

        for issue in issues:
            history_issue = {"key": issue["key"], "created": issue["fields"]["created"], "resolutiondate": issue["fields"]["resolutiondate"]}
            issue_change_history = self.get_change_history(issue)

            for field_name in self.config.get_field_names():
                if field_name not in history_issue:
                    history_issue[field_name] = self.convert_dict_to_ordered_list(self.extract_history_values(field_name, issue, issue_change_history))

            history_issues.append(history_issue)

        return history_issues

    def extract_history_values(self, field_name: str, issue: Dict, issue_change_history: Dict) -> Dict[str, str]:

        history_field = self.config.get_history_field(field_name)

        if history_field.is_present(issue_change_history):
            return history_field.extract_value(issue_change_history)
        else:
            # Field never changed. current value was present at creation date
            field = self.config.get_field(field_name)
            return {JiraHistory.get_created_timestamp(issue): field.get_current_value(issue)}

    @staticmethod
    def get_change_history(issue: Dict) -> Dict:
        changed = {"status": {"2024-01-01T00:00:00": "NEW"}, "issuetype": {}} and {}
        created_timestamp = JiraHistory.get_created_timestamp(issue)

        if "changelog" in issue and "histories" in issue["changelog"]:
            history_entries = sorted(issue["changelog"]["histories"], key=lambda entry: entry["created"], reverse=True)
            for history_entry in history_entries:
                history_created = history_entry["created"]
                for item in history_entry["items"]:
                    field_name = item["field"]
                    changed[field_name] = changed[field_name] if field_name in changed else {}
                    changed[field_name][history_created] = item["toString"]
                    changed[field_name][created_timestamp] = item["fromString"]

        return changed


def join(items: List, delimiter=" ") -> str:
    return delimiter.join(items)


def split(text: str, seperator=" ") -> None | List[str]:
    if not text:
        return None

    return text.split(sep=seperator)

def create_snapshots(history_issues, timestamps, timestamp_converter=None):
    timestamp_converter = timestamp_converter or (lambda timestamp: timestamp)

    return create_index_of_list_with_unique_keys([
        {timestamp: [
            create_snapshot(issue, timestamp_converter(timestamp))
            for issue in history_issues
            if issue['created'] <= timestamp_converter(timestamp)
        ]}
        for timestamp in timestamps
    ])


def create_snapshot(history_issue, timestamp):
    snapshot = {}

    for property_name, property_value in history_issue.items():
        if not isinstance(property_value, list):
            snapshot[property_name] = property_value
        else:
            property_values_before_timestamp = [
                {"timestamp": list(history_entry.keys())[0], "value": list(history_entry.values())[0]}
                for history_entry in property_value
                if list(history_entry.keys())[0] <= timestamp
            ]
            if property_values_before_timestamp:
                snapshot[property_name] = property_values_before_timestamp[-1]["value"]

    snapshot["history"] = history_issue

    return snapshot


def create_index_of_list_with_unique_keys(array_of_objects):
    index = {}
    for obj in array_of_objects:
        index.update(obj)
    return index


def get_leadtime(history_issues, start_state_configuration, end_state_configuration):
    return [
        {
            'key': history_issue['key'],
            'start': find_timestamp(
                history_issue,
                create_state_configuration_object(start_state_configuration)['propertyName'],
                create_state_configuration_object(start_state_configuration)['value'],
                0
            ),
            'end': find_timestamp(
                history_issue,
                create_state_configuration_object(end_state_configuration)['propertyName'],
                create_state_configuration_object(end_state_configuration)['value'],
                -1
            ),
            'issue': history_issue
        }
        for history_issue in history_issues
    ]


def get_timestamp(history_issue, start_state_configuration):
    start_state = create_state_configuration_object(start_state_configuration)
    return find_timestamp(history_issue, start_state['propertyName'], start_state['value'], 0)


def find_timestamp(history_issue, property_name, property_value, array_index):
    if callable(property_value):
        return find_timestamp_by_function(history_issue, property_name, property_value, array_index)
    elif isinstance(property_value, list):
        return find_timestamp_by_values(history_issue, property_name, property_value, array_index)
    else:
        return find_timestamp_by_value(history_issue, property_name, property_value, array_index)


def find_timestamp_by_values(history_issue, property_name, property_values, array_index):
    timestamps = [
        find_timestamp_by_value(history_issue, property_name, property_value, array_index)
        for property_value in property_values
    ]
    timestamps = list(filter(None, timestamps))  # filter out None values

    return timestamps[0] if timestamps else None


def find_timestamp_by_value(history_issue, property_name, property_value, array_index):
    timestamps = [
        {
            "timestamp": list(history_entry.keys())[0],
            "value": list(history_entry.values())[0]
        }
        for history_entry in history_issue[property_name]
        if list(history_entry.values())[0] == property_value
    ]

    return timestamps[array_index]['timestamp'] if timestamps else None


def find_timestamp_by_function(history_issue, property_name, property_function, array_index):
    return property_function(history_issue[property_name])


def create_state_configuration_object(state_configuration):
    property_name = list(state_configuration.keys())[0]
    return {
        'propertyName': property_name,
        'value': state_configuration[property_name]
    }


def get_lead_time_in_days(start: str, end: str=None, including_weekend=True) -> int:
    if including_weekend:
        return get_lead_time_in_days_including_weekend(start, end)
    else:
        return get_lead_time_in_days_without_weekend(start, end)

def get_lead_time_in_days_including_weekend(start, end=None) -> int:
    if not start:
        return -1

    one_day = 24 * 60 * 60  # Sekunden in einem Tag
    end = end or now()

    start_date = datetime.fromisoformat(start)
    end_date = datetime.fromisoformat(end)

    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)

    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    diff_in_seconds = abs((end_date - start_date).total_seconds())

    return round(diff_in_seconds / one_day)


def get_lead_time_in_days_without_weekend(start, end=None) -> int:
    if not start:
        return -1

    one_day = timedelta(days=1)
    end = end or datetime.now(UTC).isoformat()

    start_date = datetime.fromisoformat(start)
    end_date = datetime.fromisoformat(end)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    total_days = 0
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5:
            total_days += 1
        current_date += one_day

    return total_days