import mariadb

CONFIG_KEYS = ["user", "password", "host", "database"]


class DbConnection:
    def __init__(self, config):
        self.connect(config)

    def __validate_config(self, config: dict):
        for key in CONFIG_KEYS:
            if not config.get(key):
                raise AttributeError('Database configuration incomplete')

    def connect(self, config):
        try:
            self.__validate_config(config)
        except AttributeError as e:
            raise e
        except BaseException:
            raise Exception('Something went wrong')

        self.__conn = mariadb.connect(**config)

    def get_connector(self):
        return self.__conn

    def close_connector(self):
        self.__conn.close()
