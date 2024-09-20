from typing import List, Tuple
from datetime import datetime, timedelta, date, timezone

def last_day_of_month(any_day):
    # The day 28 exists in every month. 4 days later, it's always next month
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    # subtracting the number of the current day brings us back one month
    return next_month - datetime.timedelta(days=next_month.day)

def get_first_and_last_day_of_current_month() -> Tuple[datetime.date, datetime.date, str]:
    now = datetime.now()
    return get_first_and_last_day_of_month(now)


def get_first_and_last_day_of_month(month: datetime.date) -> Tuple[datetime.date, datetime.date, str]:
    start_of_month = datetime(month.year, month.month, 1)
    start_of_next_month = start_of_month + timedelta(days=32)
    start_of_next_month = start_of_next_month.replace(day=1)
    end_of_month = start_of_next_month - timedelta(days=1)

    return start_of_month, end_of_month, start_of_month.strftime("%B %Y")


def get_first_day_of_next_month(reference_date: datetime.date) -> datetime.date:
    start_of_month = datetime(reference_date.year, reference_date.month, 1)
    return start_of_month + timedelta(days=32)


def iterate_months(start_date: str) -> List[Tuple[str, str, str]]:
    last_day_of_last_month = get_first_and_last_day_of_current_month()[0] - timedelta(days=1)
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    months = []

    while current_date <= last_day_of_last_month:
        start_of_month, end_of_month, month_name = get_first_and_last_day_of_month(current_date)
        months.append((start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"), month_name ))
        current_date = get_first_day_of_next_month(current_date)

    return months


def iterate_weeks(start_date: str) -> List[Tuple[str, str]]:
    iterating_start_date = get_week_starting_date(start_date)
    iterating_end_date = get_current_week_starting_date()
    weeks = []

    for week_start_date in get_date_range(iterating_start_date, iterating_end_date, step=7):
        week_end_date = week_start_date + timedelta(days=6)
        weeks.append((week_start_date, week_end_date))

    return weeks


def iterate_calender_weeks(start_date: str) -> List[str]:
    iterating_start_date = get_week_starting_date(start_date)
    iterating_end_date = get_current_week_starting_date()
    calender_weeks = []

    for week_start_date in get_date_range(iterating_start_date, iterating_end_date, step=7):
        calender_weeks.append(get_calendar_week(week_start_date))

    return calender_weeks


def get_week_starting_date(start_date: str) -> date:
    reference_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    return reference_date + timedelta(days=-reference_date.weekday())


def get_current_week_starting_date() -> date:
    today = date.today()
    return today + timedelta(days=-today.weekday(), weeks=1)


def get_date_range(start_date: date, end_date: date, step=1) -> List[datetime.date]:
    date_range = []
    current_date = start_date
    date_range.append(current_date)
    while current_date <= end_date:
        current_date = current_date + timedelta(days=step)
        date_range.append(current_date)

    return date_range


def get_calendar_week(start_date: date) -> str:
    return str(start_date.isocalendar().week)

def from_iso_date(timestamp_iso_format: str) -> date:
    if not timestamp_iso_format or timestamp_iso_format == "<null>":
        return None

    return datetime.fromisoformat(timestamp_to_date(timestamp_iso_format)).date()

def timestamp_to_date(timestamp_iso_format: str) -> str:
    return timestamp_iso_format.split("T")[0]

def now() -> str:
    current_time_zone = datetime.now(timezone.utc).astimezone().tzinfo
    current_date = datetime.now(current_time_zone)
    return current_date.isoformat()