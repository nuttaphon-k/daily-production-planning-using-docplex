from mariadb import Connection

from libs.db_manager import Repository
from services.production_planning.repositories.machine import Machine
from services.production_planning.repositories.machine_material import MachineMaterial
from services.production_planning.repositories.materials import Materials
from services.production_planning.repositories.pd_plan import PdPlan
from services.production_planning.repositories.so_item import SoItem


class ProductionPlanningRepository(Repository):
    def __init__(self, conn: Connection):
        super().__init__(conn=conn)

        self.machine_material = MachineMaterial(conn=conn)
        self.machine = Machine(conn=conn)
        self.materials = Materials(conn=conn)
        self.so_item = SoItem(conn=conn)
        self.pd_plan = PdPlan(conn=conn)
