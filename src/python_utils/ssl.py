import os
import certifi
from python_utils.file import file_exists

def register_root_certificate(root_ca_filename: str):

    if not file_exists(root_ca_filename):
        raise Exception(f"FileNotFound: {root_ca_filename}")

    with open(root_ca_filename, 'rb') as infile:
        certificate = infile.read()
        cafile = certifi.where()
        with open(cafile, 'rb') as outfile:
            missing_certificate = certificate not in outfile.read()
        if missing_certificate:
            with open(cafile, 'ab') as outfile:
                outfile.write(b'\n')
                outfile.write(certificate)
                print(f"Added Root Cert to {cafile}.")
                import certifi.core

    os.environ["REQUESTS_CA_BUNDLE"] = cafile