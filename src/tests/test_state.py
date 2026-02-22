import json
import pathlib
from typing import Any

import pytest

import ralphlib.exceptions
import ralphlib.options
import ralphlib.state


def make_options(**kwargs: Any) -> ralphlib.options.RalpherOptions:
    return ralphlib.options.RalpherOptions(**kwargs)


class TestLoadState:
    def test_returns_empty_dict_for_nonexistent_file(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        result = ralphlib.state.load_state(options)
        assert result == {}

    def test_returns_none_when_state_not_set(self) -> None:
        options = make_options(state=None)
        result = ralphlib.state.load_state(options)
        assert result is None

    def test_returns_parsed_json_when_file_exists(self, tmp_path: pathlib.Path) -> None:
        state_path = tmp_path / 'state.json'
        state_path.write_text(json.dumps({'foo': 'bar'}))
        options = make_options(state='state.json', logdir=str(tmp_path))
        result = ralphlib.state.load_state(options)
        assert result == {'foo': 'bar'}


class TestSaveState:
    def test_noop_when_state_not_set(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state=None, logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'data': 'value'})
        assert not list(tmp_path.iterdir())

    def test_writes_json_to_state_file(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'alpha': 1, 'beta': 2})
        state_path = tmp_path / 'state.json'
        assert state_path.exists()
        content = json.loads(state_path.read_text())
        assert content == {'alpha': 1, 'beta': 2}


class TestAddToState:
    def test_no_keys_merges_into_top_level(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'existing': 'data'})
        ralphlib.state.add_to_state(options, {'new': 'value'})
        result = ralphlib.state.load_state(options)
        assert result == {'existing': 'data', 'new': 'value'}

    def test_key1_creates_nested_dict(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {})
        ralphlib.state.add_to_state(options, {'inner': 'val'}, key1='outer')
        result = ralphlib.state.load_state(options)
        assert result == {'outer': {'inner': 'val'}}

    def test_key1_updates_existing_nested_dict(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'outer': {'old': 'data'}})
        ralphlib.state.add_to_state(options, {'new': 'data'}, key1='outer')
        result = ralphlib.state.load_state(options)
        assert result == {'outer': {'old': 'data', 'new': 'data'}}

    def test_key1_key2_creates_doubly_nested_dict(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {})
        ralphlib.state.add_to_state(options, {'deep': 'val'}, key1='level1', key2='level2')
        result = ralphlib.state.load_state(options)
        assert result == {'level1': {'level2': {'deep': 'val'}}}

    def test_key1_key2_updates_existing_doubly_nested_dict(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'level1': {'level2': {'old': 'data'}}})
        ralphlib.state.add_to_state(options, {'new': 'data'}, key1='level1', key2='level2')
        result = ralphlib.state.load_state(options)
        assert result == {'level1': {'level2': {'old': 'data', 'new': 'data'}}}

    def test_sequential_calls_accumulate_state(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {})
        ralphlib.state.add_to_state(options, {'a': 1})
        ralphlib.state.add_to_state(options, {'b': 2})
        ralphlib.state.add_to_state(options, {'c': 3}, key1='nested')
        result = ralphlib.state.load_state(options)
        assert result == {'a': 1, 'b': 2, 'nested': {'c': 3}}

    def test_noop_when_state_not_set(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state=None, logdir=str(tmp_path))
        ralphlib.state.add_to_state(options, {'data': 'value'})
        assert not list(tmp_path.iterdir())

    def test_value_not_a_dict_raised_for_key1_non_dict(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'key': 'string_not_dict'})
        with pytest.raises(ralphlib.exceptions.ValueNotADict, match='key'):
            ralphlib.state.add_to_state(options, {'new': 'val'}, key1='key')

    def test_value_not_a_dict_raised_for_key1_key2_non_dict(self, tmp_path: pathlib.Path) -> None:
        options = make_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'outer': {'inner': 'string_not_dict'}})
        with pytest.raises(ralphlib.exceptions.ValueNotADict, match='outer/inner'):
            ralphlib.state.add_to_state(options, {'new': 'val'}, key1='outer', key2='inner')
