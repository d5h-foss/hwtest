from abc import ABC, abstractmethod
import atexit
import ctypes
from multiprocessing import Process, Value
import time
from typing import Any, Callable, Dict, Type

from hwtest.logging import Logger
from hwtest.telemetry import Telemetry


class Driver(ABC):
    @abstractmethod
    def read(self, **kwargs) -> Any:
        raise NotImplemented()

    @abstractmethod
    def write(self, **kwargs) -> Any:
        raise NotImplemented()


class SubprocessDriver(Driver):
    def __init__(
        self,
        driver: Driver,
        read_args: Dict[str, Any],
        read_result_type: Type[ctypes.Structure],
        logger: Logger,
        telemetry_factory: Callable[[Any], Telemetry],
        sleep: float = 0.02
    ) -> None:
        self.driver = driver
        self.last_read = Value(read_result_type)
        self.shutdown_flag = Value(ctypes.c_bool)
        args = (
            # If the driver has open file descriptors, like to a serial port, then I'm
            # not sure this will work. If that's the case, then the Process target should
            # be changed to a function that will create the driver.
            self.driver,
            read_args,
            self.last_read,
            logger,
            telemetry_factory,
            sleep,
            self.shutdown_flag,
        )
        self.process = Process(target=_subprocess_read, args=args)
        self.process.start()
        atexit.register(self._atexit)

    def read(self, **kwargs) -> Any:
        return self.last_read.get_obj()

    def write(self, **kwargs) -> Any:
        # FIXME: may need to do this in the subprocess
        return self.driver.write(**kwargs)

    def close(self):
        self.shutdown_flag.value = True
        self.process.join()

    def _atexit(self):
        self.close()  # no cov


def _subprocess_read(
    driver: Driver,
    read_args: Dict[str, Any],
    read_result: Value,
    logger: Logger,
    telemetry_factory: Callable[[Any], Telemetry],
    sleep: float,
    shutdown_flag: Value,
) -> None:
    while not shutdown_flag.value:
        value = driver.read(**read_args)
        with read_result.get_lock():
            _copy_structure(read_result.get_obj(), value)
        logger.log(telemetry_factory(value))
        time.sleep(sleep)

def _copy_structure(dst: ctypes.Structure, src: ctypes.Structure) -> None:
    # Must be the same structure type
    for attr, _ in dst._fields_:
        setattr(dst, attr, getattr(src, attr))
