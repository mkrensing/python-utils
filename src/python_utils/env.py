import os
from functools import wraps


def inject_environment(environment_variables: {}):
    def wrapper(init_function):
        @wraps(init_function)
        def decorator(*args, **kwargs):
            environment_values = lookup_environment_variables(environment_variables)
            return init_function(*environment_values, **kwargs)

        return decorator

    return wrapper


def lookup_environment_variables(environment_variables: []) -> []:
    values = []
    for environment_variable_name in environment_variables:
        values.append(
            os.getenv(key=environment_variable_name, default=environment_variables[environment_variable_name]))

    return values
