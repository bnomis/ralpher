import json
from typing import TYPE_CHECKING

import ralphlib.logger

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


def load_state(options: RalpherOptions) -> dict | None:
    if not options.state:
        return None

    path = ralphlib.logger.state_file(options)
    if not path:
        raise Exception('None state file path')

    if path.exists():
        with path.open('r') as fp:
            return json.load(fp)

    return {}


def save_state(options: RalpherOptions, state: dict) -> None:
    if not options.state:
        return

    path = ralphlib.logger.state_file(options)
    if not path:
        raise Exception('None state file path')

    with path.open('w') as fp:
        json.dump(state, fp, indent=2, sort_keys=True)


def add_to_state(options: RalpherOptions, value: dict, key1: str | None = None, key2: str | None = None) -> None:
    state = load_state(options)
    if state is None:
        return

    if key1 is not None:
        current_value = state.get(key1, {})
        if not isinstance(current_value, dict):
            raise Exception(f'Current value for key {key1} is not a dict')
        if key2 is not None:
            current_value2 = current_value.get(key2, {})
            if not isinstance(current_value2, dict):
                raise Exception(f'Current value for key {key1}/{key2} is not a dict')
            current_value2.update(value)
            current_value[key2] = current_value2
        else:
            current_value.update(value)
        state[key1] = current_value
    else:
        state.update(value)
    save_state(options, state)
