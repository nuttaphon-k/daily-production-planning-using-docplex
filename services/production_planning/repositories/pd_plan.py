from typing import Dict, List, Any
from libs.db_manager import CustomRepository


class PdPlan(CustomRepository):
    def delete_plan(self, commit=False):
        """
            Delete existing plan in the database.

                Parameters:
                    commit (boolean) (optional): Commit after execute or not
        """
        cur = self.conn.cursor()
        cur.execute(
            """
                DELETE
                FROM pd_plan
            """
        )

        if commit:
            self.conn.commit()

    def insert_plan(self, values: List[Dict[Any, Any]], commit=False):
        """
            Insert production plan into the database.

                Parameters:
                    values (List[Dict[Any,Any]]): List of Dictionaries which contain keys as the following
                        so_id (int): sale order id
                        mat_id (int): material id
                        res_volume (float): residual volume
                        start_timestamp (str): start timestamp of plan period
                        end_timestamp (str): end timestamp of plan period
                        machine_id (int): machine id
                    commit (boolean) (optional): Commit after execute or not
        """

        cur = self.conn.cursor()
        cur.executemany(
            """
                INSERT INTO pd_plan (so_id, mat_id, res_volume, start_timestamp, end_timestamp, machine_id, pd_plan_pub_date, batch_volume, remaining_volume)
                VALUES (%(so_id)s, %(mat_id)s, %(res_volume)s, %(start_timestamp)s, %(end_timestamp)s, %(machine_id)s, NOW(), %(batch_volume)s, %(remaining_volume)s)
            """,
            values
        )

        if commit:
            self.conn.commit()
