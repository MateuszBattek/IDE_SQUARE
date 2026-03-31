import datetime

class LogManager:
    def __init__(self):
        self.logs = []

    def log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp}: [INFO]: {message}"
        self.logs.append(log_entry)

    def reset_logs(self):
        self.logs = []

    def get_logs(self):
        return self.logs

    def to_serializable(self):
        return self.logs

    def load_logs(self, logs):
        self.logs = logs
