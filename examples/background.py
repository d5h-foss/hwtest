#!/usr/bin/env python
"""
Similar to the InfluxDB example, except this shows how to write a driver that's called in
a background process. The process logs continually (at 50 Hz) to InfluxDB.
"""

from ctypes import c_int, Structure
from typing import Any

from hwtest.controller import CheckAndWait, Controller
from hwtest.driver import Driver, SubprocessDriver
from hwtest.influxdb import InfluxDbLogger
from hwtest.telemetry import Telemetry

from network import Network, NetworkDriver, NetworkTelemetry


# This is the same as NetworkReadResult from the network.py example, but must be a ctypes
# structure for subprocess logging.
class NetworkReadResult(Structure):
    _fields_ = [("incremental_bytes", c_int), ("cumulative_bytes", c_int)]

# Converts the ctypes structure to a Telemetry object
def read_result_to_telemetry(r: NetworkReadResult) -> NetworkTelemetry:
    return NetworkTelemetry(r.incremental_bytes, r.cumulative_bytes)

class SubprocessNetworkDriver(Driver):
    # Wrap the NetworkDriver from the network.py example, so we can reuse the code while
    # converting the read result to the ctypes structure.
    def __init__(self, driver: NetworkDriver) -> None:
        self.driver = driver

    def read(self, **kwargs) -> Any:
        r = self.driver.read()
        return NetworkReadResult(
            incremental_bytes=r.incremental_bytes,
            cumulative_bytes=r.cumulative_bytes
        )

    def write(self, **kwargs) -> Any:
        self.driver.write()


class NetworkTest(Controller):
    def __init__(self):
        super().__init__()

        driver = SubprocessNetworkDriver(NetworkDriver())
        logger = InfluxDbLogger("network-example")
        bg_driver = SubprocessDriver(
            driver=driver,
            read_args={},
            read_result_type=NetworkReadResult,
            logger=logger,
            telemetry_factory=read_result_to_telemetry
        )

        self.network = Network(bg_driver)
        self.register_component(self.network)

    def test(self):
        yield
        for i in range(10):
            self.network.send()
            yield CheckAndWait(1)


if __name__ == "__main__":
    fails = NetworkTest().run()
    print(f"{fails} failures")
