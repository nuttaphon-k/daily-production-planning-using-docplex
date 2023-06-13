import numpy as np
from pandas import DataFrame
from typing import Union

from const import IRON_DENSITY, TIME_SCALE


class JobDurationCalculator:
    def __init__(self, machine_material: DataFrame, material_master: DataFrame, machine_master: DataFrame) -> None:
        self.machine_material = machine_material
        self.material_master = material_master
        self.machine_master = machine_master.set_index('machine_id')
        self.material_master = material_master.set_index('mat_id')
        self.machine_id = None
        self.mat_id = None
        self.is_compatible = False

    def register(self, machine_id: int, mat_id: int) -> None:
        self.machine_id = machine_id
        self.mat_id = mat_id

        if mat_id in self.machine_material[self.machine_material['machine_id'] == machine_id]['mat_id'].to_list():
            self.is_compatible = True

    def calculate_duration(self, pending_volume: float) -> Union[int, None]:
        if self.is_compatible:
            machine_info = self.machine_master.loc[self.machine_id]
            material_info = self.material_master.loc[self.mat_id]

            if machine_info['machine_weight_hour'] > 0:
                return int(np.ceil(pending_volume / float(machine_info['machine_weight_hour']) * 60 / TIME_SCALE ))

            else:
                machine_spd_mul = float(machine_info['machine_spd_mul'])
                mat_size = float(material_info['mat_size']) / 1000

                production_rate = IRON_DENSITY * machine_spd_mul * \
                    np.pi * pow(mat_size, 2) / 4 * 60 * TIME_SCALE

                return int(np.ceil(pending_volume / production_rate))
        else:
            return None
    
    def calculate_weight(self, time_unit: int) -> Union[float, None]:
        if self.is_compatible:
            machine_info = self.machine_master.loc[self.machine_id]
            material_info = self.material_master.loc[self.mat_id]
            if machine_info['machine_weight_hour'] > 0:
                return time_unit * TIME_SCALE / 60 * float(machine_info['machine_weight_hour'])
            else:
                machine_spd_mul = float(machine_info['machine_spd_mul'])
                mat_size = float(material_info['mat_size']) / 1000

                production_rate = IRON_DENSITY * machine_spd_mul * \
                    np.pi * pow(mat_size, 2) / 4 * 60 * TIME_SCALE

                return time_unit * production_rate
        else:
            return None

    def clear(self) -> None:
        self.machine_id = None
        self.mat_id = None
        self.is_compatible = False
