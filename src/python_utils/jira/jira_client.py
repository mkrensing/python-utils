from pathlib import Path
from typing import List, Dict, Callable

from jira import JIRA
from tinydb import TinyDB, Query
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage

from python_utils.profiler import profiling
from filelock import FileLock


class QueryCache:

    def __init__(self, filename: str):
        self.filename = filename
        Path(self.filename).touch()
        self.lock = FileLock(f"{self.filename}.lock")
        self.db = TinyDB(self.filename, storage=CachingMiddleware(JSONStorage))

    def get_issues(self, jql: str) -> List[Dict]:
        cached_queries = Query()
        result = self.db.search(cached_queries.jql == jql)
        if not result:
            return []
        if len(result) != 1:
            raise Exception(f"Found two matches for jql: {jql}")
        return result[0]["issues"]

    def add_issues(self, jql, issues: List[Dict]):
        cached_queries = Query()
        with self.lock:
            self.db.upsert({"jql": jql, "issues": issues}, cached_queries.jql == jql)
            self.db.storage.flush()

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

    def set_test_mode(self, test_mode: bool):
        self.test_mode = test_mode

    def get_issues(self, jql: str, access_token: str, use_cache: False, page_size=200) -> List[Dict]:

        print(f"get_issues({jql}, use_cache={use_cache}, page_size={page_size})")

        @profiling(include_parameters=True)
        def __get_issues(__jql: str):

            if self.test_mode or use_cache:
                issues = self.query_cache.get_issues(__jql)
                if issues:
                    return issues

            issues = self.search_all(__jql, expand="changelog", access_token=access_token, page_size=page_size)

            if self.test_mode or use_cache:
                self.query_cache.add_issues(__jql, issues)

            return issues

        return __get_issues(jql)

    def search_all(self, jql: str, expand: str, access_token: str, page_size=500) -> List[Dict]:

        if self.test_mode:
            print(f"TEST_MODE active. Return empty result for jql {jql}")
            return []

        jira = JIRA(server=self.hostname, token_auth=access_token)
        issues = []

        result_set = jira.search_issues(jql, expand=expand, maxResults=50)
        if result_set.total > self.max_result_size:
            raise Exception(f"Resultset is to large. Size: {result_set.total} over {self.max_result_size}")

        while result_set.startAt < result_set.total:
            for issue in result_set:
                issues.append(issue.raw)
            next_page_start_at = result_set.startAt + len(result_set)
            result_set = jira.search_issues(jql, expand=expand, maxResults=page_size, startAt=next_page_start_at)

        return issues

    def close(self):
        if self.query_cache:
            self.query_cache.close()
