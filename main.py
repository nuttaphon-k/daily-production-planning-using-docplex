import json

from libs import DbConnection
from libs.utils import resource_path
from services.production_planning import ProductionPlanning


if __name__ == "__main__":
    db_connection = DbConnection()
    try:
        with open(resource_path("./dbconfig.json"), 'r') as jsonfile:
            config = json.load(jsonfile)
        db_connection.connect(
            config=config
        )
    except Exception as e:
        print(e)
        print("Connect database error")

    if db_connection.get_connector():
        try:
            conn = db_connection.get_connector()

            production_planning = ProductionPlanning(
                conn=conn
            )

            production_planning.generate_production_plan()
        except Exception as e:
            print(e)
            print("Generate plan error")
    else:
        print("Databse connection not found")

    input("Close...")
