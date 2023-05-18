from libs.db_manager import CustomRepository

class MachineMaterial(CustomRepository):
    def get_machine_material(self):
        cur = self.conn.cursor()
        cur.execute(
            """
                SELECT *
                FROM machine_material
            """
        )

        return self.fetch_list_of_dict(cur)
