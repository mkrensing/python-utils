import time
from threading import Thread
from functools import wraps
import schedule

scheduler_running = False


def __schedule_task():
    global scheduler_running
    while scheduler_running:
        schedule.run_pending()
        time.sleep(1)

def stop_scheduler():
    print("stop scheduler...")
    global scheduler_running
    scheduler_running=False

def scheduled_task(interval_minutes):
    global scheduler_running
    if not scheduler_running:
        scheduler_running = True
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



