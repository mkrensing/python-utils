from python_utils.jira.jira_client import QueryCache, JiraPageResult
from typing import List, Dict

cache = QueryCache("query_cache.json")
cache.clear()

def create_issues(prefix: str, start_at: int, count: int) -> List[Dict]:
    issues = []
    for index in range(start_at, start_at+count):
        issues.append({ "key": f"{prefix}{index}"})
    return issues

jql = "project = TEST-A"
page_1 = JiraPageResult(start_at=0, total=30, issues=create_issues("TEST-A-", 0, 10))

cache.add_page(jql, page_1)

pages = cache.get_all_pages(jql)

assert pages.get_start_at() == 0
assert pages.get_total() == 30
assert pages.has_next() == True
assert len(pages.get_issues()) == 10

page_2 = JiraPageResult(start_at=10, total=30, issues=create_issues("TEST-A-", 10, 10))
cache.add_page(jql, page_2)

pages = cache.get_all_pages(jql)

assert pages.get_start_at() == 0
assert pages.get_total() == 30
assert pages.has_next() == True
assert len(pages.get_issues()) == 20

page_3 = JiraPageResult(start_at=20, total=30, issues=create_issues("TEST-A-", 20, 10))
cache.add_page(jql, page_3)

pages = cache.get_all_pages(jql)

assert pages.get_start_at() == 0
assert pages.get_total() == 30
assert pages.has_next() == False
assert len(pages.get_issues()) == 30
