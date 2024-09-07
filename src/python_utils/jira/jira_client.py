import sys
import logging
from pathlib import Path
from typing import List, Dict, Callable

from jira import JIRA
from tinydb import TinyDB, Query
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
        return {"nextStartAt": self.get_next_start_at(), "hasNext": self.has_next(), "total": self.total, "issues": self.issues}


class QueryCache:

    def __init__(self, filename: str):
        self.filename = filename
        Path(self.filename).touch()
        self.lock = FileLock(f"{self.filename}.lock")
        self.db = TinyDB(self.filename, storage=CachingMiddleware(JSONStorage))

    def get_all_pages(self, jql: str, start_at: int) -> JiraPageResult:
        issues = []
        first_page = self.get_page(jql, start_at)
        if not first_page:
            return None
        issues.extend(first_page.get_issues())
        page = first_page
        while page.has_next():
            page = self.get_page(jql, page.get_next_start_at())
            if page:
                issues.extend(page.get_issues())

        return JiraPageResult(start_at=start_at, total=first_page.get_total(), issues=issues)


    def get_page(self, jql: str, start_at: int) -> JiraPageResult:
        cached_queries = Query()
        result = self.db.search(cached_queries.key == self.create_key(jql, start_at))
        if not result:
            return None
        if len(result) != 1:
            raise Exception(f"Found two matches for jql: {jql}")

        page = result[0]
        return JiraPageResult(start_at=start_at, total=page["total"], issues=page["issues"])

    def add_page(self, jql, page: JiraPageResult):
        key = self.create_key(jql, page.get_start_at())
        cached_queries = Query()
        with self.lock:
            self.db.upsert({"key": key, "issues": page.get_issues(), "total": page.get_total()}, cached_queries.key == key)
            self.db.storage.flush()

    @staticmethod
    def create_key(jql: str, start_at: int) -> str:
        return f"{jql}_{start_at}"

    def close(self):
        if self.db:
            with self.lock:
                self.db.close()


class JiraClient:

    def __init__(self, hostname: str, query_cache_filename: str, test_mode: bool, max_result_size=700):
        self.hostname = hostname
        self.query_cache = QueryCache(filename=query_cache_filename)
        self.test_mode = test_mode
        self.max_result_size = max_result_size
        self.active_paginations = shared_dict()

    def set_test_mode(self, test_mode: bool):
        self.test_mode = test_mode


    def get_issues(self, jql: str, access_token: str, use_cache: bool, expand="changelog", page_size=200, start_at=0, search_all_in_once=False) -> JiraPageResult:
        logger.debug(f"get_issues(jql={jql}, use_cache={use_cache}, expand={expand}, page_size={page_size}, start_at={start_at}, search_all_in_once={search_all_in_once}")

        @profiling()
        def __get_page_from_cache(jql: str, start_at: int) -> JiraPageResult:
            return self.query_cache.get_all_pages(jql, start_at)

        @profiling()
        def __add_page_to_cache(jql: str, jira_page: JiraPageResult):
            self.query_cache.add_page(jql, jira_page)

        @profiling()
        def __get_issues(jql: str, use_cache: bool, expand: str, page_size:int, start_at: int, search_all_in_once: bool):

            if self.test_mode or use_cache:
                jira_page = __get_page_from_cache(jql, start_at)
                if jira_page:
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
                    next_page = self.search(jql, access_token, expand, page_size, jira_page.get_next_start_at())
                    issues.extend(next_page.get_issues())
                jira_page = JiraPageResult(start_at, jira_page.get_total(), issues)

            if use_cache:
                __add_page_to_cache(jql, jira_page)

            return jira_page

        return __get_issues(jql, use_cache, expand, page_size, start_at, search_all_in_once)

    def search(self, jql: str, access_token: str, expand: str, page_size:int, start_at: int) -> JiraPageResult:
        jira = JIRA(self.hostname, token_auth=access_token)
        result_set = jira.search_issues(jql, expand=expand, maxResults=page_size, startAt=start_at)
        issues = [issue.raw for issue in result_set]
        return JiraPageResult(start_at=result_set.startAt, total=result_set.total, issues=issues)

    def close(self):
        if self.query_cache:
            self.query_cache.close()


