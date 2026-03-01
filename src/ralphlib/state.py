import json
import pathlib
import sys
from typing import TYPE_CHECKING

import filelock
import loguru
import tenacity

import ralphlib.exceptions
import ralphlib.logger

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions

STATE_LOCK_TIMEOUT = 10


def load_state(options: RalpherOptions) -> dict | None:
    if not options.state:
        return None

    path = ralphlib.logger.state_file(options)
    if not path:
        raise ralphlib.exceptions.NoStateFilePath()

    try:
        if path.exists():
            with path.open('r') as fp:
                return json.load(fp)
    except Exception as e:
        loguru.logger.exception(f'Exception in load_state: {e}')

    return {}


def save_state(options: RalpherOptions, state: dict) -> None:
    if not options.state:
        return

    path = ralphlib.logger.state_file(options)
    if not path:
        raise ralphlib.exceptions.NoStateFilePath()

    with path.open('w') as fp:
        json.dump(state, fp, indent=2, sort_keys=True)


def add_to_state(
    options: RalpherOptions,
    value: dict,
    key1: str | None = None,
    key2: str | None = None,
) -> None:
    if not options.state:
        return

    lock_path = ralphlib.logger.state_lock_file(options)
    if not lock_path:
        raise ralphlib.exceptions.NoStateLockFilePath()

    try:
        add_to_state_work(options, lock_path, value, key1, key2)
    except Exception as e:
        s = f'Exception in add_to_state: {e}'
        loguru.logger.exception(s)
        print(s, file=sys.stderr, flush=True)
        raise


@tenacity.retry(
    reraise=True,
    retry=tenacity.retry_if_exception_type(filelock.Timeout),
    wait=tenacity.wait_fixed(1),
    stop=tenacity.stop_after_attempt(3),
)
def add_to_state_work(
    options: RalpherOptions,
    lock_path: pathlib.Path,
    value: dict,
    key1: str | None = None,
    key2: str | None = None,
) -> None:
    lock = filelock.FileLock(lock_path)

    try:
        with lock.acquire(timeout=STATE_LOCK_TIMEOUT):
            state = load_state(options)
            if state is None:
                return

            if key1 is not None:
                current_value = state.get(key1, {})
                if not isinstance(current_value, dict):
                    raise ralphlib.exceptions.ValueNotADict(f'{key1}')
                if key2 is not None:
                    current_value2 = current_value.get(key2, {})
                    if not isinstance(current_value2, dict):
                        raise ralphlib.exceptions.ValueNotADict(f'{key1}/{key2}')
                    current_value2.update(value)
                    current_value[key2] = current_value2
                else:
                    current_value.update(value)
                state[key1] = current_value
            else:
                state.update(value)
            save_state(options, state)
    except filelock.Timeout:
        loguru.logger.exception(f'Could not acquire state lock after {STATE_LOCK_TIMEOUT} seconds')
