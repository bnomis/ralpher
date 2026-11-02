import copy
import json
import pathlib
import tempfile
import typing

import filelock
import hypothesis
import hypothesis.strategies
import pytest
import tenacity

import ralphlib.exceptions
import ralphlib.logger
import ralphlib.options
import ralphlib.state
import tests.helpers


class TestLoadState:
    def test_returns_empty_dict_for_nonexistent_file(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        result = ralphlib.state.load_state(options)
        assert result == {}

    def test_returns_none_when_state_not_set(self) -> None:
        options = tests.helpers.make_plain_options(state=None)
        result = ralphlib.state.load_state(options)
        assert result is None

    def test_returns_parsed_json_when_file_exists(self, tmp_path: pathlib.Path) -> None:
        state_path = tmp_path / 'state.json'
        state_path.write_text(json.dumps({'foo': 'bar'}))
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        result = ralphlib.state.load_state(options)
        assert result == {'foo': 'bar'}

    def test_corrupt_file_raises_naming_path(self, tmp_path: pathlib.Path) -> None:
        state_path = tmp_path / 'state.json'
        state_path.write_text('{not json')
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        with pytest.raises(ralphlib.exceptions.StateFileError, match='state.json'):
            ralphlib.state.load_state(options)


class TestSaveState:
    def test_noop_when_state_not_set(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state=None, logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'data': 'value'})
        assert not list(tmp_path.iterdir())

    def test_writes_json_to_state_file(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'alpha': 1, 'beta': 2})
        state_path = tmp_path / 'state.json'
        assert state_path.exists()
        content = json.loads(state_path.read_text())
        assert content == {'alpha': 1, 'beta': 2}


class TestAddToState:
    def test_no_keys_merges_into_top_level(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'existing': 'data'})
        ralphlib.state.add_to_state(options, {'new': 'value'})
        result = ralphlib.state.load_state(options)
        assert result == {'existing': 'data', 'new': 'value'}

    def test_key1_creates_nested_dict(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {})
        ralphlib.state.add_to_state(options, {'inner': 'val'}, key1='outer')
        result = ralphlib.state.load_state(options)
        assert result == {'outer': {'inner': 'val'}}

    def test_key1_updates_existing_nested_dict(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'outer': {'old': 'data'}})
        ralphlib.state.add_to_state(options, {'new': 'data'}, key1='outer')
        result = ralphlib.state.load_state(options)
        assert result == {'outer': {'old': 'data', 'new': 'data'}}

    def test_key1_key2_creates_doubly_nested_dict(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {})
        ralphlib.state.add_to_state(options, {'deep': 'val'}, key1='level1', key2='level2')
        result = ralphlib.state.load_state(options)
        assert result == {'level1': {'level2': {'deep': 'val'}}}

    def test_key1_key2_updates_existing_doubly_nested_dict(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'level1': {'level2': {'old': 'data'}}})
        ralphlib.state.add_to_state(options, {'new': 'data'}, key1='level1', key2='level2')
        result = ralphlib.state.load_state(options)
        assert result == {'level1': {'level2': {'old': 'data', 'new': 'data'}}}

    def test_sequential_calls_accumulate_state(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {})
        ralphlib.state.add_to_state(options, {'a': 1})
        ralphlib.state.add_to_state(options, {'b': 2})
        ralphlib.state.add_to_state(options, {'c': 3}, key1='nested')
        result = ralphlib.state.load_state(options)
        assert result == {'a': 1, 'b': 2, 'nested': {'c': 3}}

    def test_corrupt_file_is_left_unchanged(self, tmp_path: pathlib.Path) -> None:
        state_path = tmp_path / 'state.json'
        state_path.write_bytes(b'{not json\xff')
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        with pytest.raises(ralphlib.exceptions.StateFileError, match='state.json'):
            ralphlib.state.add_to_state(options, {'new': 'val'})
        assert state_path.read_bytes() == b'{not json\xff'

    def test_lock_timeout_is_retried_then_raised(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        attempts: list[float] = []

        def acquire(self: filelock.FileLock, timeout: float) -> None:
            attempts.append(timeout)
            raise filelock.Timeout(str(self.lock_file))

        monkeypatch.setattr(filelock.FileLock, 'acquire', acquire)
        monkeypatch.setattr(ralphlib.state.add_to_state_work.retry, 'wait', tenacity.wait_none())
        with pytest.raises(ralphlib.exceptions.StateFileError) as excinfo:
            ralphlib.state.add_to_state(options, {'new': 'val'})
        assert isinstance(excinfo.value.__cause__, filelock.Timeout)
        assert str(ralphlib.logger.state_lock_file(options)) in str(excinfo.value)
        assert len(attempts) == 3

    def test_noop_when_state_not_set(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state=None, logdir=str(tmp_path))
        ralphlib.state.add_to_state(options, {'data': 'value'})
        assert not list(tmp_path.iterdir())

    def test_value_not_a_dict_raised_for_key1_non_dict(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'key': 'string_not_dict'})
        with pytest.raises(ralphlib.exceptions.ValueNotADictError, match='key'):
            ralphlib.state.add_to_state(options, {'new': 'val'}, key1='key')

    def test_value_not_a_dict_raised_for_key1_key2_non_dict(self, tmp_path: pathlib.Path) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        ralphlib.state.save_state(options, {'outer': {'inner': 'string_not_dict'}})
        with pytest.raises(ralphlib.exceptions.ValueNotADictError, match='outer/inner'):
            ralphlib.state.add_to_state(options, {'new': 'val'}, key1='outer', key2='inner')


class TestDomainErrors:
    def test_save_state_translates_os_error(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / 'state.json').mkdir()
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))
        with pytest.raises(ralphlib.exceptions.StateFileError):
            ralphlib.state.save_state(options, {'a': 1})

    def test_lock_os_error_is_translated(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        options = tests.helpers.make_plain_options(state='state.json', logdir=str(tmp_path))

        def acquire(self: filelock.FileLock, timeout: float) -> None:
            raise PermissionError('denied')

        monkeypatch.setattr(filelock.FileLock, 'acquire', acquire)
        with pytest.raises(ralphlib.exceptions.StateFileError):
            ralphlib.state.add_to_state(options, {'new': 'val'})


KEYS = hypothesis.strategies.sampled_from(['a', 'b', 'c'])
LEAVES = hypothesis.strategies.dictionaries(hypothesis.strategies.sampled_from(['x', 'y', 'z']), hypothesis.strategies.integers(), max_size=3)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    initial=hypothesis.strategies.dictionaries(KEYS, hypothesis.strategies.dictionaries(KEYS, LEAVES, max_size=3), max_size=3),
    value=LEAVES,
    key1=hypothesis.strategies.none() | KEYS,
    key2=hypothesis.strategies.none() | KEYS,
)
def test_add_to_state_merges_value_at_its_keys_and_leaves_the_rest(
    initial: dict[str, typing.Any], value: dict[str, int], key1: str | None, key2: str | None
) -> None:
    with tempfile.TemporaryDirectory() as logdir:
        state_path = pathlib.Path(logdir) / 'state.json'
        state_path.write_text(json.dumps(initial))
        options = tests.helpers.make_plain_options(state='state.json', logdir=logdir)

        ralphlib.state.add_to_state(options, value, key1, key2)

        expected = copy.deepcopy(initial)
        if key1 is None:
            expected.update(value)
        elif key2 is None:
            expected.setdefault(key1, {}).update(value)
        else:
            expected.setdefault(key1, {}).setdefault(key2, {}).update(value)
        assert json.loads(state_path.read_text()) == expected
