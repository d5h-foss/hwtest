from typing import Optional

from hwtest.logging import Fail, Logger, Pass, StdoutLogger


INF = float("inf")


class Component:
    name: str = ""  # Must give each Component a unique name
    logger: Logger = StdoutLogger()
    fail_count: int = 0

    # Override this
    def check(self):
        """Tests internal consistency of the Component."""

        raise NotImplemented()

    def assert_lt(
        self,
        value: float,
        upper_bound: float,
        name: Optional[str] = None,
    ):
        if value < upper_bound:
            self.log_pass(-INF, value, upper_bound, name)
        else:
            self.log_fail(-INF, value, upper_bound, name)

    def assert_gt(
        self,
        lower_bound: float,
        value: float,
        name: Optional[str] = None,
    ):
        if lower_bound < value:
            self.log_pass(lower_bound, value, INF, name)
        else:
            self.log_fail(lower_bound, value, INF, name)

    def assert_between(
        self,
        lower_bound: float,
        value: float,
        upper_bound: float,
        name: Optional[str] = None,
    ):
        if lower_bound <= value <= upper_bound:
            self.log_pass(lower_bound, value, upper_bound, name)
        else:
            self.log_fail(lower_bound, value, upper_bound, name)

    def log_pass(
        self,
        lower_bound: float,
        value: float,
        upper_bound: float,
        name: Optional[str] = None,
    ):
        self.logger.log(Pass(self.name, lower_bound, value, upper_bound, name))

    def log_fail(
        self,
        lower_bound: float,
        value: float,
        upper_bound: float,
        name: Optional[str] = None,
    ):
        self.fail_count += 1
        self.logger.log(Fail(self.name, lower_bound, value, upper_bound, name))
