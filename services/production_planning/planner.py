from typing import Dict
from docplex.cp.model import *
from pandas import DataFrame

from services.production_planning.job_duration_calculator import JobDurationCalculator
from libs.utils import resource_path


class Planner:
    def __init__(
        self,
        jobs_dict: Dict[int, int],
        machines_dict: Dict[int, int],
        pending_task: DataFrame,
        duration_calculator: JobDurationCalculator,
        setup_time_dict: Dict[int, int] = None,
    ):
        self.mdl = CpoModel(name='productionPlanning')

        self.jobs = list(jobs_dict.keys())
        self.machines = list(machines_dict.keys())
        self.jobs_dict = jobs_dict
        self.machines_dict = machines_dict
        self.pending_task = pending_task
        self.duration_calculator = duration_calculator
        self.setup_time_dict = setup_time_dict
        self.processing_itv_vars = []

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

    def __create_setup_matrix(self, processing_itv_vars):
        setup_matrix = [*range(0, len(self.machines))]
        for m in self.machines:
            setup_time = self.setup_time_dict.get(m)
            temp1 = []
            for j1 in self.jobs:
                temp2 = []
                for j2 in self.jobs:
                    if (isinstance(processing_itv_vars[j1][m], expression.CpoIntervalVar) & isinstance(processing_itv_vars[j2][m], expression.CpoIntervalVar)):
                        if self.pending_task.loc[self.jobs_dict.get(j1)]['mat_id'] == self.pending_task.loc[self.jobs_dict.get(j2)]['mat_id']:
                            temp2.append(0)
                        else:
                            temp2.append(setup_time)
                if len(temp2) > 0:
                    temp1.append(temp2)
            setup_matrix[m] = temp1

        return setup_matrix

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
                name="sequences_machine{}".format(m))
            for m in self.machines
        ]

        if self.setup_time_dict:
            setup_matrix = self.__create_setup_matrix(processing_itv_vars)

            for m in self.machines:
                self.mdl.add(self.mdl.no_overlap(
                    sequence_vars[m], setup_matrix[m]))

        else:
            for m in self.machines:
                self.mdl.add(self.mdl.no_overlap(sequence_vars[m]))

    def __add_objective_function(self, non_none_processing_itv_vars_list):
        objective = self.mdl.max(
            [self.mdl.end_of(var) for var in non_none_processing_itv_vars_list]
        )

        self.mdl.add(self.mdl.minimize(objective))

    def get_processing_itv_vars(self):
        return self.processing_itv_vars

    def generate(self):
        processing_itv_vars, non_none_processing_itv_vars_list = self.__prepare_processing_interval()
        self.processing_itv_vars = processing_itv_vars

        self.__add_jon_must_be_done_constraint(processing_itv_vars)
        self.__add_no_overlab_and_set_up_overhead_constraint(
            processing_itv_vars)
        self.__add_objective_function(non_none_processing_itv_vars_list)

        msol = self.mdl.solve(
            log_output=True,
            execfile=resource_path('./cpoptimizer'),
            TimeLimit=120
        )

        return msol
