import errno
import os
from typing import List

from tinydb import TinyDB, Query


def create_file_with_path(filename: str):
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


class BaseSettingsProvider:

    def __init__(self):
        self.db: TinyDB = None

    def load(self, filename):
        create_file_with_path(filename)
        self.db = TinyDB(filename)

    def set(self, property_name, property_value):
        settings_query = Query()
        settings = self.db.get(settings_query.name == property_name)
        if not settings:
            settings = {'name': property_name, 'value': property_value}
        else:
            settings['value'] = property_value

        self.db.upsert(settings, settings_query.name == property_name)

    def get(self, property_name):
        settings_query = Query()
        try:
            settings = self.db.get(settings_query.name == property_name)
            if not settings:
                return None
        except Exception as e:
            return None

        return settings['value']

    def has(self, property_name):
        if self.get(property_name):
            return True
        else:
            return False

    def remove(self, property_name):
        settings_query = Query()
        self.db.remove(settings_query.name == property_name)

    def get_all(self) -> List:
        return self.db.all()

    def as_dict(self) -> dict:
        result = {}
        for entry in self.get_all():
            result[entry["name"]] = entry["value"]
        return result

    def close(self):
        self.db.close()
