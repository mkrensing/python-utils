from typing import List, Dict
from lxml import etree


class XMLString:

    def __init__(self, xml_content: str, namespaces: List[str]):
        self.xml_content = xml_content
        self.namespaces = XMLString.create_namespaces_dict(namespaces)
        self.root = etree.fromstring(
            f"<root {XMLString.create_namespaces_declarations(self.namespaces)} >{self.xml_content}</root>")

    @staticmethod
    def create_namespaces_dict(namespaces: List[str]) -> Dict[str, str]:
        return {key: f"http://example.com/{key}" for key in namespaces}

    @staticmethod
    def create_namespaces_declarations(namespaces: Dict[str, str]):
        return ' '.join([f"xmlns:{key}='{url}'" for key, url in namespaces.items()])

    def xpath_first_match(self, xpath: str) -> str:
        elements = self.root.xpath(xpath, namespaces=self.namespaces)
        if not elements:
            return None

        return elements[0].text