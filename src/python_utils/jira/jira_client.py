import sys
import logging
from pathlib import Path
from typing import List, Dict, Callable

from jira import JIRA
from tinydb import TinyDB, Query, where
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage

from filelock import FileLock
from python_utils.flask.shared import shared_dict
from python_utils.profiler import profiling

logger = logging.getLogger(__name__)


class JiraPageResult:

    def __init__(self, start_at: int, total: int, issues: List[Dict]):
        self.start_at = start_at
        self.total = total
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

    def __dict__(self) -> Dict:
        return {"nextStartAt": self.get_next_start_at(), "hasNext": self.has_next(), "total": self.total,
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
        for page in result:
            issues.extend(page["issues"])
            total = max(total, page["total"])

        return JiraPageResult(start_at=start_at, total=total, issues=issues)

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
        return JiraPageResult(start_at=start_at, total=page["total"], issues=page["issues"])

    def add_page(self, jql, page: JiraPageResult):
        cached_queries = Query()
        with self.lock:
            self.db.upsert(
                {"jql": jql, "startAt": page.get_start_at(), "total": page.get_total(), "issues": page.get_issues()},
                (cached_queries.jql == jql) & (cached_queries.startAt == page.get_start_at()))
            self.db.storage.flush()

    def clear(self):
        with self.lock:
            self.db.truncate()

    def close(self):
        if self.db:
            with self.lock:
                self.db.close()


class SprintCache:

    def __init__(self, filename: str):
        self.filename = filename
        Path(self.filename).touch()
        self.lock = FileLock(f"{self.filename}.lock")
        self.db = TinyDB(self.filename, storage=CachingMiddleware(JSONStorage))

    def get_sprints(self, project_id: str) -> List[Dict[str, str]]:
        cached_queries = Query()
        result = self.db.search((cached_queries.project_id == project_id) & (cached_queries.timestamp == self.current_timestamp()))
        if not result:
            return None

        return result[0]["sprints"]

    def add_sprints(self, project_id: str, sprints: List[Dict[str, str]]):
        cached_queries = Query()
        with self.lock:
            self.db.upsert({"project_id": project_id, "timestamp": self.current_timestamp(), "sprints": sprints }, (cached_queries.project_id == project_id))
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
            with self.lock:
                self.db.close()


class JiraClient:

    def __init__(self, hostname: str, query_cache_filename: str, sprint_cache_filename: str, jira_backend_lock_filename: str, test_mode: bool, max_result_size=700):
        self.hostname = hostname
        self.query_cache = QueryCache(filename=query_cache_filename)
        self.sprint_cache = SprintCache(filename=sprint_cache_filename)
        Path(jira_backend_lock_filename).touch()
        self.jira_backend_lock = FileLock(jira_backend_lock_filename)
        self.test_mode = test_mode
        self.max_result_size = max_result_size
        self.active_paginations = shared_dict()

    def set_test_mode(self, test_mode: bool):
        self.test_mode = test_mode

    def get_issues(self, jql: str, access_token: str, use_cache: bool, expand="changelog", page_size=200, start_at=0,
                   search_all_in_once=False) -> JiraPageResult:
        logger.debug(
            f"get_issues(jql={jql}, use_cache={use_cache}, expand={expand}, page_size={page_size}, start_at={start_at}, search_all_in_once={search_all_in_once}")

        @profiling()
        def __add_page_to_cache(jql: str, jira_page: JiraPageResult):
            self.query_cache.add_page(jql, jira_page)

        @profiling()
        def __get_issues(jql: str, use_cache: bool, expand: str, page_size: int, start_at: int,
                         search_all_in_once: bool) -> JiraPageResult:

            if self.test_mode or use_cache:
                jira_page = self.query_cache.get_all_pages(jql, start_at)
                if jira_page:
                    logger.info(
                        f"Return cached issues for {jql}: Total={jira_page.get_total()} / issues: {len(jira_page.get_issues())}")
                    return jira_page

            if self.test_mode:
                logger.info(f"TEST_MODE active. Return empty result for jql {jql}")
                return JiraPageResult(start_at=0, total=0, issues=[])

            jira_page = self.search(jql, access_token, expand, page_size, start_at)

            if search_all_in_once:
                next_page = jira_page
                issues = []
                issues.extend(jira_page.get_issues())
                while next_page.has_next():
                    next_page = self.search(jql, access_token, expand, page_size, next_page.get_next_start_at())
                    issues.extend(next_page.get_issues())
                jira_page = JiraPageResult(start_at, len(issues), issues)
                logger.info(f"search_all_in_once activ! Return for {jql}: List with {jira_page.get_total()} issues")

            if use_cache:
                logger.info(f"Add {jql} to cache: {len(jira_page.get_issues())} items")
                __add_page_to_cache(jql, jira_page)

            return jira_page

        return __get_issues(jql, use_cache, expand, page_size, start_at, search_all_in_once)

    def search(self, jql: str, access_token: str, expand: str, page_size: int, start_at: int) -> JiraPageResult:
        with self.jira_backend_lock:
            jira = JIRA(self.hostname, token_auth=access_token)
            result_set = jira.search_issues(jql, expand=expand, maxResults=page_size, startAt=start_at)
            issues = [issue.raw for issue in result_set]
            return JiraPageResult(start_at=result_set.startAt, total=result_set.total, issues=issues)

    def get_sprints_for_project(self, project_id: str, name_filter: str, activated_date: str, access_token: str) -> List[Dict[str, str]]:

        sprints = self.sprint_cache.get_sprints(project_id)
        if sprints:
            return sprints

        with self.jira_backend_lock:
            sprint_ids = []
            sprints = []
            jira = JIRA(self.hostname, token_auth=access_token)
            boards = self.get_boards_for_project(jira, project_id, name_filter)
            print(f"boards: {boards}")
            for board in boards:
                for sprint in [ sprint.raw for sprint in jira.sprints(board_id=board["id"]) ]:
                    if "activatedDate" in sprint and sprint["activatedDate"] >= activated_date and sprint["id"] not in sprint_ids:
                        sprint_ids.append(sprint["id"])
                        sprints.append(sprint)

            self.sprint_cache.add_sprints(project_id, sprints)

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
