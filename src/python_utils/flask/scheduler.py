import time
from threading import Thread
from functools import wraps
import schedule
from python_utils.flask.shared import shared_dict

scheduler_running = shared_dict()


def __schedule_task():
    while "running" in scheduler_running:
        schedule.run_pending()
        time.sleep(1)


def stop_scheduler():
    del scheduler_running["running"]


def scheduled_task(interval_minutes):
    if "running" in scheduler_running:
        def wrapper(func):
            @wraps(func)
            def decorator(*args, **kwargs):
                return func(*args, **kwargs)

            return decorator

        return wrapper

    scheduler_running["running"] = True
    schedule_thread = Thread(target=__schedule_task)
    schedule_thread.start()

    def wrapper(func):
        print(f"Register for scheduler with interval [{interval_minutes}]: {str(func)}")
        schedule.every(interval_minutes).minutes.do(func)

        @wraps(func)
        def decorator(*args, **kwargs):
            return func(*args, **kwargs)

        return decorator

    return wrapper
