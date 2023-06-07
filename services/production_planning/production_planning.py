import pandas as pd
import numpy as np
from mariadb import Connection
from typing import Dict
from datetime import timedelta
import traceback

from const import MACHINE_GROUP, TIME_SCALE
from const.working_hour import working_hour_interval, overtime_hour_interval
from libs.settings import settings
from libs.utils import create_time_for_comparison
from libs.loggers import logging
from services.production_planning.job_duration_calculator import JobDurationCalculator
from services.production_planning.planner import Planner
from services.production_planning.repositories import ProductionPlanningRepository
from services.production_planning.scheduler import Scheduler


logger = logging.getLogger('production_planning')

class ProductionPlanning:
    def __init__(self, conn: Connection):
        self.repository = ProductionPlanningRepository(conn=conn)
        self.non_processed_job = []
        self.objective_value = 0
        if settings.get_setting('ot'):
            self.working_hour_interval = working_hour_interval + overtime_hour_interval
        else:
            self.working_hour_interval = working_hour_interval

    def __retreive_master_data(self):
        machine_master = pd.DataFrame(
            self.repository.machine.get_machine_master())
        machine_material = pd.DataFrame(
            self.repository.machine_material.get_machine_material())
        material_master = pd.DataFrame(
            self.repository.materials.get_material_material())

        return machine_master, machine_material, material_master

    def __filter_pending_job(self, pending_job, machine_material):
        self.non_processed_job.extend(
            pending_job['so_id'].tolist()
        )
        # Filter negative res_draft_volume value
        pending_job = pending_job[pending_job['res_draft_volume'] > 0]
        pending_job = pending_job.reset_index(drop=True)

        # Filter too small volume
        pending_job = pending_job[(
            pending_job['res_draft_volume']/pending_job['sale_volume']) > 0.03]
        pending_job = pending_job.reset_index(drop=True)

        # Filter materials that do not be included in machine_material data
        pending_job = pending_job[pending_job['mat_id'].isin(
            machine_material['mat_id'].tolist())]
        pending_job = pending_job.reset_index(drop=True)

        for so_id in pending_job['so_id'].tolist():
            if so_id in self.non_processed_job:
                self.non_processed_job.remove(so_id)

        return pending_job

    def __create_setup_time_dict(self, machines_dict: Dict[int, int], machine_master: pd.DataFrame):
        relevant_machine_id_list = machines_dict.values()
        select_machine_df = machine_master[machine_master['machine_id'].isin(
            relevant_machine_id_list)]
        select_machine_df = select_machine_df.reset_index(drop=True)

        # Change time scale from 15 min to 1 unit using TIME_SCALE variable
        select_machine_df['machine_change_time'] = np.ceil(
            select_machine_df['machine_change_time']/TIME_SCALE)
        select_machine_df['machine_change_time'] = select_machine_df['machine_change_time'].astype(
            int)

        return dict(zip(machines_dict.keys(), select_machine_df['machine_change_time'].tolist()))

    def __insert_production_plan(self, schedule_df: pd.DataFrame):
        schedule_values = schedule_df.to_dict('records')

        def insert_plan():
            self.repository.pd_plan.delete_plan()
            self.repository.pd_plan.insert_plan(
                values=schedule_values
            )

        self.repository.run_in_transaction(
            task=insert_plan
        )

    def __create_due_date_time_unit(self, pending_job):
        pending_job['deadline_date'] = pending_job['so_pub_date'] + \
            timedelta(days=14)
        time_unit_per_day = 0

        for working_hour in self.working_hour_interval:
            start, end = working_hour
            diff = create_time_for_comparison(
                end) - create_time_for_comparison(start)
            diff_seconds = diff.seconds
            time_unit = diff_seconds / 60 / TIME_SCALE
            time_unit = int(np.ceil(time_unit))
            time_unit_per_day = time_unit_per_day + time_unit

        pending_job['due_date'] = (
            pending_job['deadline_date'] - settings.get_start_working_date(date_type="datetime") + timedelta(days=1)).dt.days
        pending_job['due_time_unit'] = pending_job['due_date'].apply(
            lambda x: x * time_unit_per_day if x > 0 else None)

        return pending_job

    def generate_production_plan(self):
        machine_master, machine_material, material_master = self.__retreive_master_data()

        pending_job = pd.DataFrame(self.repository.so_item.get_pending_job())
        logger.info("Number of total jobs: {}.".format(len(pending_job)))
        pending_job = self.__filter_pending_job(pending_job, machine_material)
        logger.info(
            "Number of total jobs after filtering: {}.".format(len(pending_job)))

        duration_calculator = JobDurationCalculator(
            machine_master=machine_master,
            machine_material=machine_material,
            material_master=material_master
        )

        all_schedule_df = pd.DataFrame()

        logger.info('------------------------------------------------')

        for machines_type_list in MACHINE_GROUP:
            logger.info("Select machine type: {}.".format(
                ', '.join([str(x) for x in machines_type_list])))
            relavant_machine_list = machine_master[machine_master['machine_type_id'].isin(
                machines_type_list)]['machine_id'].tolist()
            relevant_mat_id = machine_material[machine_material['machine_id'].isin(
                relavant_machine_list)]['mat_id'].tolist()

            selected_pending_job = pending_job[pending_job['mat_id'].isin(
                relevant_mat_id)]
            selected_pending_job = selected_pending_job.reset_index(drop=True)
            selected_pending_job = self.__create_due_date_time_unit(
                pending_job=selected_pending_job)

            n_manchine = len(relavant_machine_list)
            n_jobs = len(selected_pending_job)

            logger.info("Number of machines: {}.".format(n_manchine))
            logger.info("Number of jobs: {}.".format(n_jobs))

            jobs_dict: Dict[int, int] = dict(
                zip(range(0, n_jobs), selected_pending_job.index))
            machines_dict: Dict[int, int] = dict(
                zip(range(0, n_manchine), relavant_machine_list))
            due_date_dict: Dict[int, int] = dict(
                zip(range(0, n_jobs), selected_pending_job['due_time_unit'])
            )

            setup_time_dict = self.__create_setup_time_dict(
                machines_dict=machines_dict,
                machine_master=machine_master
            )

            planner = Planner(
                jobs_dict=jobs_dict,
                machines_dict=machines_dict,
                pending_task=selected_pending_job,
                duration_calculator=duration_calculator,
                due_date_dict=due_date_dict,
                setup_time_dict=setup_time_dict
            )

            try:
                solution = planner.generate()

                self.objective_value = self.objective_value + solution.get_objective_value()

                processing_itv_vars = planner.get_processing_itv_vars()

            except Exception as e:
                logger.debug(e)
                logger.debug(traceback.format_exc())
                logger.error('Plan for machine type: {} failed.'.format(
                    [str(x) for x in machines_type_list]))
                self.non_processed_job.extend(
                    selected_pending_job['so_id'].tolist())

                continue

            if planner.get_solution_status():
                try:
                    scheduler = Scheduler(
                        solution=solution,
                        jobs_dict=jobs_dict,
                        machines_dict=machines_dict,
                        processing_itv_vars=processing_itv_vars,
                        work_date=settings.get_start_working_date(
                            date_type="datetime")
                    )

                    schdule_df = scheduler.main(
                        selected_pending_job=selected_pending_job
                    )

                    all_schedule_df = pd.concat(
                        [all_schedule_df, schdule_df], sort=False, axis=0, ignore_index=True)

                except Exception as e:
                    logger.debug(e)
                    logger.debug(traceback.format_exc())
                    logger.error('Create schedule for machine type: {} failed.'.format(
                        [str(x) for x in machines_type_list]))
                    self.non_processed_job.extend(
                        selected_pending_job['so_id'].tolist())

                    continue
            
            logger.info('------------------------------------------------')

        if len(all_schedule_df) > 0:
            try:
                logger.info("Scheduling succeeded.")
                logger.info("Insert schedule to the database ...")
                self.__insert_production_plan(
                    schedule_df=all_schedule_df
                )
                logger.info("Success.")
                logger.info("The overall objective value is {}".format(self.objective_value))
                logger.info("The so_id that are not processed in this planning are {}".format(
                    ', '.join([str(x) for x in sorted(self.non_processed_job)])))
            except Exception as e:
                logger.debug(e)
                logger.debug(traceback.format_exc())
                logger.error("Failed.")

                raise Exception("Insert schudle to the database failed.")
        else:
            logger.error("All planning failed.")

            raise Exception("All planning failed.")
