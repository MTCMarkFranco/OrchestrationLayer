import logging
import colorlog
import time

class duration_formatter(colorlog.ColoredFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()

    def format(self, record):
        duration = time.time() - self.start_time
        self.start_time = time.time()
        record.duration = "{:.1f}".format(duration)
        return super().format(record)
    
class logger_service:
    def __init__(self):
        handler = colorlog.StreamHandler()
        handler.setFormatter(duration_formatter('%(log_color)s%(levelname)s: Previous Step Time: %(duration)s(seconds). Next Step: %(message)s',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }))
        self.logger = colorlog.getLogger("__CHATBOT__")
        self.logger.handlers = []
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

class logger_proxy:
    
    logger_service = logger_service()
    
    @staticmethod
    def get_logger_service():
        return logger_proxy.logger_service

    