from libs.db_manager import CustomRepository

class Machine(CustomRepository):
    def get_machine_master(self):
        cur = self.conn.cursor()
        cur.execute(
            """
                SELECT *
                FROM machine
            """
        )

        return self.fetch_list_of_dict(cur)
