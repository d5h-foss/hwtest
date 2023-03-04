import pytest

from hwtest.component import Component, INF
from hwtest.logging import Fail, Pass

from helpers import MockLogger


class MockComponent(Component):
    name = "test"

    def __init__(self) -> None:
        self.logger = MockLogger()

    def check(self):
        pass


@pytest.fixture
def comp():
    return MockComponent()


def test_assert_lt_pass(comp: Component):
    assert len(comp.logger.logs) == 0
    comp.assert_lt(0, 1)
    assert len(comp.logger.logs) == 1
    assert comp.logger.logs[0] == Pass(
        component_name="test",
        lower_bound=-INF,
        value=0,
        upper_bound=1,
        timestamp=comp.logger.logs[0].timestamp,
    )

def test_assert_lt_fail(comp: Component):
    assert len(comp.logger.logs) == 0
    comp.assert_lt(2, 1)
    assert len(comp.logger.logs) == 1
    assert comp.logger.logs[0] == Fail(
        component_name="test",
        lower_bound=-INF,
        value=2,
        upper_bound=1,
        timestamp=comp.logger.logs[0].timestamp,
    )

def test_assert_gt_pass(comp: Component):
    assert len(comp.logger.logs) == 0
    comp.assert_gt(0, 1)
    assert len(comp.logger.logs) == 1
    assert comp.logger.logs[0] == Pass(
        component_name="test",
        lower_bound=0,
        value=1,
        upper_bound=INF,
        timestamp=comp.logger.logs[0].timestamp,
    )

def test_assert_gt_fail(comp: Component):
    assert len(comp.logger.logs) == 0
    comp.assert_gt(2, 1)
    assert len(comp.logger.logs) == 1
    assert comp.logger.logs[0] == Fail(
        component_name="test",
        lower_bound=2,
        value=1,
        upper_bound=INF,
        timestamp=comp.logger.logs[0].timestamp,
    )

def test_assert_between_pass(comp: Component):
    assert len(comp.logger.logs) == 0
    comp.assert_between(0, 1, 2)
    assert len(comp.logger.logs) == 1
    assert comp.logger.logs[0] == Pass(
        component_name="test",
        lower_bound=0,
        value=1,
        upper_bound=2,
        timestamp=comp.logger.logs[0].timestamp,
    )

def test_assert_between_fail(comp: Component):
    assert len(comp.logger.logs) == 0
    comp.assert_between(0, 3, 2)
    assert len(comp.logger.logs) == 1
    assert comp.logger.logs[0] == Fail(
        component_name="test",
        lower_bound=0,
        value=3,
        upper_bound=2,
        timestamp=comp.logger.logs[0].timestamp,
    )