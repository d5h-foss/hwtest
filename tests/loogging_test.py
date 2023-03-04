from unittest.mock import patch

from hwtest.logging import Fail, Pass, StdoutLogger, ThreadLogger

from helpers import MockLogger


def test_eq():
    assert Fail("test", 0, 1, 2, timestamp=0) == Fail("test", 0, 1, 2, timestamp=0)
    assert Fail("test", 0, 1, 2, timestamp=0) != Pass("test", 0, 1, 2, timestamp=0)
    assert Fail("test", 0, 1, 2, timestamp=0) != Fail("test", 0, 1, 3, timestamp=0)

@patch('builtins.print')
def test_stdout_logger(mock_print):
    logger = StdoutLogger()

    logger.log(Fail("test", 0, 1, 2, timestamp=0))
    mock_print.assert_called_with("0,FAIL,test,0,1,2")

    logger.log(Fail("test", 0, 1, 2, subcomponent_name="sub", timestamp=0))
    mock_print.assert_called_with("0,FAIL,test,0,1,2,sub")

def test_thread_logger():
    test_logger = MockLogger()
    thread_logger = ThreadLogger(test_logger)

    assert len(test_logger.logs) == 0

    log_events = [
        Fail("test", 0, 3, 2, timestamp=0),
        Pass("test", 0, 1, 2, timestamp=1),
    ]
    for e in log_events:
        thread_logger.log(e)

    thread_logger.close()
    assert test_logger.logs == log_events
