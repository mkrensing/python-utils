from multiprocessing.managers import SyncManager
from typing import Dict, Any

class FlaskShareSyncManager(SyncManager):
    pass

shared_data = {}
def get_shared_data():
    return shared_data

class GlobalDataStore:

    def __init__(self, port: int = 120000):
        FlaskShareSyncManager.register("shared_data", get_shared_data)
        self.manager = FlaskShareSyncManager(("127.0.0.1", port), authkey='password'.encode('utf-8'))
        self.shared_data = None

    def start(self):
        self.manager.start()
        self.manager.connect()
        self.shared_data = self.manager.shared_data()

    def stop(self):
        self.manager.shutdown()

    def update(self, key: str, value: Dict[Any, Any]):
        self.shared_data.update({key: value })

    def get_data(self, key: str) -> Dict[Any, Any]:
        return self.shared_data.get(key) or {}

    def delete_key(self, key_name: str):
        self.update({ key_name: None })


global_data_share = GlobalDataStore()

def init_global_data_share():
    global_data_share.start()