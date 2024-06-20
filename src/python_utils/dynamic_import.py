import glob
from typing import Dict, List
import os
import importlib.util


def find_files(search_pattern: str, root_dir='.') -> List:
    return glob.glob(os.path.join(root_dir, search_pattern), recursive=True)


def import_modules(directory_path: str) -> Dict:
    module_names = []
    for filename in find_files(directory_path):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            module_names.append(module_name)

    modules = {}
    for module_name in module_names:
        spec = importlib.util.spec_from_file_location(name=module_name, location=f"{module_name}.py")
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            modules[module_name] = module

    return modules
