#!/usr/bin/env python
"""
This example builds on the network.py example. The main difference is that it illustrates
the use of the InfluxDB logger. In order to run this example, you'll need InfluxDB
installed and running, and you'll need to configure some environment variables. See
README.md for details.
"""

from hwtest.controller import CheckAndWait, Controller
from hwtest.influxdb import InfluxDbLogger

from network import NetworkDriver, Network


class NetworkTest(Controller):
    def __init__(self):
        super().__init__()

        driver = NetworkDriver()
        driver.logger = InfluxDbLogger("network-example")

        self.network = Network(driver)
        self.register_component(self.network)

    def test(self):
        yield
        for i in range(10):
            self.network.send()
            yield CheckAndWait(1)


if __name__ == "__main__":
    fails = NetworkTest().run()
    print(f"{fails} failures")
