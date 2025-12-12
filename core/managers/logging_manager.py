import os
import logging
from logging.handlers import RotatingFileHandler


class LoggingManager:
    def __init__(self, app):
        self.app = app

    def setup_logging(self):
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Detect if running in Vagrant
        working_dir = os.environ.get('WORKING_DIR', '')
        is_vagrant = working_dir == '/vagrant/'

        # Only use file logging outside Vagrant
        if not is_vagrant:
            file_handler = RotatingFileHandler("app.log", maxBytes=10240, backupCount=10)
            file_handler.setLevel(logging.ERROR)
            file_handler.setFormatter(formatter)
            self.app.logger.addHandler(file_handler)

        # Console logging
        if self.app.debug:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            stream_handler.setFormatter(formatter)
            self.app.logger.addHandler(stream_handler)

        self.app.logger.setLevel(logging.INFO)
