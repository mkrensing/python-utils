from python_utils.jira.jira_batch import JiraBatchConfig

config = {
    "start_date": "2024-01-01",
    "batch_jql": "project = TEST AND (resolved >= {start_of_month} and resolved <= {end_of_month})",
    "jql": "project = TEST AND (resolved >= {start_of_month} and resolved <= {end_of_month})"
}
batch_config = JiraBatchConfig(config)
queries = batch_config.create_batch_config()
print(queries)