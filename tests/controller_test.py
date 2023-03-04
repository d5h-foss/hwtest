from unittest.mock import patch

import pytest

from hwtest.component import Component
from hwtest.controller import CheckAndWait, Controller, DuplicateComponentName


# Allows setting a value without assignment
class BoolBox:
    value: bool = False


class TestComponent(Component):
    def __init__(self, name: str = "test") -> None:
        self.name = name
        self.check_count = 0

    def check(self):
        self.check_count += 1


class YieldOnceController(Controller):
    def test(self):
        yield


def test_setup_called():
    setup_called = BoolBox()

    class TC(YieldOnceController):
        def setup(self):
            setup_called.value = True

    TC().run()
    assert setup_called.value

def test_teardown_called():
    teardown_called = BoolBox()

    class TC(YieldOnceController):
        def teardown(self):
            teardown_called.value = True

    TC().run()
    assert teardown_called.value


def test_register_same_component():
    c = TestComponent()
    tc = YieldOnceController()
    tc.register_component(c)
    tc.register_component(c)

def test_register_same_component_name():
    tc = YieldOnceController()
    tc.register_component(TestComponent())
    with pytest.raises(DuplicateComponentName):
        tc.register_component(TestComponent())

def test_check_called():
    comp1 = TestComponent("test1")
    comp2 = TestComponent("test2")

    tc = YieldOnceController()
    tc.register_component(comp1)
    tc.register_component(comp2)
    tc.run()
    assert comp1.check_count == 1
    assert comp2.check_count == 1

@patch('time.sleep')
def test_sleep(mock_sleep):
    tc = YieldOnceController()
    tc.default_action_args = 1
    tc.run()
    mock_sleep.assert_called_once_with(1)

@patch('time.sleep')
def test_check_and_wait_zero(mock_sleep):
    comp = TestComponent()
    tc = YieldOnceController()
    tc.default_action_class = CheckAndWait
    tc.register_component(comp)
    tc.run()
    assert comp.check_count == 1
    # Do not call sleep if wait == 0
    mock_sleep.assert_not_called()

@patch('time.sleep')
def test_check_and_wait(mock_sleep):
    comp = TestComponent()
    tc = YieldOnceController()
    tc.default_action_class = CheckAndWait
    tc.default_action_args = 1
    tc.register_component(comp)
    tc.run()
    assert comp.check_count == 1
    assert mock_sleep.call_args.args[0] <= 1.0
