import traceback
from collections.abc import MutableMapping, MutableSequence
from multiprocessing.managers import SyncManager
from typing import Dict, Any, List
import inspect


class FlaskShareSyncManager(SyncManager):
    pass


shared_data = {}


def get_shared_data():
    return shared_data


class GlobalDataStore:

    def __init__(self, port: int = 12000):
        FlaskShareSyncManager.register("shared_data", get_shared_data)
        self.manager = FlaskShareSyncManager(("127.0.0.1", port), authkey='password'.encode('utf-8'))
        self.shared_data = None

    def start(self):
        self.manager.start()

    def connect(self):
        self.manager.connect()
        self.shared_data = self.manager.shared_data()

    def stop(self):
        self.manager.shutdown()

    def update(self, key: str, value: Dict[Any, Any]):
        self.shared_data.update({key: value})

    def get_data(self, key: str, default: Any) -> Dict[Any, Any]:
        return self.shared_data.get(key) or default

    def delete_key(self, key_name: str):
        self.update({key_name: None})


my_global_data_share = GlobalDataStore()


class SharedDataProxyDict(MutableMapping):
    def __init__(self, name: str, global_data_store: GlobalDataStore):
        self.name = name
        self.global_data_store = global_data_store

    def get_data(self) -> Dict:
        return dict(self.global_data_store.get_data(self.name, {}))

    def __getitem__(self, key):
        return self.get_data().get(key)

    def __setitem__(self, key, value):
        stored_dict = self.get_data()
        stored_dict[key] = value
        self.global_data_store.update(self.name, stored_dict)

    def __delitem__(self, key):
        stored_dict = self.get_data()
        del stored_dict[key]
        self.global_data_store.update(self.name, stored_dict)

    def __iter__(self):
        # Fetch all keys by getting the entire dataset (assuming there's a method to get all keys)
        return iter(self.get_data())

    def __len__(self):
        # Fetch the length of the dataset
        return len(self.get_data())

    def __repr__(self):
        # Fetch all data for a representation
        return repr(self.get_data())

    def __contains__(self, key) -> bool:
        return key in self.get_data()


class SharedDataProxyList(MutableSequence):
    def __init__(self, name: str, global_data_store: GlobalDataStore):
        self.name = name
        self.global_data_store = global_data_store

    def get_data(self) -> List:
        return list(self.global_data_store.get_data(self.name, []))

    def __getitem__(self, index):
        return self.get_data()[index]

    def __setitem__(self, index, value):
        data = self.get_data()
        data[index] = value
        self.global_data_store.update(self.name, data)

    def __delitem__(self, index):
        data = self.get_data()
        del data[index]
        self.global_data_store.update(self.name, data)

    def __len__(self):
        data = self.get_data()
        return len(data)

    def insert(self, index, value):
        data = self.get_data()
        data.insert(index, value)
        self.global_data_store.update(self.name, data)

    def __repr__(self):
        data = self.get_data()
        return repr(data)

    def __contains__(self, key) -> bool:
        return key in self.get_data()


def get_unique_id() -> str:
    caller_frame_info = inspect.stack()[2]
    return f"{caller_frame_info.filename}_{caller_frame_info.lineno}"


def shared_dict() -> Dict:
    return SharedDataProxyDict(name=get_unique_id(), global_data_store=my_global_data_share)


def shared_list() -> List:
    return SharedDataProxyList(name=get_unique_id(), global_data_store=my_global_data_share)


class GlobalDataShareContext:

    def __init__(self, global_data_store: GlobalDataStore):
        self.global_data_store = global_data_store

    def __enter__(self):
        self.global_data_store.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # destroy_global_data_share_on_exit()
        pass


def global_data_share(start_global_data_share_server: bool) -> GlobalDataShareContext:
    if start_global_data_share_server:
        init_global_data_share()

    return GlobalDataShareContext(my_global_data_share)


def init_global_data_share():
    my_global_data_share.start()


def destroy_global_data_share():
    my_global_data_share.stop()


def destroy_global_data_share_on_exit():
    import signal
    import atexit
    signal.signal(signal.SIGTERM, lambda *x: global_data_share.stop())
    atexit.register(lambda *x: global_data_share.stop())
