import logging

from libs.settings import settings


class Logging:
    def init(self):
        logging.basicConfig(
            format='%(asctime)s %(name)s %(levelname)s %(message)s',
            level=logging.DEBUG if settings.get_setting(
                'STAGE') == 'dev' else logging.INFO,
            datefmt='%H:%M:%S'
        )

    def getLogger(self, name: str):
        return logging.getLogger(name)
