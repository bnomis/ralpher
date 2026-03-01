import pytest

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
