import logging
import requests
from pathlib import Path
from typing import List, Dict

from python_utils.timestamp import now

from jira import JIRA
from tinydb import TinyDB, Query, where
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage

from filelock import FileLock
from python_utils.profiler import profiling

logger = logging.getLogger(__name__)


class JiraPageResult:

    def __init__(self, start_at: int, total: int, timestamp: str, issues: List[Dict]):
        self.start_at = start_at
        self.total = total
        self.timestamp = timestamp
        self.issues = issues

    def get_start_at(self) -> int:
        return self.start_at

    def get_total(self) -> int:
        return self.total

    def get_issues(self) -> List[Dict]:
        return self.issues

    def get_next_start_at(self) -> int:
        return self.start_at + len(self.issues)

    def has_next(self) -> bool:
        return self.get_next_start_at() < self.total

    def get_timestamp(self) -> str:
        return self.timestamp

    def __dict__(self) -> Dict:
        return {"nextStartAt": self.get_next_start_at(), "hasNext": self.has_next(), "total": self.total, "timestamp": self.timestamp,
                "issues(count)": len(self.issues)}


class QueryCache:

    def __init__(self, filename: str):
        self.filename = filename
        Path(self.filename).touch()
        self.lock = FileLock(f"{self.filename}.lock")
        self.db = TinyDB(self.filename, storage=CachingMiddleware(JSONStorage))

    def get_all_pages(self, jql: str, start_at: int = 0) -> JiraPageResult:
        cached_queries = Query()
        result = self.db.search((cached_queries.jql == jql) & (cached_queries.startAt >= start_at))
        if not result:
            return None
        issues = []
        total = 0
        timestamp = ""
        for page in result:
            issues.extend(page["issues"])
            total = max(total, page["total"])
            timestamp = max(timestamp, page["timestamp"])

        return JiraPageResult(start_at=start_at, total=total, timestamp=timestamp, issues=issues)

    def remove_all_pages(self, jql: str):
        cached_queries = Query()
        with self.lock:
            for document_id in self.db.remove(where("jql") == jql):
                print(f"Removed: {document_id}")
            self.db.storage.flush()

    def get_page(self, jql: str, start_at: int) -> JiraPageResult:
        cached_queries = Query()
        result = self.db.search((cached_queries.jql == jql) & (cached_queries.startAt == start_at))
        if not result:
            return None
        if len(result) != 1:
            raise Exception(f"Found two matches for jql: {jql}")

        page = result[0]
        return JiraPageResult(start_at=start_at, total=page["total"], timestamp=page["timestamp"], issues=page["issues"])

    def add_page(self, jql, page: JiraPageResult):
        cached_queries = Query()
        with self.lock:
            self.db.upsert(
                {"jql": jql, "startAt": page.get_start_at(), "total": page.get_total(), "timestamp": page.get_timestamp(), "issues": page.get_issues()},
                (cached_queries.jql == jql) & (cached_queries.startAt == page.get_start_at()))
            self.db.storage.flush()

    def clear(self):
        with self.lock:
            self.db.truncate()

    def close(self):
        if self.db:
            self.db.close()


class ProjectCache:

    def __init__(self, filename: str):
        self.filename = filename
        Path(self.filename).touch()
        self.lock = FileLock(f"{self.filename}.lock")
        self.db = TinyDB(self.filename, storage=CachingMiddleware(JSONStorage))

    @staticmethod
    def create_sprint_record_id(project_id: str, name_filter: str, activated_date: str) -> str:
        return f"{project_id}_{name_filter}_{activated_date}"

    def get_versions(self, project_id: str) -> List[Dict[str, str]]:
        cached_queries = Query()
        result = self.db.search((cached_queries.type == "version") & (cached_queries.id == project_id) & (
                        cached_queries.timestamp == self.current_timestamp()))
        if not result:
            return None

        return result[0]["versions"]

    def add_versions(self, project_id: str, versions: List[Dict[str, str]]):
        cached_queries = Query()
        with self.lock:
            self.db.upsert({"type": "versions", "id": project_id, "timestamp": self.current_timestamp(), "versions": versions}, (cached_queries.type == "versions") & (cached_queries.id == project_id))
            self.db.storage.flush()

    def get_sprints(self, project_id: str, name_filter: str, activated_date: str) -> List[Dict[str, str]]:
        cached_queries = Query()
        result = self.db.search(
            (cached_queries.type == "sprints") & (cached_queries.id == self.create_sprint_record_id(project_id, name_filter, activated_date)) & (cached_queries.timestamp == self.current_timestamp()))
        if not result:
            return None

        return result[0]["sprints"]

    def add_sprints(self, project_id: str, name_filter: str, activated_date: str, sprints: List[Dict[str, str]]):
        cached_queries = Query()
        with self.lock:
            record_id = self.create_sprint_record_id(project_id, name_filter, activated_date)
            self.db.upsert({"type": "sprints", "id": record_id, "timestamp": self.current_timestamp(), "sprints": sprints}, (cached_queries.type == "sprints") & (cached_queries.id == record_id))
            self.db.storage.flush()

    @staticmethod
    def current_timestamp() -> str:
        from time import strftime
        return strftime("%Y-%m-%d")

    def clear(self):
        with self.lock:
            self.db.truncate()

    def close(self):
        if self.db:
            self.db.close()


class RoadmapCache:

    def __init__(self, filename: str):
        self.filename = filename
        Path(self.filename).touch()
        self.lock = FileLock(f"{self.filename}.lock")
        self.db = TinyDB(self.filename, storage=CachingMiddleware(JSONStorage))

    @staticmethod
    def create_roadmap_id(project_id: str, plan_id: int, scenario_id: int) -> str:
        return f"{project_id}_{plan_id}_{scenario_id}"

    def get_roadmap(self, project_id: str, plan_id: int, scenario_id: int) -> Dict[str, str]:
        cached_queries = Query()
        result = self.db.search((cached_queries.id == self.create_roadmap_id(project_id, plan_id, scenario_id)) & (
                        cached_queries.timestamp == self.current_timestamp()))
        if not result:
            return None

        return { "issues": result[0]["roadmap"], "timestamp": result[0]["timestamp"] }

    def add_roadmap(self, project_id: str, plan_id: int, scenario_id: int, roadmap: List[Dict[str, str]]):
        cached_queries = Query()
        roadmap_id = self.create_roadmap_id(project_id, plan_id, scenario_id)
        with self.lock:
            self.db.upsert({"id": roadmap_id, "timestamp": self.current_timestamp(), "roadmap": roadmap}, (cached_queries.id == roadmap_id))
            self.db.storage.flush()

    @staticmethod
    def current_timestamp() -> str:
        from time import strftime
        return strftime("%Y-%m-%d")

    def clear(self):
        with self.lock:
            self.db.truncate()

    def close(self):
        if self.db:
            self.db.close()

class JiraClient:

    def __init__(self, hostname: str, cache_directory: str,  test_mode=False, max_result_size=700):
        self.hostname = hostname
        self.query_cache = QueryCache(filename=f"{cache_directory}/query_cache.json")
        self.project_cache = ProjectCache(filename=f"{cache_directory}/project_cache.json")
        self.roadmap_cache = RoadmapCache(filename=f"{cache_directory}/roadmap_cache.json")
        self.test_mode = test_mode
        self.max_result_size = max_result_size

    def set_test_mode(self, test_mode: bool):
        self.test_mode = test_mode

    def paginate(self, jql: str, access_token: str, use_cache: bool, page_size=200, expand="changelog", cache_suffix="") -> (List[Dict], str):
        page_result = self.get_issues(jql=jql, access_token=access_token, use_cache=use_cache, start_at=0,
                                                  page_size=page_size, cache_suffix=cache_suffix)
        issues = []
        issues.extend(page_result.get_issues())

        while page_result.has_next():
            page_result = self.get_issues(jql=jql, access_token=access_token, use_cache=use_cache,
                                                      start_at=page_result.get_next_start_at(), expand=expand, page_size=page_size, cache_suffix=cache_suffix)
            issues.extend(page_result.get_issues())

        return issues, page_result.get_timestamp()

    def get_issues(self, jql: str, access_token: str, use_cache: bool, expand="changelog", page_size=200, start_at=0, cache_suffix="") -> JiraPageResult:

        cache_id = f"{jql}_{cache_suffix}"

        logger.debug(
            f"get_issues(jql={jql}, use_cache={use_cache}, expand={expand}, page_size={page_size}, start_at={start_at}")

        if use_cache:
            jira_page = self.query_cache.get_all_pages(cache_id, start_at)
            if jira_page:
                logger.info(
                    f"Return cached issues for {cache_id}: Total={jira_page.get_total()} / issues: {len(jira_page.get_issues())}")
                return jira_page

        if self.test_mode:
            logger.info(f"TEST_MODE active. Return empty result for jql {jql}")
            return JiraPageResult(start_at=0, total=0, timestamp=now(), issues=[])

        jira_page = self.search(jql, access_token, expand, page_size, start_at)

        logger.info(f"Add {cache_id} to cache: {len(jira_page.get_issues())} items")
        self.query_cache.add_page(cache_id, jira_page)

        return jira_page

    def get_unreleased_versions(self, project_id: str, access_token: str) -> List[Dict[str, str]]:
        versions = self.get_versions(project_id, access_token)
        unreleased_versions = []
        for version in versions:
            if not version["released"]:
                unreleased_versions.append(version)

        return unreleased_versions


    def get_versions(self, project_id: str, access_token: str) -> List[Dict[str, str]]:

        versions = self.project_cache.get_versions(project_id)
        if versions:
            logger.info(
                f"Return cached versions for {project_id}: {versions}")
            return versions

        jira = self.create_jira(access_token=access_token)
        versions = [ version.raw for version in jira.project_versions(project=project_id) ]


        logger.info(f"Add versions to cache: {len(versions)} items")
        self.project_cache.add_versions(project_id, versions)

        return versions


    def get_roadmap(self, project_id: str, plan_id: int, scenario_id: int, fix_version_filters: List[str], access_token: str, use_cache=True) -> (List[Dict[str, str]], str):

        roadmap = None
        if use_cache:
            roadmap = self.roadmap_cache.get_roadmap(project_id, plan_id, scenario_id)

        if not roadmap:
            roadmap = self.get_roadmap_from_jira_backend(plan_id, scenario_id, access_token)
            self.roadmap_cache.add_roadmap(project_id, plan_id, scenario_id, roadmap["issues"])

        unreleased_versions = self.get_unreleased_versions(project_id, access_token)
        version_ids = get_matching_version_ids(unreleased_versions, fix_version_filters)
        roadmap_issues = roadmap["issues"]
        roadmap_issues = filter(
            lambda issue: has_fix_versions(issue, version_ids),
            roadmap_issues)

        roadmap_issues = sorted(roadmap_issues, key=lambda issue: issue["values"]["lexoRank"])
        issues = []
        for index, roadmap_issue in enumerate(roadmap_issues):
            issues.append(convert_roadmap_issue_to_issue(project_id, roadmap_issue))

        return { "issues": issues, "timestamp": roadmap["timestamp"] }

    def change_roadmap_issue_rank(self, plan_id: int, scenario_id: int, anchor_issue_id: int, issue_id: int, access_token: str, operation="AFTER"):
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        data = { "operations":[{"anchor":f"{anchor_issue_id}","itemKeys":[f"{issue_id}"],"operationType":f"{operation}"}],"planId":int(plan_id),"scenarioId":int(scenario_id)}

        response = requests.post(f"{self.hostname}/rest/jpo/1.0/issues/rank", headers=headers, json=data,
                                 allow_redirects=False)
        response.raise_for_status()
        return { "status": response.json() }

    def get_roadmap_from_jira_backend(self, plan_id: int, scenario_id: int, access_token: str) -> Dict[str, str]:

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        data = {"planId": int(plan_id), "scenarioId": int(scenario_id),
                "filter": {"includeCompleted": True, "performDependencyCompletion": False, "includeIssueLinks": True}}

        response = requests.post(f"{self.hostname}/rest/jpo/1.0/backlog", headers=headers, json=data,
                                 allow_redirects=False)
        response.raise_for_status()

        roadmap = response.json()
        return { "issues": roadmap["issues"], "timestamp": now() }


    def search(self, jql: str, access_token: str, expand: str, page_size: int, start_at: int) -> JiraPageResult:
        jira = self.create_jira(access_token=access_token)
        result_set = jira.search_issues(jql, expand=expand, maxResults=page_size, startAt=start_at)
        issues = [issue.raw for issue in result_set]
        return JiraPageResult(start_at=result_set.startAt, total=result_set.total, timestamp=now(), issues=issues)

    def get_sprints_for_project(self, project_id: str, name_filter: str, activated_date: str, access_token: str, force_reload=False) -> List[Dict[str, str]]:

        if not force_reload:
            sprints = self.project_cache.get_sprints(project_id, name_filter, activated_date)
            if sprints:
                return sprints

        sprint_ids = []
        sprints = []
        jira = self.create_jira(access_token=access_token)
        boards = self.get_boards_for_project(jira, project_id, name_filter)
        for board in boards:
            for sprint in [sprint.raw for sprint in jira.sprints(board_id=int(board["id"]))]:
                if "activatedDate" in sprint and sprint["activatedDate"] >= activated_date and sprint["id"] not in sprint_ids:
                    sprint_ids.append(sprint["id"])
                    sprints.append(sprint)

        self.project_cache.add_sprints(project_id, name_filter, activated_date, sprints)

        return sprints

    def get_boards_for_project(self, jira: JIRA, project_id: str, name_filter: str) -> List[Dict[str, str]]:
        boards = []
        for board in jira.boards(projectKeyOrID=project_id, type="scrum", maxResults=50):
            if name_filter in board.name:
                boards.append(board.raw)

        return sorted(boards, key=lambda board: board["id"], reverse=False)

    def close(self):
        if self.query_cache:
            self.query_cache.close()
        if self.project_cache:
            self.project_cache.close()


    def create_jira(self, access_token: str) -> JIRA:
        if ":::" in access_token:
            username_password = access_token.split(":::")
            return JIRA(self.hostname, basic_auth=(username_password[0], username_password[1]))
        else:
            return JIRA(self.hostname, token_auth=access_token)

def get_matching_version_ids(versions: List[Dict[str, str]], version_filters: List[str]) -> List[str]:
    version_ids : List[int] = []
    for version in versions:
        for version_filter in version_filters:
            if version["name"].startswith(version_filter):
                version_ids.append(str(version["id"]))

    return version_ids

def has_fix_versions(issue: Dict, fix_versions_filters: List[str]) -> bool:
    if not "fixVersions" in issue["values"]:
        return False

    for fix_version_filter in fix_versions_filters:
        if fix_version_filter in issue["values"]["fixVersions"]:
            return True

    return False

def convert_roadmap_issue_to_issue(project_id: str, roadmap_issue: Dict) -> Dict:
    return { "key": f"{project_id}-{roadmap_issue['issueKey']}",
             "id": roadmap_issue["id"],
             "summary": roadmap_issue["values"]["summary"],
             "labels": roadmap_issue["values"]["labels"] if "labels" in roadmap_issue["values"] else [],
             "issuetype": roadmap_issue["values"]["type"],
             "status": roadmap_issue["values"]["status"]
             }