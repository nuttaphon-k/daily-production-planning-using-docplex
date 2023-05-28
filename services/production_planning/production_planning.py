import pandas as pd
import numpy as np
from mariadb import Connection
from typing import Dict

from const import MACHINE_GROUP, TIME_SCALE
from services.production_planning.job_duration_calculator import JobDurationCalculator
from services.production_planning.planner import Planner
from services.production_planning.repositories import ProductionPlanningRepository
from services.production_planning.scheduler import Scheduler


class ProductionPlanning:
    def __init__(self, conn: Connection):
        self.repository = ProductionPlanningRepository(conn=conn)

    def __retreive_master_data(self):
        machine_master = pd.DataFrame(
            self.repository.machine.get_machine_master())
        machine_material = pd.DataFrame(
            self.repository.machine_material.get_machine_material())
        material_master = pd.DataFrame(
            self.repository.materials.get_material_material())

        return machine_master, machine_material, material_master

    def __filter_pending_job(self, pending_job, machine_material):
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

    def generate_production_plan(self):
        machine_master, machine_material, material_master = self.__retreive_master_data()

        pending_job = pd.DataFrame(self.repository.so_item.get_pending_job())
        pending_job = self.__filter_pending_job(pending_job, machine_material)

        duration_calculator = JobDurationCalculator(
            machine_master=machine_master,
            machine_material=machine_material,
            material_master=material_master
        )

        for machines_type_list in MACHINE_GROUP:
            print("Select machine type: " +
                  ', '.join([str(x) for x in machines_type_list]))
            relavant_machine_list = machine_master[machine_master['machine_type_id'].isin(
                machines_type_list)]['machine_id'].tolist()
            relevant_mat_id = machine_material[machine_material['machine_id'].isin(
                relavant_machine_list)]['mat_id'].tolist()

            selected_pending_job = pending_job[pending_job['mat_id'].isin(
                relevant_mat_id)]
            selected_pending_job = selected_pending_job.reset_index(drop=True)

            n_manchine = len(relavant_machine_list)
            n_jobs = len(selected_pending_job)

            print("Number of machines: {}".format(n_manchine))
            print("Number of jobs: {}".format(n_jobs))

            jobs_dict: Dict[int, int] = dict(
                zip(range(0, n_jobs), selected_pending_job.index))
            machines_dict: Dict[int, int] = dict(
                zip(range(0, n_manchine), relavant_machine_list))

            setup_time_dict = self.__create_setup_time_dict(
                machines_dict=machines_dict,
                machine_master=machine_master
            )

            planner = Planner(
                jobs_dict=jobs_dict,
                machines_dict=machines_dict,
                pending_task=selected_pending_job,
                duration_calculator=duration_calculator,
                setup_time_dict=setup_time_dict
            )

            try:
                solution = planner.generate()

                processing_itv_vars = planner.get_processing_itv_vars()

            except BaseException as e:
                print(e)

            if planner.get_solution_status():
                try:
                    scheduler = Scheduler(
                        solution=solution,
                        jobs_dict=jobs_dict,
                        machines_dict=machines_dict,
                        processing_itv_vars=processing_itv_vars
                    )

                    schdule_df = scheduler.main(
                        selected_pending_job=selected_pending_job
                    )

                except BaseException as e:
                    print(e)