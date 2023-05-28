import json

from libs import DbConnection
from libs.utils import resource_path
from services.production_planning import ProductionPlanning


if __name__ == "__main__":
    with open(resource_path("./dbconfig.json"), 'r') as jsonfile:
        config = json.load(jsonfile)

    db_connection = DbConnection(
        config=config
    )

    conn = db_connection.get_connector()

    production_planning = ProductionPlanning(
        conn=conn
    )

    production_planning.generate_production_plan()
