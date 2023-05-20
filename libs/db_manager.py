from abc import ABCMeta
from mariadb import Connection, Cursor


class Repository:
    def __init__(self, conn: Connection):
        self.__conn = conn

    def commit(self):
        try:
            self.__conn.commit()
        except Exception as e:
            self.__conn.rollback()
            raise e

    def run_in_transaction(self, task, kwargs: dict = None, is_raise: bool = True, is_commit: bool = True):
        if kwargs is None:
            kwargs = dict()

        try:
            result = task(**kwargs)

            if is_commit:
                self.__conn.commit()

            return result

        except BaseException as e:
            self.__conn.rollback()
            if is_raise:
                raise e


class CustomRepository(metaclass=ABCMeta):
    def __init__(self, conn: Connection):
        self.conn = conn

    def fetch_list_of_dict(self, cur: Cursor):
        result = cur.fetchall()
        key_names = [x[0] for x in cur.description]
        result = [dict(zip(key_names, x)) for x in result]

        return result
