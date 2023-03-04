#!/usr/bin/env python
"""
Example test that monitors a network interface as a Component.

This example illustrates the main pieces of a test:
- hardware drivers (a network interface)
- components (also a network interface)
- logging (logs to stdout)
- test (sends bytes over the network and verifies bytes sent)
"""

import subprocess
import time
from typing import NamedTuple, Tuple

from hwtest.component import Component
from hwtest.controller import Controller
from hwtest.driver import Driver
from hwtest.logging import Logger, NullLogger
from hwtest.telemetry import Telemetry

class NetworkReadResult(NamedTuple):
    incremental_bytes: int
    cumulative_bytes: int

class NetworkTelemetry(Telemetry):
    device: str = "network"
    incremental_bytes: int
    cumulative_bytes: int

    def __init__(self, incremental_bytes: int, cumulative_bytes: int) -> None:
        self.timestamp = time.time()
        self.incremental_bytes = incremental_bytes
        self.cumulative_bytes = cumulative_bytes

    def keys(self) -> Tuple[str]:
        return super().keys() + (
            "incremental_bytes",
            "cumulative_bytes",
        )

class NetworkDriver(Driver):
    logger: Logger = NullLogger()

    def __init__(self):
        self.last_bytes_sent = self.bytes_sent()

    def read(self, **kwargs) -> NetworkReadResult:
        n = self.bytes_sent()
        d = n - self.last_bytes_sent
        self.last_bytes_sent = n
        self.logger.log(NetworkTelemetry(d, n))
        return NetworkReadResult(d, n)

    def bytes_sent(self) -> NetworkReadResult:
        with open("/proc/net/dev") as f:
            for line in f.readlines():
                if line.lstrip().startswith("lo:"):
                    return int(line.split()[1])
        return 0

    def write(self, **kwargs) -> None:
        # Send some arbitrary bytes
        subprocess.call(
            ["ping", "-c", "1", "localhost"],
            stdout=subprocess.DEVNULL,
        )


class Network(Component):
    def __init__(self, driver: NetworkDriver):
        self.name = "network"
        self.driver = driver
        self.expect_bytes = False

    def check(self):
        n = self.driver.read().incremental_bytes
        if self.expect_bytes:
            self.assert_gt(0, n)
        else:
            # This assumes nothing outside the test uses this interface
            self.assert_between(0, n, 0)

        # Reset expectation
        self.expect_bytes = False

    def send(self):
        self.driver.write()
        self.expect_bytes = True


class NetworkTest(Controller):
    def __init__(self):
        super().__init__()
        self.network = Network(NetworkDriver())
        self.register_component(self.network)

    def test(self):
        yield 0 # Check no bytes sent
        yield 1 # Double check
        self.network.send()
        yield 1 # Check bytes sent


if __name__ == "__main__":
    fails = NetworkTest().run()
    print(f"{fails} failures")
