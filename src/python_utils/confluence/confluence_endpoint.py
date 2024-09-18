from flask import Blueprint

from python_utils.confluence.confluence_client import ConfluenceClient
from python_utils.flask.endpoint import response_json
from python_utils.env import inject_environment


@inject_environment({"CONFLUENCE_HOSTNAME": "", "CONFLUENCE_ACCESS_TOKEN": ""})
def create_confluence_client(hostname: str, access_token: str) -> ConfluenceClient:
    return ConfluenceClient(hostname, access_token)


@inject_environment({"CONFLUENCE_PAGE_ID": ""})
def get_config_page_id(page_id: str) -> str:
    return page_id


confluence_endpoint = Blueprint('confluence_endpoint', __name__, url_prefix='/rest/confluence')
confluence_client = create_confluence_client()


@confluence_endpoint.route('/config/<config_id>')
def get_board_config(config_id):
    try:
        config = confluence_client.get_config(get_config_page_id(), config_id)

        return response_json(config)
    except Exception as e:
        return response_json({"error": str(e)}), 400


@confluence_endpoint.route('/file/<page_id>/<filename>')
def get_file(page_id: str, filename: str):
    try:
        config = confluence_client.get_file(page_id, filename)
        return response_json(config)
    except Exception as e:
        return response_json({"error": str(e)}), 400
