import json
import pathlib
import typing

import filelock
import loguru
import rich.console
import tenacity

import ralphlib.exceptions
import ralphlib.logger

if typing.TYPE_CHECKING:
    import ralphlib.options

STATE_LOCK_TIMEOUT = 10
console_stderr = rich.console.Console(stderr=True, highlight=False)


def load_state(options: ralphlib.options.RalpherOptions) -> dict[str, typing.Any] | None:
    if not options.state:
        return None

    path = ralphlib.logger.state_file(options)
    if not path:
        raise ralphlib.exceptions.NoStateFilePathError()

    if not path.exists():
        return {}

    try:
        with path.open('r') as fp:
            return json.load(fp)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ralphlib.exceptions.StateFileError(f'Cannot read state file {path}') from e


def save_state(options: ralphlib.options.RalpherOptions, state: dict[str, typing.Any]) -> None:
    if not options.state:
        return

    path = ralphlib.logger.state_file(options)
    if not path:
        raise ralphlib.exceptions.NoStateFilePathError()

    try:
        with path.open('w') as fp:
            json.dump(state, fp, indent=2, sort_keys=True)
    except OSError as e:
        raise ralphlib.exceptions.StateFileError(f'Cannot write state file {path}') from e


def add_to_state(
    options: ralphlib.options.RalpherOptions,
    value: dict[str, typing.Any],
    key1: str | None = None,
    key2: str | None = None,
) -> None:
    if not options.state:
        return

    lock_path = ralphlib.logger.state_lock_file(options)
    if not lock_path:
        raise ralphlib.exceptions.NoStateLockFilePathError()

    try:
        add_to_state_work(options, lock_path, value, key1, key2)
    except Exception as e:
        # auditme: accept[except-interpolation] the message is also printed to stderr, which shows no traceback
        s = f'Exception in add_to_state: {e}'
        loguru.logger.exception(s)
        console_stderr.print(s)
        raise


@tenacity.retry(
    reraise=True,
    retry=tenacity.retry_if_exception_type(filelock.Timeout),
    wait=tenacity.wait_fixed(1),
    stop=tenacity.stop_after_attempt(3),
)
def add_to_state_work(
    options: ralphlib.options.RalpherOptions,
    lock_path: pathlib.Path,
    value: dict[str, typing.Any],
    key1: str | None = None,
    key2: str | None = None,
) -> None:
    lock = filelock.FileLock(lock_path)

    try:
        acquired = lock.acquire(timeout=STATE_LOCK_TIMEOUT)
    except filelock.Timeout:
        raise
    except OSError as e:
        raise ralphlib.exceptions.StateFileError(f'Cannot create state lock file {lock_path}') from e

    with acquired:
        state = load_state(options)
        if state is None:
            return

        if key1 is not None:
            current_value = state.get(key1, {})
            if not isinstance(current_value, dict):
                raise ralphlib.exceptions.ValueNotADictError(f'{key1}')
            if key2 is not None:
                current_value2 = current_value.get(key2, {})
                if not isinstance(current_value2, dict):
                    raise ralphlib.exceptions.ValueNotADictError(f'{key1}/{key2}')
                current_value2.update(value)
                current_value[key2] = current_value2
            else:
                current_value.update(value)
            state[key1] = current_value
        else:
            state.update(value)
        save_state(options, state)
