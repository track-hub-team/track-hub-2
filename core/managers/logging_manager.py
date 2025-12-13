import os
import logging
from logging.handlers import RotatingFileHandler


class LoggingManager:
    def __init__(self, app):
        self.app = app

    def setup_logging(self):
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        working_dir = os.environ.get('WORKING_DIR', '')

        should_use_file_logging = (
            working_dir != '/vagrant/' and
            working_dir != '/app/' and
            working_dir != ''
        )

        if should_use_file_logging:
            try:
                file_handler = RotatingFileHandler("app.log", maxBytes=10240, backupCount=10)
                file_handler.setLevel(logging.ERROR)
                file_handler.setFormatter(formatter)
                self.app.logger.addHandler(file_handler)
            except (PermissionError, OSError) as e:
                # If we can't create the log file, just skip it
                print(f"Warning: Could not create log file: {e}")

        # Console logging
        if self.app.debug:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            stream_handler.setFormatter(formatter)
            self.app.logger.addHandler(stream_handler)

        self.app.logger.setLevel(logging.INFO)
