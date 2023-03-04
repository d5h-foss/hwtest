from abc import ABC, abstractmethod
import time
from typing import Any, Callable, Dict, Tuple, Type

from hwtest.component import Component


class DuplicateComponentName(Exception):
    pass


class ControllerAction(ABC):
    @abstractmethod
    def perform(self, controller: "Controller"):
        raise NotImplemented()

class WaitAndCheck(ControllerAction):
    def __init__(self, wait: float):
        self.wait = wait

    def perform(self, controller: "Controller"):
        if 0.0 < self.wait:
            time.sleep(self.wait)
        controller.check()

class CheckAndWait(ControllerAction):
    def __init__(self, wait: float):
        self.wait = wait

    def perform(self, controller: "Controller"):
        start = time.time()
        controller.check()

        if 0.0 < self.wait:
            end = time.time()
            dur = self.wait - (end - start)
            if 0.0 < dur:
                time.sleep(dur)

class ConditionTimeout(Exception):
    pass

def condition_timeout():
    raise ConditionTimeout()

class CheckAfterTrue(ControllerAction):
    def __init__(
        self,
        condition: Callable[[], bool],
        failure: Callable[[], None] = condition_timeout,
        timeout: float = 5,
        sleep: float = 0.001
    ):
        self.condition = condition
        self.failure = failure
        self.timeout = timeout
        self.sleep = sleep

    def perform(self, controller: "Controller"):
        start = time.time()
        while not self.condition():
            if start + self.timeout < time.time():
                self.failure()
                return
            time.sleep(self.sleep)

        controller.check()


class Controller(ABC):
    components: Dict[str, Component]

    def __init__(
        self,
        default_action_class: Type[ControllerAction] = WaitAndCheck,
        default_action_args: Tuple[Any] = (0.0,),
    ):
        self.components = {}
        self.default_action_class = default_action_class
        self.default_action_args = default_action_args

    @abstractmethod
    def test(self):
        """Implement your test here."""

        raise NotImplemented()

    def setup(self):
        """Implement setup for your test here."""
        pass

    def teardown(self):
        """Implement tear down your test here."""
        pass

    def register_component(self, c: Component):
        if c.name in self.components and c is not self.components[c.name]:
            raise DuplicateComponentName(c.name)

        self.components[c.name] = c

    def check(self):
        for c in self.components.values():
            c.check()

    def run(self) -> int:
        """Returns the number of failures in the test."""

        existing_fails = sum(c.fail_count for c in self.components.values())
        self.setup()

        try:
            for action in self.test():
                if not isinstance(action, ControllerAction):
                    if action is None:
                        action = self.default_action_args
                    if not isinstance(action, tuple):
                        action = (action,)
                    action = self.default_action_class(*action)

                action.perform(self)
        finally:
            self.teardown()

        latest_fails = sum(c.fail_count for c in self.components.values())
        return latest_fails - existing_fails
