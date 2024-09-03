import re
from typing import List
SPRINT_PATTERN = r"com\.atlassian\.greenhopper\.service\.sprint\.Sprint@[A-Za-z0-9]*\[id=(\d+),.*,state=([^,]+),.*name=([^,]+),startDate=([^,]+),endDate=([^,]+),completeDate=([^,]+),activatedDate=([^,]+),.*"


class Sprint:

    def __init__(self, jira_sprint_field_value: str):
        self.jira_sprint_field_value = jira_sprint_field_value

        match = re.search(SPRINT_PATTERN, self.jira_sprint_field_value, re.MULTILINE)
        if not match:
            raise Exception(f"Invalid sprint format: {jira_sprint_field_value}")
        # Extrahieren der Informationen
        self.sprint_id = match.group(1)
        self.state = match.group(2)
        self.sprint_name = match.group(3)
        self.start_date = match.group(4)
        self.end_date = match.group(5)
        self.complete_date = match.group(6)
        self.activated_date = match.group(7)

    def is_valid(self) -> bool:
        return self.start_date and self.start_date != "<null>" and self.end_date and self.end_date != "<null>"

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return str(self.__dict__())

    def __dict__(self):
        return {"id": self.sprint_id, "name": self.sprint_name, "state": self.state, "start_date": self.start_date,
                "end_date": self.end_date, "activated_date": self.activated_date,
                "complete_date": self.complete_date}


def extract_sprint_name(sprint_object: str) -> List | str | None:

    if not sprint_object:
        return None

    if isinstance(sprint_object, list):
        return [ extract_sprint_name(item) for item in sprint_object ]

    return Sprint(str(sprint_object)).sprint_name
