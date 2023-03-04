from abc import ABC, abstractmethod
import atexit
from queue import Queue
from threading import Thread
import time
from typing import Any, Dict, Optional, Sequence, Tuple


class LogEvent:
    timestamp: Optional[float]
    type_tag: str

    def keys(self) -> Tuple[str]:
        return (
            "timestamp",
            "type_tag",
        )

    def values(self) -> Sequence[Any]:
        return [
            getattr(self, k) for k in self.keys()
        ]

    def items(self) -> Dict[str, Any]:
        return {
            k: getattr(self, k) for k in self.keys()
        }

    # Used for testing
    def __eq__(self, other: object) -> bool:
        return isinstance(other, LogEvent) and self.items() == other.items()


class CheckEvent(LogEvent):
    component_name: str
    lower_bound: float
    value: float
    upper_bound: float
    subcomponent_name: Optional[str]

    def __init__(
        self,
        component_name: str,
        lower_bound: float,
        value: float,
        upper_bound: float,
        subcomponent_name: Optional[str] = None,
        timestamp: Optional[float] = None,
    ):
        if timestamp is None:
            timestamp = time.time()

        self.timestamp = timestamp
        self.component_name = component_name
        self.lower_bound = lower_bound
        self.value = value
        self.upper_bound = upper_bound
        self.subcomponent_name = subcomponent_name

    def keys(self) -> Tuple[str]:
        return super().keys() + (
            "component_name",
            "lower_bound",
            "value",
            "upper_bound",
        ) + (("subcomponent_name",) if self.subcomponent_name else tuple())

class Pass(CheckEvent):
    type_tag: str = "PASS"

class Fail(CheckEvent):
    type_tag: str = "FAIL"


class Logger(ABC):
    @abstractmethod
    def log(self, event: LogEvent) -> None:
        raise NotImplemented()

class NullLogger(Logger):
    def log(self, event: LogEvent) -> None:
        pass

class StdoutLogger(Logger):
    def log(self, event: LogEvent) -> None:
        print(",".join(str(f) for f in event.values()))


class ThreadLogger(Logger):
    def __init__(self, logger: Logger):
        self.queue = Queue()
        self.thread = _LoggingThread(self.queue, logger)
        self.thread.start()
        atexit.register(self._atexit)

    def log(self, event: LogEvent):
        self.queue.put(event)

    def close(self):
        self.thread.finish = True
        self.thread.join()

    def _atexit(self):
        self.close()  # no cov

class _LoggingThread(Thread):
    def __init__(self, queue: Queue, logger: Logger):
        super().__init__()
        self.queue = queue
        self.logger = logger
        self.finish = False

    def run(self):
        while not (self.finish and self.queue.empty()):
            event = self.queue.get()
            self.logger.log(event)
            self.queue.task_done()
