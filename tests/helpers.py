from hwtest.logging import LogEvent, Logger


class MockLogger(Logger):
    def __init__(self):
        self.logs = []

    def log(self, event: LogEvent):
        self.logs.append(event)
