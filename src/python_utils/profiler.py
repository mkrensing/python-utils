from __future__ import annotations

import logging
import threading
import time
from functools import wraps
from typing import Callable, Dict, List

logger = logging.getLogger("profiler")
import inspect


class Profiler:

    def __init__(self, name: str, threshold: float, parent: Profiler = None):
        self.name = name
        self.threshold = threshold
        self.start_time: float = 0
        self.duration: float = 0
        self.children = []
        self.parent = parent
        if parent:
            parent.add_child(self)

    def get_parent(self):
        return self.parent

    def add_child(self, profiler: Profiler):
        self.children.append(profiler)

    def start(self):
        self.start_time = time.time()

    def stop(self):
        stop_time = time.time()
        self.duration: float = stop_time - self.start_time

    def get_call_log(self) -> dict:
        if self.duration >= self.threshold:
            duration_text: str = "{:.2f}".format(self.duration)
            return {"name": self.name, "duration": self.duration, "duration_text": duration_text}
        return {}

    def get_log(self, formatting_callback: Callable[[Dict], str]) -> []:

        log = []

        def __add_log(profiler: Profiler, child_level: int):
            call_log = profiler.get_call_log()
            if call_log:
                call_log["level"] = child_level
                log.append(formatting_callback(call_log))

            child_level += 1
            for child in profiler.children:
                __add_log(child, child_level)

        __add_log(self, 0)

        return log

    def is_root(self) -> bool:
        return not bool(self.parent)

    def get_root(self) -> Profiler:
        if self.parent:
            return self.parent.get_root()
        return self


class ProfilerProvider:
    STORAGE = threading.local()
    GLOBAL_VARIABLE_NAME = "profiler"

    @staticmethod
    def get_profiler(name: str, threshold: float) -> Profiler:
        parent_profiler = getattr(ProfilerProvider.STORAGE, ProfilerProvider.GLOBAL_VARIABLE_NAME, None)
        profiler = Profiler(name=name, threshold=threshold, parent=parent_profiler)
        setattr(ProfilerProvider.STORAGE, ProfilerProvider.GLOBAL_VARIABLE_NAME, profiler)

        return profiler

    @staticmethod
    def remove_profiler(profiler: Profiler):
        setattr(ProfilerProvider.STORAGE, ProfilerProvider.GLOBAL_VARIABLE_NAME, profiler.get_parent())


class ProfilingContext:
    GLOBAL_VARIABLE_NAME = "profiler"

    def __init__(self, name: str, log_level: int, threshold: float):
        self.name = name
        self.log_level = log_level
        self.threshold: float = threshold
        self.profiler: Profiler = None
        self.log_messages = []

    def __enter__(self):
        self.profiler = ProfilerProvider.get_profiler(self.name, self.threshold)
        if logger.isEnabledFor(self.log_level):
            self.profiler.start()

        return logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        if logger.isEnabledFor(self.log_level):
            self.profiler.stop()
            self.dump(self.profiler)
        ProfilerProvider.remove_profiler(self.profiler)

    def dump(self, profiler: Profiler):

        if not profiler.is_root():
            return

        def format_log_entry(log_entry: dict) -> str:
            prefix = log_entry["level"] * " "
            return f"[{log_entry['duration_text']}] {prefix} {log_entry['name']}"

        log_stack = profiler.get_root().get_log(format_log_entry)
        for log_entry in log_stack:
            self.log(log_entry)

    def log(self, msg, *args, **kwargs):
        logger._log(self.log_level, msg, args, **kwargs)


def profiling(name: str = None, log_level: int = logging.INFO, threshold: float = 0.1, include_parameters=True):

    def get_parameter_values(arguments_spec, args, kwargs) -> []:
        parameter_values = []
        arg_length = len(args)
        arg_index = 0
        arg_kwargs_index = 0
        arg_default_index = 0

        for parameter_name in arguments_spec.args:
            if arg_length > arg_index:
                parameter_values.append(args[arg_index])
                arg_index += 1
            elif parameter_name in kwargs:
                parameter_values.append(kwargs[parameter_name])
                arg_kwargs_index += 1
            else:
                parameter_values.append(arguments_spec.defaults[arg_default_index])
                arg_default_index += 1

        return parameter_values

    def get_profiler_name(executed_function, args: List, kwargs: Dict) -> str:
        profiler_name = name or executed_function.__name__
        if include_parameters:
            arguments = []
            arguments_spec = inspect.getfullargspec(executed_function)
            # print(f"INSPECT: {inspect.getfullargspec(executed_function)}")
            parameter_values = get_parameter_values(arguments_spec, args, kwargs)
            for parameter_name, parameter_value in zip(arguments_spec.args,
                                                       get_parameter_values(arguments_spec, args, kwargs)):
                if parameter_name != "self":
                    arguments.append(f"{parameter_name}={parameter_value}")
            if arguments:
                profiler_name = f"{profiler_name}{arguments}"

        return profiler_name

    def wrapper(executed_function):
        @wraps(executed_function)
        def decorator(*args, **kwargs):
            with profiler(get_profiler_name(executed_function, args=args, kwargs=kwargs), log_level, threshold):
                return executed_function(*args, **kwargs)

        return decorator

    return wrapper


def profiler(name: str, log_level: int = logging.INFO, threshold: float = 0.1) -> ProfilingContext:
    return ProfilingContext(name=name, log_level=log_level, threshold=threshold)
