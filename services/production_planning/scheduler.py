from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from docplex.cp.solution import CpoSolveResult, CpoIntervalVar, CpoIntervalVarSolution

from const import TIME_SCALE
from const.working_hour import working_hour_interval, overtime_hour_interval
from libs.loggers import logging
from libs.settings import settings
from services.production_planning.job_duration_calculator import JobDurationCalculator


logger = logging.getLogger('scheduler')

class Scheduler:
    def __init__(
        self,
        solution: CpoSolveResult,
        jobs_dict: Dict[int, int],
        machines_dict: Dict[int, int],
        processing_itv_vars: List[List[CpoIntervalVar]],
        duration_calculator: JobDurationCalculator,
        work_date: datetime
    ):
        logger.info('Start scheduling ...')
        self.msol = solution
        self.jobs = list(jobs_dict.keys())
        self.machines = list(machines_dict.keys())
        self.machines_dict = machines_dict
        self.processing_itv_vars = processing_itv_vars
        self.work_date = work_date
        self.duration_calculator = duration_calculator
        if settings.get_setting('ot'):
            self.working_hour_interval = working_hour_interval + overtime_hour_interval
        else:
            self.working_hour_interval = working_hour_interval

    def __create_solution_dataframe(self):
        solutions = []
        for m in self.machines:
            for j in self.jobs:
                itv: CpoIntervalVarSolution = self.msol.get_var_solution(
                    self.processing_itv_vars[j][m])
                if itv:
                    if itv.is_present():
                        solutions.append(
                            {
                                "machine_id": m,
                                "job_id": j,
                                "start": itv.get_start(),
                                "end": itv.get_end()
                            }
                        )
        solutions_df = pd.DataFrame(solutions)

        return solutions_df

    def __create_time_for_comparison(self, time: str):
        (hour, min) = time.split(':')
        return datetime(year=2022, month=1, day=1, hour=int(hour), minute=int(min))

    def __create_job_time_interval(self, df: pd.DataFrame):
        time_table = []
        processed_job = 0

        work_date = self.work_date

        df['working_minutes'] = ((df['end'] - df['start'])
                                 * TIME_SCALE).astype(int)
        df['remaining_minutes'] = df['working_minutes']

        setup_time = []
        for i in range(len(df)):
            if i > 0:
                setup_time.append(
                    (df.iloc[i]['start'] - df.iloc[i-1]['end']) * TIME_SCALE)
            else:
                setup_time.append(np.nan)

        df['setup_time'] = setup_time
        df['remaining_setup_time'] = df['setup_time']

        while processed_job < len(df):
            for working_hour in self.working_hour_interval:
                use_default_start_time = True
                start_working_hour, end_working_hour = working_hour
                start_working_hour_dt = self.__create_time_for_comparison(
                    start_working_hour)
                end_working_hour_dt = self.__create_time_for_comparison(
                    end_working_hour)

                for idx in df[processed_job:].index:
                    remaining_minutes = df.loc[idx, 'remaining_minutes']

                    if use_default_start_time:
                        start_time = work_date.replace(
                            minute=start_working_hour_dt.minute,
                            hour=start_working_hour_dt.hour
                        )
                    else:
                        start_time: datetime = time_table[-1]['end_timestamp']

                    if not pd.isna(df.loc[idx, 'remaining_setup_time']):
                        if df.loc[idx, 'remaining_setup_time'] > 0:
                            start_time_plus_setup_time = start_time + \
                                timedelta(minutes=int(
                                    df.loc[idx, 'remaining_setup_time']))

                            if start_time_plus_setup_time > start_time.replace(hour=end_working_hour_dt.hour, minute=end_working_hour_dt.minute):
                                time_table.append({
                                    "start_timestamp": start_time,
                                    "end_timestamp": start_time.replace(hour=end_working_hour_dt.hour, minute=end_working_hour_dt.minute),
                                    "job_id": -1
                                })

                                df.loc[idx, 'remaining_setup_time'] = df.loc[idx, 'remaining_setup_time'] - int(np.ceil((
                                    start_time_plus_setup_time - start_time.replace(hour=end_working_hour_dt.hour, minute=end_working_hour_dt.minute)).seconds / 60))

                                use_default_start_time = True

                                break
                            else:
                                start_time = start_time_plus_setup_time
                                df.loc[idx, 'remaining_setup_time'] = 0

                    working_slot_minute = int(
                        np.ceil(((start_time.replace(hour=end_working_hour_dt.hour, minute=end_working_hour_dt.minute) - start_time).seconds) / 60))

                    if remaining_minutes > working_slot_minute:
                        time_table.append({
                            "start_timestamp": start_time,
                            "end_timestamp": start_time.replace(hour=end_working_hour_dt.hour, minute=end_working_hour_dt.minute),
                            "job_id": df.loc[idx, 'job_id']
                        })

                        df.loc[idx, 'remaining_minutes'] = df.loc[idx,
                                                                  'remaining_minutes'] - working_slot_minute

                        use_default_start_time = True

                        break
                    elif remaining_minutes == working_slot_minute:
                        time_table.append({
                            "start_timestamp": start_time,
                            "end_timestamp": start_time.replace(hour=end_working_hour_dt.hour, minute=end_working_hour_dt.minute),
                            "job_id": df.loc[idx, 'job_id']
                        })

                        df.loc[idx, 'remaining_minutes'] = df.loc[idx,
                                                                  'remaining_minutes'] - working_slot_minute

                        use_default_start_time = True

                        processed_job = processed_job + 1

                        break
                    else:
                        time_table.append({
                            "start_timestamp": start_time,
                            "end_timestamp": start_time + timedelta(minutes=int(remaining_minutes)),
                            "job_id": df.loc[idx, 'job_id']
                        })

                        df.loc[idx, 'remaining_minutes'] = df.loc[idx,
                                                                  'remaining_minutes'] - remaining_minutes

                        use_default_start_time = False

                        processed_job = processed_job + 1

            is_new_work_date_correct = False
            while not is_new_work_date_correct:
                work_date = work_date + timedelta(days=1)
                if work_date.strftime('%Y-%m-%d') not in settings.get_setting('holiday'):
                    is_new_work_date_correct = True

        return time_table
    
    def __calculate_weight(self, data: pd.Series):
        self.duration_calculator.register(
            machine_id=data['machine_id'],
            mat_id=data['mat_id']
        )

        working_time_unit = int((data['end_timestamp'] - data['start_timestamp']).seconds / 60 / TIME_SCALE)

        weight = self.duration_calculator.calculate_weight(
            time_unit=working_time_unit
        )

        self.duration_calculator.clear()

        return weight

    def main(self, selected_pending_job: pd.DataFrame):
        solutions_df = self.__create_solution_dataframe()

        selected_pending_job.index.name = 'job_id'
        selected_pending_job = selected_pending_job.reset_index(drop=False)

        selected_pending_job = selected_pending_job
        selected_pending_job = selected_pending_job.merge(
            solutions_df, how='left', on='job_id')
        selected_pending_job = selected_pending_job.sort_values(
            ['machine_id', 'start'])
        selected_pending_job = selected_pending_job.reset_index(drop=True)

        machine_timetable = selected_pending_job.groupby(
            'machine_id').apply(self.__create_job_time_interval)
        machine_timetable_list = []
        for machine_id in machine_timetable.index:
            temp = pd.DataFrame(machine_timetable.loc[machine_id])
            temp['machine_id'] = machine_id

            machine_timetable_list.append(temp)

        machine_timetable_df = pd.concat(
            machine_timetable_list, ignore_index=True, sort=False)
        machine_timetable_df = machine_timetable_df[machine_timetable_df['job_id'] != '-1']
        machine_timetable_df = machine_timetable_df.reset_index(drop=True)
        selected_pending_job = selected_pending_job.merge(machine_timetable_df[[
                                                          'job_id', 'start_timestamp', 'end_timestamp']], how='left', on='job_id')
        selected_pending_job['machine_id'] = selected_pending_job['machine_id'].map(self.machines_dict)

        weight_list = selected_pending_job.apply(lambda x: self.__calculate_weight(x), axis=1).tolist()
        selected_pending_job['batch_volume'] = weight_list

        selected_pending_job = selected_pending_job[['so_id', 'mat_id', 'res_draft_volume', 'batch_volume', 'start_timestamp', 'end_timestamp', 'machine_id']]
        selected_pending_job = selected_pending_job.rename(columns={'res_draft_volume': 'res_volume'})
        selected_pending_job['start_timestamp'] = selected_pending_job['start_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        selected_pending_job['end_timestamp'] = selected_pending_job['end_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        selected_pending_job['res_volume'] = selected_pending_job['res_volume'].astype(float)
        
        remaining_volume_list = [selected_pending_job.iloc[0]['res_volume'] - selected_pending_job.iloc[0]['batch_volume']]
        last_remaining_weight = remaining_volume_list[0]
        for i in range(1, len(selected_pending_job)):
            last_so_id = selected_pending_job.iloc[i-1]['so_id']
            last_mat_id = selected_pending_job.iloc[i-1]['mat_id']

            current_so_id = selected_pending_job.iloc[i]['so_id']
            current_mat_id = selected_pending_job.iloc[i]['mat_id']

            if (last_so_id == current_so_id) & (last_mat_id == current_mat_id):
                remaining_volume = last_remaining_weight - selected_pending_job.iloc[i]['batch_volume']
            else:
                remaining_volume = selected_pending_job.iloc[i]['res_volume'] - selected_pending_job.iloc[i]['batch_volume']
            
            remaining_volume_list.append(
                    remaining_volume
                )
            last_remaining_weight = remaining_volume

        selected_pending_job['remaining_volume'] = remaining_volume_list
        selected_pending_job['remaining_volume'] = selected_pending_job['remaining_volume'].round(2)

        logger.info("Success.")

        return selected_pending_job
    
