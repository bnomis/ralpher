from collections.abc import Iterator

import pytest

import ralphlib.signals


@pytest.fixture(autouse=True)
def reset_should_exit() -> Iterator[None]:
    ralphlib.signals.set_should_exit(False)
    yield
    ralphlib.signals.set_should_exit(False)
