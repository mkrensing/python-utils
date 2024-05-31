import dateutil.parser
import math
import datetime

# 2018-07-31T09:35:45.000+0000
def convert_jira_timestamp_to_millis(iso8601_timestamp):
    datetime = dateutil.parser.parse(iso8601_timestamp)
    timestamp = datetime.timestamp()

    return int(math.trunc(timestamp))

# 2018-07-31T09:35:45.000+0000
def convert_jira_timestamp_to_text(iso8601_timestamp, pattern="%Y-%V"):
    datetime = convert_jira_timestamp_to_datetime(iso8601_timestamp)
    return datetime.strftime(pattern)

# 2018-07-31T09:35:45.000+0000
def convert_jira_timestamp_to_datetime(iso8601_timestamp: str):
    return dateutil.parser.parse(iso8601_timestamp)


def to_text(datetime):
    return datetime.strftime(format="%Y-%m-%d")


def today():
    return datetime.datetime.today()

MONDAY = 0
class WeekIterator():

    def __init__(self, start_datetime: datetime, end_datetime : datetime):
        self.start_datetime = self.next_weekday(start_datetime - datetime.timedelta(days=1), MONDAY)
        self.end_datetime = self.next_weekday(end_datetime, MONDAY)
        self.current_position = self.start_datetime

    def has_next(self):
        return self.current_position + datetime.timedelta(days=7) <= self.end_datetime

    def move_next(self):
        if self.has_next():
            self.current_position += datetime.timedelta(days=7)
        return self.has_next()

    def get_week(self):
        return self.current_position.strftime(format="%G-%V")

    def get_current_start_datetime(self):
        return self.current_position

    def get_current_end_datetime(self):
        return self.current_position + datetime.timedelta(days=6)

    @staticmethod
    def next_weekday(date: datetime, weekday: int):
        """
        :param d:
        :param weekday:  0 = Monday, 1=Tuesday, 2=Wednesday...
        :return:
        """
        days_ahead = weekday - date.weekday()
        if days_ahead <= 0: # Target day already happened this week
            days_ahead += 7
        return date + datetime.timedelta(days_ahead)