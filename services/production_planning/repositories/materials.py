from libs.db_manager import CustomRepository


class Materials(CustomRepository):
    def get_material_material(self):
        cur = self.conn.cursor()
        cur.execute(
            """
                SELECT *
                FROM materials
            """
        )

        return self.fetch_list_of_dict(cur)
