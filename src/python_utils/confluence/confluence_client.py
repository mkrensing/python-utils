from typing import Dict

import requests
import yaml

from python_utils.file import lookup_file
from python_utils.xml import XMLString


class ConfluenceClient:

    def __init__(self, hostname: str, access_token: str):
        self.hostname = hostname
        self.access_token = access_token

    def get_config(self, page_id: str, config_id: str) -> Dict:

        if not self.hostname:
            return { **self.get_testdata("General"), **self.get_testdata(config_id) }

        xml_content = self.get_page_xml_content(page_id)

        general_config = self.get_config_by_xml_content("General", xml_content) or {}
        config = self.get_config_by_xml_content(config_id, xml_content) or {}

        return {**general_config, **config}

    def get_page_xml_content(self, page_id: str) -> str:

        url = f"{self.hostname}/rest/api/content/{page_id}?expand=body.storage"

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(
                f'Failed to load config: {response.status_code} {response.text}')

        page = response.json()
        xml_content = page["body"]["storage"]["value"]

        return xml_content

    @staticmethod
    def get_config_by_xml_content(config_id: str, xml_content: str) -> None | Dict:
        xml_string = XMLString(xml_content)
        board_configuration = xml_string.xpath_first_match(
            f"//ac:structured-macro[@ac:name='code'][ac:parameter[@ac:name='title' and text()='{config_id}']]/ac:plain-text-body")
        if not board_configuration:
            return None

        return yaml.safe_load(board_configuration.text().replace("\t", "  "))


    def get_file(self, page_id: str, filename: str) -> str:

        # Setze die Basis-URL für den Anhang-Endpunkt
        url = f"{self.hostname}/confluence/rest/api/content/{page_id}/child/attachment"

        # Header mit dem Access Token erstellen
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(f'Failed to fetch attachments: {response.status_code} {response.text}')

        # Suche nach dem Anhang mit dem angegebenen Dateinamen
        attachments = response.json().get('results', [])
        attachment = next((att for att in attachments if att['title'] == filename), None)

        if not attachment:
            raise Exception(f'Attachment {filename} not found on page {page_id}')

        # Hole die URL der neuesten Version des Anhangs
        attachment_url = attachment['_links']['download']
        download_url = f'{self.hostname}/confluence{attachment_url}'

        # Lade die Datei herunter
        download_response = requests.get(download_url, headers=headers, stream=True)

        if download_response.status_code != 200:
            raise Exception(
                f'Failed to download attachment: {download_response.status_code} {download_response.text}')

        content_type = download_response.headers.get('Content-Type', '')

        if 'text' in content_type or 'json' in content_type:
            content = ''.join(chunk.decode('utf-8') for chunk in download_response.iter_content(chunk_size=8192))
        else:
            content = b''.join(chunk for chunk in download_response.iter_content(chunk_size=8192)).decode('utf-8')

        return content

    @staticmethod
    def get_testdata(config_id: str) -> Dict:
        filename = lookup_file(f"testdata/{config_id}.yaml")
        with open(filename, "r", encoding="UTF-8") as testfile:
            return yaml.safe_load(testfile.read().replace("\t", "  "))
