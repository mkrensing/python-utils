NOT_FOUND = "90adfojkn34iufg98u34"


class SmartDict:

    def __init__(self, config: dict):
        self.config = config or dict()
        pass

    def contains(self, config_path: str | list) -> bool:
        if isinstance(config_path, str):
            return self.contains(config_path.split("."))

        return self.__contains(config_path)

    def __contains(self, config_path: []):

        assert isinstance(config_path, list)
        config_key = config_path[0]
        if config_key not in self.config:
            return False

        if len(config_path) > 1:
            config_path.pop(0)
            return SmartDict(self.config[config_key]).__contains(config_path)
        else:
            return True

    def get(self, config_path: str | list, default_value=NOT_FOUND):
        if isinstance(config_path, str):
            return self.get(config_path.split("."), default_value=default_value)

        full_config_path = list(config_path)
        value = self.__get(config_path, default_value)
        if value == NOT_FOUND:
            raise Exception(f"No value for path: {full_config_path}. Could not resolve: {config_path}")

        return value

    def __get(self, config_path: [], default_value):

        assert isinstance(config_path, list)
        config_key = config_path[0]
        if config_key not in self.config:
            return default_value

        if len(config_path) > 1:
            config_path.pop(0)
            return SmartDict(self.config[config_key]).__get(config_path, default_value=default_value)
        else:
            return self.config[config_key]

    def __contains__(self, item):
        return self.contains(item)

    def __getitem__(self, item):
        return self.get(item)


def merge_dicts(a: dict, b: dict, path=[]):
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] != b[key]:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a
