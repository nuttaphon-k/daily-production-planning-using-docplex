import os
import sys
import numpy as np
from datetime import datetime


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def create_time_for_comparison(time: str):
    (hour, min) = time.split(':')
    return datetime(year=2022, month=1, day=1, hour=int(hour), minute=int(min))


def is_time_between(start: datetime, end: datetime, t: datetime):
    if (start.time() <= t.time()) & (t.time() < end.time()):
        return True
    return False


def get_minute_between_timestamp(start: datetime, end: datetime):
    seconds = (end - start).seconds

    return int(np.ceil(seconds/60))

def is_date_format(date_str:str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except:
        return False