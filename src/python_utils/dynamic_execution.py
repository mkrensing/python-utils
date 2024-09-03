from __future__ import annotations
import importlib
from typing import List


class DynamicExecution:

    def __init__(self, module_name: str, method_name: str, default_module_name: str):
        if not module_name and default_module_name:
            module_name = default_module_name
        imported_module = importlib.import_module(module_name)
        self.imported_method = getattr(imported_module, method_name)
        self.name = f"{module_name}.{method_name}"

    def execute(self, parameters: List):
        return self.imported_method(*parameters)

    @staticmethod
    def by_full_name(full_method_name: str, default_module_name="") -> DynamicExecution:
        module_name, method_name = seperate_module_and_method(full_method_name)
        return DynamicExecution(module_name, method_name, default_module_name)


def seperate_module_and_method(full_method_name: str) -> (str, str):
    partitions = full_method_name.rpartition(".")
    module_name = partitions[0]
    method_name = partitions[2]
    return module_name, method_name

