import requests
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives import serialization

JWT_PUBLIC_KEY_LOADER = "JWT_PUBLIC_KEY_LOADER"
JWT_TOKEN_LOCATION = "JWT_TOKEN_LOCATION"
JWT_ALGORITHM = "JWT_ALGORITHM"

class JWTConfigurator:

    def __init__(self, public_key_loader_config_value):
        self.public_key_loader_config_value = public_key_loader_config_value

    def configure(self, jwt):
        if self.is_filename_configured():
            jwt.decode_key_loader(FileKeyLoaderCallback(self.get_configuration_value()))
            return

        if self.is_url_configured():
            jwt.decode_key_loader(JsonWebTokenKeyLoaderCallback(self.get_configuration_value()))
            return

        raise Exception(f"Unbekannter Konfigurationswert: {self.public_key_loader_config_value}")

    def is_filename_configured(self):
        return self.public_key_loader_config_value.startswith("file:")

    def is_url_configured(self):
        return self.public_key_loader_config_value.startswith("url:")

    def get_configuration_value(self):
        return self.public_key_loader_config_value.split(":", 1)[1]


def extract_public_key_from_cert(cert_str):
    cert_obj = load_pem_x509_certificate(cert_str.encode('utf-8'))
    return cert_obj.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)


class JsonWebTokenKeyLoaderCallback:

    def __init__(self, url):
        self.url = url
        self.public_key = self.extract_public_key(url)

    def __call__(self, jwt_header, jwt_data):
        return self.public_key

    @staticmethod
    def extract_public_key(url):
        json_web_token = requests.get(url).json()
        certificate_data = json_web_token['keys'][0]['x5c'][0]
        certificate = f"-----BEGIN CERTIFICATE-----\n{certificate_data}\n-----END CERTIFICATE-----\n"
        return extract_public_key_from_cert(certificate)


class FileKeyLoaderCallback:

    def __init__(self, filename):
        self.filename = filename
        self.public_key = open(filename, 'rb').read()

    def __call__(self, unverified_headers, unverified_claims):
        return self.public_key
