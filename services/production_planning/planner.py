import platform
from typing import Dict, List
from docplex.cp.model import *
from pandas import DataFrame
from const.weights import WEIGHT_OF_ADJUSTMENT_TIME, WEIGHT_OF_TARDY_JOB
from libs.settings import settings

from services.production_planning.job_duration_calculator import JobDurationCalculator
from libs.utils import resource_path
from libs.loggers import logging


logger = logging.getLogger('planner')


class Planner:
    def __init__(
        self,
        jobs_dict: Dict[int, int],
        machines_dict: Dict[int, int],
        pending_task: DataFrame,
        duration_calculator: JobDurationCalculator,
        due_date_dict: Dict[int, int],
        setup_time_dict: Dict[int, int] = None,
    ):
        logger.info('Start planning ...')

        self.mdl = CpoModel(name='productionPlanning')

        self.jobs = list(jobs_dict.keys())
        self.machines = list(machines_dict.keys())
        self.jobs_dict = jobs_dict
        self.due_date_dict = due_date_dict
        self.machines_dict = machines_dict
        self.pending_task = pending_task
        self.duration_calculator = duration_calculator
        self.setup_time_dict = setup_time_dict
        self.processing_itv_vars = []
        self.__solution_status = False

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

        return processing_itv_vars

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

    def __add_job_must_be_done_constraint(self, processing_itv_vars):
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

    def __add_no_overlap_and_set_up_overhead_constraint(self, processing_itv_vars):
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
                if len(setup_matrix[m]) > 0:
                    self.mdl.add(self.mdl.no_overlap(
                        sequence_vars[m], setup_matrix[m]))
                else:
                    self.mdl.add(self.mdl.no_overlap(
                        sequence_vars[m]))

        else:
            for m in self.machines:
                self.mdl.add(self.mdl.no_overlap(sequence_vars[m]))

        return sequence_vars

    def __add_objective_function(self, sequence_vars: List[expression.CpoSequenceVar]):
        adjustment_time_list = []

        for m in self.machines:
            for var in sequence_vars[m].get_interval_variables():
                start_next = self.mdl.start_of_next(
                    sequence_vars[m], var, lastValue=-1, absentValue=-1)

                binary = self.mdl.binary_var(
                    name=f"binary_adjustment_time{var.name}")
                self.mdl.add(binary == (start_next >= 0))

                adjustment_time = (start_next - self.mdl.end_of(var)) * binary
                adjustment_time.set_name(f"adjustment_time_{var.name}")

                adjustment_time_list.append(adjustment_time)

        adjustment_time_obj = self.mdl.sum(adjustment_time_list)

        n_tardy_day_list = []
        for m in self.machines:
            for j in self.jobs:
                if isinstance(self.processing_itv_vars[j][m], expression.CpoIntervalVar):
                    due_date = self.due_date_dict.get(j)
                    if due_date:
                        if due_date > 0:
                            n_tardy_day_list.append(self.mdl.max(
                                [0, self.mdl.end_of(self.processing_itv_vars[j][m]) - due_date]))

        n_tardy_day_obj = self.mdl.sum(n_tardy_day_list)
        self.mdl.add(self.mdl.minimize(adjustment_time_obj *
                     WEIGHT_OF_ADJUSTMENT_TIME + n_tardy_day_obj * WEIGHT_OF_TARDY_JOB))

    def get_processing_itv_vars(self):
        return self.processing_itv_vars

    def get_solution_status(self):
        return self.__solution_status

    def __update_solution_status(self, status=True):
        self.__solution_status = status

    def __calculate_objective_value(self, overall_objective_value: int, end_time_unit_dict: Dict[int, int]):
        tardy_job_objective_value = (
            self.pending_task.index.map(end_time_unit_dict) - self.pending_task['due_time_unit']
        ).apply(lambda x: x if x > 0 else 0).sum()
        tardy_job_objective_value = tardy_job_objective_value * WEIGHT_OF_TARDY_JOB

        return {
            "tardy_job_objective_value": tardy_job_objective_value,
            "adjustment_time_objective_value": overall_objective_value - tardy_job_objective_value
        }

    def __create_end_time_unit_dict(self, msol):
        end_time_unit_dict = {}
        for m in self.machines:
            for j in self.jobs:
                itv: CpoIntervalVarSolution = msol.get_var_solution(
                    self.processing_itv_vars[j][m])
                if itv:
                    if itv.is_present():
                        end_time_unit_dict.update(
                            {
                                j: itv.get_end()
                            }
                        )

        return end_time_unit_dict

    def generate(self):
        processing_itv_vars = self.__prepare_processing_interval()
        self.processing_itv_vars = processing_itv_vars

        self.__add_job_must_be_done_constraint(processing_itv_vars)
        sequence_var = self.__add_no_overlap_and_set_up_overhead_constraint(
            processing_itv_vars)
        self.__add_objective_function(sequence_var)

        if platform.system() in (['Linux', 'Darwin']):
            # Linux or MAC OS X
            execfile = './cpoptimizer'

        elif platform.system() == 'Windows':
            # Windows
            execfile = './cpoptimizer.exe'

        else:
            raise Exception('Invalid platform')

        msol = self.mdl.solve(
            log_output=True if settings.get_setting(
                "STAGE") == 'dev' else None,
            execfile=resource_path(execfile),
            TimeLimit=settings.get_setting('run_time_limit')
        )

        self.__update_solution_status()
        end_time_unit_dict = self.__create_end_time_unit_dict(msol)

        obj_value_details = self.__calculate_objective_value(
            msol.get_objective_value(), end_time_unit_dict)

        logger.info('Success.')
        logger.info('Objective value is {}'.format(msol.get_objective_value()))
        logger.info('Tardy job objective value: {}'.format(
            obj_value_details['tardy_job_objective_value']))
        logger.info('Adjustment time objective value: {}'.format(
            obj_value_details['adjustment_time_objective_value']))

        return msol
