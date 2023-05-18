from typing import Dict
from docplex.cp.model import *
from pandas import DataFrame

from services.production_planning.job_duration_calculator import JobDurationCalculator


class Planner:
    def __init__(
        self,
        jobs_dict: Dict[int, int],
        machines_dict: Dict[int, int],
        pending_task: DataFrame,
        duration_calculator: JobDurationCalculator
    ):
        self.mdl = CpoModel(name='productionPlanning')

        self.jobs = list(jobs_dict.keys())
        self.machines = list(machines_dict.keys())
        self.jobs_dict = jobs_dict
        self.machines_dict = machines_dict
        self.pending_task = pending_task
        self.duration_calculator = duration_calculator

    def __prepare_processing_interval(self):
        processing_itv_vars = []

        for j in self.jobs:
            processing_itv_job_vars = []
            for m in self.machines:
                job_id = self.jobs_dict.get(j)
                mat_id = self.pending_task.loc[job_id]['mat_id']
                pending_volume = float(
                    self.pending_task.loc[job_id]['res_draft_volume'])
                machine = self.machines_dict.get(m)

                self.duration_calculator.register(
                    machine_id=machine,
                    mat_id=mat_id
                )

                duration = self.duration_calculator.calculate_duration(
                    pending_volume=pending_volume
                )

                self.duration_calculator.clear()

                if duration:
                    int_var = self.mdl.interval_var(
                        optional=True, size=duration, name="interval_job{}_machine{}".format(j, m))

                    processing_itv_job_vars.append(
                        int_var
                    )

                else:
                    processing_itv_job_vars.append(
                        None
                    )

            processing_itv_vars.append(processing_itv_job_vars)

        non_none_processing_itv_vars_list = []

        for m in self.machines:
            for j in self.jobs:
                if isinstance(processing_itv_vars[j][m], expression.CpoIntervalVar):
                    non_none_processing_itv_vars_list.append(
                        processing_itv_vars[j][m])

        return processing_itv_vars, non_none_processing_itv_vars_list

    def __add_jon_must_be_done_constraint(self, processing_itv_vars):
        for j in self.jobs:
            processing_itv_vars_at_j = processing_itv_vars[j]
            non_none_processing_itv_vars_at_j = []

            for m in self.machines:
                if isinstance(processing_itv_vars_at_j[m], expression.CpoIntervalVar):
                    non_none_processing_itv_vars_at_j.append(
                        processing_itv_vars_at_j[m])

            self.mdl.add(
                self.mdl.sum(
                    [self.mdl.presence_of(var)
                     for var in non_none_processing_itv_vars_at_j]
                ) == 1
            )

    def __add_no_overlab_and_set_up_overhead_constraint(self, processing_itv_vars):
        sequence_vars = [
            self.mdl.sequence_var(
                [processing_itv_vars[j][m] for j in self.jobs if isinstance(
                    processing_itv_vars[j][m], expression.CpoIntervalVar)],
                types=[j for j in self.jobs if isinstance(
                    processing_itv_vars[j][m], expression.CpoIntervalVar)],
                name="sequences_machine{}".format(m))
            for m in self.machines
        ]

        for m in self.machines:
            self.mdl.add(self.mdl.no_overlap(sequence_vars[m]))

    def __add_objective_function(self, non_none_processing_itv_vars_list):
        objective = self.mdl.max(
            [self.mdl.end_of(var) for var in non_none_processing_itv_vars_list]
        )

        self.mdl.add(self.mdl.minimize(objective)) 

    def generate(self):
        processing_itv_vars, non_none_processing_itv_vars_list = self.__prepare_processing_interval()
        self.__add_jon_must_be_done_constraint(processing_itv_vars)
        self.__add_no_overlab_and_set_up_overhead_constraint(processing_itv_vars)
        self.__add_objective_function(non_none_processing_itv_vars_list)

        msol = self.mdl.solve(
            log_output=True,
            execfile='/Applications/CPLEX_Studio_Community2211/cpoptimizer/bin/arm64_osx/cpoptimizer',
            TimeLimit=120
        )
        
        return msol
