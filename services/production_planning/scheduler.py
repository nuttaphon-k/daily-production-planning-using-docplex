from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from docplex.cp.solution import CpoSolveResult, CpoIntervalVar, CpoIntervalVarSolution

from const import TIME_SCALE
from const.working_hour import working_hour_interval


current_timestamp = datetime.now()


class Scheduler:
    def __init__(
        self,
        solution: CpoSolveResult,
        jobs_dict: Dict[int, int],
        machines_dict: Dict[int, int],
        processing_itv_vars: List[List[CpoIntervalVar]],
    ):
        self.msol = solution
        self.jobs = list(jobs_dict.keys())
        self.machines = list(machines_dict.keys())
        self.machines_dict = machines_dict
        self.processing_itv_vars = processing_itv_vars

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
        work_date = datetime.strptime('{} {}'.format(current_timestamp.strftime(
            '%Y-%m-%d'), '00:00:00'), '%Y-%m-%d %H:%M:%S') + timedelta(days=1)
        processed_job = 0

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
            for working_hour in working_hour_interval:
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

            work_date = work_date + timedelta(days=1)
        return time_table

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
        selected_pending_job = selected_pending_job[['so_id', 'mat_id', 'res_draft_volume', 'start_timestamp', 'end_timestamp', 'machine_id']]
        selected_pending_job = selected_pending_job.rename(columns={'res_draft_volume': 'res_volume'})
        selected_pending_job['start_timestamp'] = selected_pending_job['start_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        selected_pending_job['end_timestamp'] = selected_pending_job['end_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

        return selected_pending_job
