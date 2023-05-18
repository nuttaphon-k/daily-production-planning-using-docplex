from libs.db_manager import CustomRepository


class SoItem(CustomRepository):
    def get_pending_job(self):
        cur = self.conn.cursor()
        cur.execute(
            """
                SELECT 
                    so_item.mat_id,
                    so.so_id,
                    so_item.sale_volume, 
                    COALESCE(do_buffer.weight, 0) AS sent_volume,
                    so_item.sale_volume - COALESCE(do_buffer.weight, 0) AS res_volume,
                    COALESCE(draft_buffer.weight, 0) AS draft_volume,
                    so_item.sale_volume - COALESCE(do_buffer.weight, 0) - COALESCE(draft_buffer.weight, 0) AS res_draft_volume,
                    so.so_pub_date
                FROM so_item
                LEFT JOIN so
                ON so.so_id = so_item.so_id
                LEFT JOIN 
                (
                    SELECT do_item.mat_id, do.so_id, SUM(do_item.weight_deliver) AS weight 
                    FROM do_item
                    LEFT JOIN do
                    ON do.do_id = do_item.do_id
                    WHERE do_item.do_id IN 
                        (
                            SELECT do.do_id 
                            FROM do 
                            WHERE do.do_status_id < 90
                        )
                    GROUP BY do_item.mat_id, do.so_id
                ) do_buffer 
                ON (
                    so_item.mat_id = do_buffer.mat_id
                    AND so_item.so_id = do_buffer.so_id
                )
                LEFT JOIN 
                (
                    SELECT 
                        result_id,
                        so_id,                                 
                        SUM(pd_weight) AS weight  
                    FROM draft_do_item 
                    INNER JOIN pd_item USING (pd_item_id) 
                    GROUP BY result_id
                ) draft_buffer 
                ON (
                    so_item.mat_id = draft_buffer.result_id
                    AND so_item.so_id = draft_buffer.so_id
                )
                WHERE so_status_id < 9
            """
        )

        return self.fetch_list_of_dict(cur)
