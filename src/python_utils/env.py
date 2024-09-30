import os
from functools import wraps


def inject_environment(environment_variables: {}, required=False):
    def wrapper(init_function):
        @wraps(init_function)
        def decorator(*args, **kwargs):
            environment_values = lookup_environment_variables(environment_variables, required)
            return init_function(*environment_values, **kwargs)

        return decorator

    return wrapper


def lookup_environment_variables(environment_variables: [], required: bool) -> []:
    values = []
    for environment_variable_name in environment_variables:
        value = os.getenv(key=environment_variable_name, default=None)
        if not value:
            value = environment_variables[environment_variable_name]
            if value and callable(value):
                value = value()

        if not value and required:
            raise Exception(f"Missing environment variable: {environment_variable_name}")
        values.append(value)

    return values
