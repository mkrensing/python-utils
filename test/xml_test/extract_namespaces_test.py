from python_utils.xml import XMLString

xml = XMLString("<a:test>Ich bin Text</a:test><b:test><c:content /></b:test>")
print(xml.xpath_first_match("//a:test").text())
print(xml.xpath_first_match("//b:test").content(without_namespaces_declarations=True))

