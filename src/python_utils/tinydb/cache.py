from typing import List, Dict
from pathlib import Path
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage
from tinydb import TinyDB, Query
from filelock import FileLock


class JsonCache:

    def __init__(self, filename: str):
        self.filename = filename
        self.lock = FileLock(f"{filename}.lock")
        Path(self.filename).touch()
        self.db = TinyDB(self.filename, storage=CachingMiddleware(JSONStorage))

    def has_item(self, key: str) -> bool:
        return bool(self.get_item(key))

    def get_item(self, key: str) -> Dict:
        cached_items = Query()
        result = self.db.search(cached_items.key == key)
        if not result:
            return {}

        if len(result) != 1:
            raise Exception(f"Found more matches for key: {key}")

        return result[0]["item"]

    def get_not_existing_keys(self, keys: List[str]) -> List[str]:
        cached_items = Query()
        existing_entries = self.db.search(cached_items.key.one_of(keys))
        existing_keys = [entry["key"] for entry in existing_entries]

        return [key for key in keys if key not in existing_keys]

    def get_items(self, keys: List[str]) -> List[Dict]:
        cached_items = Query()
        result = self.db.search(cached_items.key.one_of(keys))
        if not result:
            return {}

        return [entry["item"] for entry in result]

    def get_all(self) -> List[Dict]:
        return [row['item'] for row in self.db.all()]

    def add_item(self, key: str, item: Dict, auto_flush=True):
        cached_items = Query()
        with self.lock:
            self.db.upsert({"key": key, "item": item}, cached_items.key == key)
            if auto_flush:
                self.flush()

    def flush(self):
        with self.lock:
            self.db.storage.flush()

    def close(self):
        if self.db:
            with self.lock:
                self.db.close()
