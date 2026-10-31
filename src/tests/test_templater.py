import pytest
from hypothesis import given, settings as hypothesis_settings, strategies as st

import ralphlib.exceptions
import ralphlib.options
import ralphlib.templater


def test_templater() -> None:
    options = ralphlib.options.RalpherOptions(
        vars=[
            'name=World',
            'greeting=Hello',
        ]
    )
    prompt = '{{ greeting }}, {{ name }}!'
    rendered = ralphlib.templater.render(options, prompt, 1)
    assert rendered == 'Hello, World!'


def test_iteration_context_variable() -> None:
    options = ralphlib.options.RalpherOptions(vars=[])
    prompt = 'Iteration {{ iteration }}'
    rendered = ralphlib.templater.render(options, prompt, 5)
    assert rendered == 'Iteration 5'


def test_iteration_context_variable_is_string() -> None:
    options = ralphlib.options.RalpherOptions(vars=[])
    prompt = '{{ iteration }}'
    rendered = ralphlib.templater.render(options, prompt, 42)
    assert rendered == '42'


def test_var_without_equals_raises_an_error() -> None:
    options = ralphlib.options.RalpherOptions(vars=['noequals', 'valid=yes'])
    prompt = '{{ valid }}'

    with pytest.raises(ralphlib.exceptions.InvalidVarFormat):
        ralphlib.templater.render(options, prompt, 1)


def test_var_with_multiple_equals_splits_on_first() -> None:
    options = ralphlib.options.RalpherOptions(vars=['key=val=ue'])
    prompt = '{{ key }}'
    rendered = ralphlib.templater.render(options, prompt, 1)
    assert rendered == 'val=ue'


def test_empty_vars_only_iteration_available() -> None:
    options = ralphlib.options.RalpherOptions(vars=[])
    prompt = '{{ iteration }}'
    rendered = ralphlib.templater.render(options, prompt, 7)
    assert rendered == '7'


def test_undefined_variable_renders_empty() -> None:
    options = ralphlib.options.RalpherOptions(vars=[])
    prompt = '{{ undefined_var }}'
    rendered = ralphlib.templater.render(options, prompt, 1)
    assert rendered == ''


def test_slugify_lowercases_input() -> None:
    assert ralphlib.templater.slugify('HELLO') == 'hello'


def test_slugify_replaces_non_alphanumeric_with_hyphens() -> None:
    assert ralphlib.templater.slugify('hello world!') == 'hello-world'


def test_slugify_strips_leading_trailing_hyphens() -> None:
    assert ralphlib.templater.slugify('--hello--') == 'hello'


def test_slugify_collapses_consecutive_special_chars() -> None:
    assert ralphlib.templater.slugify('a!!!b') == 'a-b'


def test_slugify_returns_empty_string_for_empty_input() -> None:
    assert ralphlib.templater.slugify('') == ''


@given(st.text())
@hypothesis_settings(max_examples=20, deadline=10000)
def test_slugify_output_contains_only_valid_chars(value: str) -> None:
    result = ralphlib.templater.slugify(value)
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in result)
    assert not result.startswith('-')
    assert not result.endswith('-')


def test_task_file_slug_with_multipart_path_uses_parent_stem() -> None:
    result = ralphlib.templater.task_file_slug('agents/tasks/my_task.md')
    assert result == 'tasks-my-task'


def test_task_file_slug_with_single_part_path_uses_stem_only() -> None:
    result = ralphlib.templater.task_file_slug('my_task.md')
    assert result == 'my-task'
