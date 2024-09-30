from typing import List, Dict
from lxml import etree
import re

def remove_namespace_declarations(xml_content: str) -> str:
    # Regex, um alle Namespace-Deklarationen zu finden und zu entfernen
    cleaned_content = re.sub(r'\s+xmlns(:\w+)?="[^"]+"', '', xml_content)
    return cleaned_content


class XMLMatch:

    def __init__(self, element):
        self.element = element

    def text(self) -> str:
        return self.element.text

    def content(self, without_namespaces_declarations=False) -> str:
        text=etree.tostring(self.element, encoding='unicode')
        if without_namespaces_declarations:
            text=remove_namespace_declarations(text)
        return text



class XMLString:

    def __init__(self, xml_content: str):
        self.xml_content = xml_content
        self.namespaces = XMLString.create_namespaces_dict(self.extract_namespaces(xml_content))
        self.root = etree.fromstring(
            f"<root {XMLString.create_namespaces_declarations(self.namespaces)} >{self.xml_content}</root>")

    @staticmethod
    def extract_namespaces(xml_content: str) -> list:
        # Regex, um Präfixe vor Doppelpunkten in XML-Tags zu finden
        pattern = r"<([a-zA-Z_]+):"

        # Alle Übereinstimmungen im Text finden
        matches = re.findall(pattern, xml_content)

        # Doppelte Präfixe entfernen und die Liste zurückgeben
        return list(set(matches))

    @staticmethod
    def create_namespaces_dict(namespaces: List[str]) -> Dict[str, str]:
        return {key: f"http://example.com/{key}" for key in namespaces}

    @staticmethod
    def create_namespaces_declarations(namespaces: Dict[str, str]):
        return ' '.join([f"xmlns:{key}='{url}'" for key, url in namespaces.items()])

    def xpath_first_match(self, xpath: str) -> XMLMatch:
        elements = self.root.xpath(xpath, namespaces=self.namespaces)
        if not elements:
            return None

        return XMLMatch(elements[0])
