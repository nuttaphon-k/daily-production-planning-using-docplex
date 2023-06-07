import json
import os
import sys
import time
import traceback
import argparse
from datetime import datetime

from libs import DbConnection
from libs.utils import is_date_format, resource_path
from services.production_planning import ProductionPlanning
from libs.settings import settings
from libs.loggers import logging


parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true")
args = parser.parse_args()


if args.debug:
    settings.update_setting('STAGE', 'dev')

logging.init()
logger = logging.getLogger('main')

if settings.get_setting('STAGE') == 'dev':
    logger.debug("Run program with debug mode")


def main():
    db_connection = DbConnection()

    try:
        logger.info('Connect to the database ...')
        with open(resource_path("./dbconfig.json"), 'r') as jsonfile:
            config = json.load(jsonfile)
        db_connection.connect(
            config=config
        )

    except Exception as e:
        logger.debug(e)
        logger.debug(traceback.format_exc())
        logger.error("Connect database error")

        return

    if db_connection.get_connector():
        logger.info('The connection to the database was successful.')
        logger.info('------------------------------------------------')
        logger.info('Start production planning')
        logger.info("Default start date: {}".format(
            settings.get_start_working_date()))
        
        change_start_date_complete = False

        while not change_start_date_complete:
            change_start_date = input(
                ">>>Do you want to change start date (Y/n): ")

            if change_start_date == 'Y':
                is_change_start_date_finish = False
                is_time_format_wrong = False
                while not is_change_start_date_finish:
                    if is_time_format_wrong:
                        new_start_date = input(
                            ">>>please enter date in format YYYY-MM-DD: ")
                    else:
                        new_start_date = input(
                            ">>>enter start date (YYYY-MM-DD): ")

                    try:
                        settings.set_start_working_date(
                            date_str=new_start_date
                        )

                        is_change_start_date_finish = True
                    except Exception as e:
                        logger.debug(e)
                        logger.debug(traceback.format_exc())
                        logger.info('Wrong date format')
                        is_time_format_wrong = True

                logger.info("Setting new start date: {}".format(
                    settings.get_start_working_date()))
                time.sleep(1)
                change_start_date_complete = True
            elif change_start_date == 'n':
                change_start_date_complete = True
            else:
                logger.error("Please enter a valid answer.")

        logger.info('------------------------------------------------')

        add_holiday_complete = False

        while not add_holiday_complete:
            is_holiday = input(">>>Do you have a holiday in next two weeks (Y/n): ")
            if is_holiday == 'Y':
                is_holiday_finish = False
                is_holiday_format_wrong = False
                while not is_holiday_finish:
                    if is_holiday_format_wrong:
                        new_holiday = input(
                            ">>>Please enter holiday in format (YYYY-MM-DD,YYYY-MM-DD): ")
                    else:
                        new_holiday = input(
                            ">>>enter holiday in format (YYYY-MM-DD,YYYY-MM-DD): ")

                    try:
                        holidays = new_holiday.split(',')
                        holidays = [x.strip() for x in holidays]

                        for h in holidays:
                            if not is_date_format(h):
                                raise Exception('Incorrect date format')

                        old_holidays = settings.get_setting('holiday')
                        old_holidays.extend(holidays)

                        settings.update_setting(
                            key='holiday',
                            value=old_holidays
                        )

                        is_holiday_finish = True
                    except Exception as e:
                        logger.debug(e)
                        logger.debug(traceback.format_exc())
                        logger.info('Wrong date format')
                        is_holiday_format_wrong = True

                logger.info("The holidays are: {}".format(
                    ', '.join(settings.get_setting('holiday'))))
                time.sleep(1)
                add_holiday_complete = True
            elif is_holiday == 'n':
                add_holiday_complete = True
            else:
                logger.error("Please enter a valid answer.")

        logger.info('------------------------------------------------')

        config_ot_complete = False
        while not config_ot_complete:
            is_OT = input(">>>Do you want to plan with OT (Y/n): ")
            if is_OT == 'Y':
                settings.update_setting(
                    key='ot',
                    value=True
                )

                logger.info("The working hours are include OT.")
                time.sleep(1)
                config_ot_complete=True
            elif is_OT == 'n':
                config_ot_complete = True
            else:
                logger.error("Please enter a valid answer.")

        try:
            conn = db_connection.get_connector()

            production_planning = ProductionPlanning(
                conn=conn
            )

            production_planning.generate_production_plan()
        except Exception as e:
            logger.debug(e)
            logger.debug(traceback.format_exc())
            logger.info('------------------------------------------------')
            logger.error("Generate production plan was error")
            logger.error("Exit the program with error")

    else:
        logger.error("Database connection not found")
        logger.error("Exit the program with error")


if __name__ == "__main__":
    try:
        main()
        input(">>>Press enter to exit the program ...")
    except KeyboardInterrupt:
        print("The program was iterrupted.")
        print("Close program.")
    
    sys.exit(0)
