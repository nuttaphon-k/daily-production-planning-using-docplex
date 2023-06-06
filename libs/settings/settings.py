from datetime import datetime, timedelta

from const import DEFUALT_RUN_TIME_LIMIT, OT
from const.working_hour import working_hour_interval



class Settings:
    def __init__(self):
        current_timestamp = datetime.now()
        start_working_hour = current_timestamp + timedelta(days=1)
        start_working_hour = datetime.strptime(
            start_working_hour.strftime(
                '%Y-%m-%d') + ' {}'.format(working_hour_interval[0][0]),
            '%Y-%m-%d %H:%M'
        )

        self.settings = {
            "STAGE": 'prod',
            "start_working_hour": start_working_hour,
            "run_time_limit": DEFUALT_RUN_TIME_LIMIT,
            "holiday": [],
            "ot": OT
        }

    def update_setting(self, key, value):
        self.settings.update({
            key: value
        })

    def get_setting(self, key):
        return self.settings.get(key)

    def set_start_working_date(self, date_str: str):
        start_working_hour = datetime.strptime(
            date_str + ' {}'.format(working_hour_interval[0][0]),
            '%Y-%m-%d %H:%M'
        )

        self.settings.update({
            'start_working_hour': start_working_hour
        })

    def get_start_working_date(self, date_type: str = 'date'):
        if date_type == 'date':
            return self.settings.get('start_working_hour').strftime('%Y-%m-%d')
        elif date_type == 'timestamp':
            return self.settings.get('start_working_hour').stftime('%Y-%m-%d %H-%M-%D')
        elif date_type == 'datetime':
            return self.settings.get('start_working_hour')
