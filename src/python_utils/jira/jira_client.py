import logging
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


class SprintCache:

    def __init__(self, filename: str):
        self.filename = filename
        Path(self.filename).touch()
        self.lock = FileLock(f"{self.filename}.lock")
        self.db = TinyDB(self.filename, storage=CachingMiddleware(JSONStorage))

    @staticmethod
    def create_record_id(project_id: str, name_filter: str, activated_date: str) -> str:
        return f"{project_id}_{name_filter}_{activated_date}"

    def get_sprints(self, project_id: str, name_filter: str, activated_date: str) -> List[Dict[str, str]]:
        cached_queries = Query()
        result = self.db.search(
            (cached_queries.id == self.create_record_id(project_id, name_filter, activated_date)) & (cached_queries.timestamp == self.current_timestamp()))
        if not result:
            return None

        return result[0]["sprints"]

    def add_sprints(self, project_id: str, name_filter: str, activated_date: str, sprints: List[Dict[str, str]]):
        cached_queries = Query()
        with self.lock:
            record_id = self.create_record_id(project_id, name_filter, activated_date)
            self.db.upsert({"id": record_id, "timestamp": self.current_timestamp(), "sprints": sprints}, (cached_queries.id == record_id))
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

    def __init__(self, hostname: str, query_cache_filename: str, sprint_cache_filename: str, test_mode=False, max_result_size=700):
        self.hostname = hostname
        self.query_cache = QueryCache(filename=query_cache_filename)
        self.sprint_cache = SprintCache(filename=sprint_cache_filename)
        self.test_mode = test_mode
        self.max_result_size = max_result_size

    def set_test_mode(self, test_mode: bool):
        self.test_mode = test_mode

    def get_issues(self, jql: str, access_token: str, use_cache: bool, expand="changelog", page_size=200, start_at=0, cache_suffix="") -> JiraPageResult:

        cache_id = f"{jql}_{cache_suffix}"

        logger.debug(
            f"get_issues(jql={jql}, use_cache={use_cache}, expand={expand}, page_size={page_size}, start_at={start_at}")

        @profiling()
        def __get_issues(jql: str, use_cache: bool, expand: str, page_size: int, start_at: int) -> JiraPageResult:

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

        return __get_issues(jql, use_cache, expand, page_size, start_at)

    def paginate(self, jql: str, access_token: str, use_cache: bool, page_size=200, cache_suffix="") -> (List[Dict], str):
        page_result = self.get_issues(jql=jql, access_token=access_token, use_cache=use_cache, start_at=0,
                                                  page_size=page_size, cache_suffix=cache_suffix)
        issues = []
        issues.extend(page_result.get_issues())

        while page_result.has_next():
            page_result = self.get_issues(jql=jql, access_token=access_token, use_cache=use_cache,
                                                      start_at=page_result.get_next_start_at(), page_size=page_size, cache_suffix=cache_suffix)
            issues.extend(page_result.get_issues())

        return issues, page_result.get_timestamp()

    def search(self, jql: str, access_token: str, expand: str, page_size: int, start_at: int) -> JiraPageResult:
        jira = self.create_jira(access_token=access_token)
        result_set = jira.search_issues(jql, expand=expand, maxResults=page_size, startAt=start_at)
        issues = [issue.raw for issue in result_set]
        return JiraPageResult(start_at=result_set.startAt, total=result_set.total, timestamp=now(), issues=issues)

    def get_sprints_for_project(self, project_id: str, name_filter: str, activated_date: str, access_token: str, force_reload=False) -> List[Dict[str, str]]:

        if not force_reload:
            sprints = self.sprint_cache.get_sprints(project_id, name_filter, activated_date)
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

        self.sprint_cache.add_sprints(project_id, name_filter, activated_date, sprints)

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
        if self.sprint_cache:
            self.sprint_cache.close()


    def create_jira(self, access_token: str) -> JIRA:
        if ":::" in access_token:
            username_password = access_token.split(":::")
            return JIRA(self.hostname, basic_auth=(username_password[0], username_password[1]))
        else:
            return JIRA(self.hostname, token_auth=access_token)


