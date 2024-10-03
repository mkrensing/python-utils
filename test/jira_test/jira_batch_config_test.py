from python_utils.jira.jira_batch import JiraBatchConfig

config = {
    "start_date": "2024-01-01",
    "batch_jql": "project = TEST AND (resolved >= {start_of_month} and resolved <= {end_of_month})",
    "jql": "project = TEST AND (resolved >= {start_of_month} and resolved <= {end_of_month})"
}
batch_config = JiraBatchConfig(config)
queries = batch_config.create_batch_config()
assert queries[0]["use_cache"] == True
assert queries[-1]["use_cache"] == False

queries = batch_config.create_batch_config(reload_all=True)
assert queries[0]["use_cache"] == False
assert queries[-1]["use_cache"] == False

queries = batch_config.create_batch_config(reload_current=False)
assert queries[0]["use_cache"] == True
assert queries[-1]["use_cache"] == True