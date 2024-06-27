import os
import importlib.util
from fastapi.logger import logger


def import_all_modules():
    modules = []
    directory = os.path.dirname(__file__)
    for filename in os.listdir(directory):
        if filename.endswith(".py") and filename != "__init__.py" and filename != "example_parser.py":
            module_name = filename[:-3]
            module_path = os.path.join(directory, filename)
            spec = importlib.util.spec_from_file_location(
                module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            modules.append(module.parser)
    return modules


parsers = import_all_modules()
parsers_dict = {parser.parser_id: parser for parser in parsers}