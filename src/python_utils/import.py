from typing import Dict
import os
import importlib.util


def import_all_modules_from_directory(directory_path: str) -> Dict:
    module_names = []
    for filename in os.listdir(directory_path):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            module_names.append(module_name)

    modules = {}
    for module_name in module_names:
        module_path = os.path.join(directory_path, f"{module_name}.py")
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            modules[module_name] = module

    return modules