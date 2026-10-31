import collections.abc

import pytest

import ralphlib.signals


@pytest.fixture(autouse=True)
def reset_should_exit() -> collections.abc.Iterator[None]:
    ralphlib.signals.set_should_exit(False)
    yield
    ralphlib.signals.set_should_exit(False)
