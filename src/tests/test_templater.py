import pathlib

import hypothesis
import hypothesis.strategies
import pytest

import ralphlib.exceptions
import ralphlib.options
import ralphlib.templater

# auditme: accept[non-alphabetical-literal] the commands run in this order
SETUP_COMMANDS = ['uv sync', 'pre-commit install']


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

    with pytest.raises(ralphlib.exceptions.InvalidVarFormatError):
        ralphlib.templater.render(options, prompt, 1)


def test_parse_vars_splits_good_vars() -> None:
    options = ralphlib.options.RalpherOptions(vars=['name=World', 'expr=a=b', 'empty='])
    assert ralphlib.templater.parse_vars(options) == {'name': 'World', 'expr': 'a=b', 'empty': ''}


def test_parse_vars_without_vars_is_empty() -> None:
    options = ralphlib.options.RalpherOptions(vars=[])
    assert ralphlib.templater.parse_vars(options) == {}


def test_parse_vars_rejects_a_value_without_equals() -> None:
    options = ralphlib.options.RalpherOptions(vars=['valid=yes', 'noequals'])
    with pytest.raises(ralphlib.exceptions.InvalidVarFormatError, match="'noequals', expected key=value"):
        ralphlib.templater.parse_vars(options)


@pytest.mark.parametrize('key', ralphlib.templater.BUILTIN_VARS)
def test_parse_vars_rejects_each_built_in_key(key: str) -> None:
    options = ralphlib.options.RalpherOptions(vars=[f'{key}=override'])
    with pytest.raises(ralphlib.exceptions.InvalidVarFormatError, match=f"'{key}' is a built-in template variable"):
        ralphlib.templater.parse_vars(options)


def test_render_never_lets_a_var_replace_a_built_in() -> None:
    options = ralphlib.options.RalpherOptions(vars=['iteration=99'])
    with pytest.raises(ralphlib.exceptions.InvalidVarFormatError):
        ralphlib.templater.render(options, '{{ iteration }}', 1)


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


def test_render_refuses_an_attribute_the_sandbox_blocks() -> None:
    options = ralphlib.options.RalpherOptions(vars=[])
    with pytest.raises(ralphlib.exceptions.PromptTemplateError, match='blocked'):
        ralphlib.templater.render(options, "{{ ''.__class__.__mro__ }}", 1)


def test_render_reports_a_template_syntax_error() -> None:
    options = ralphlib.options.RalpherOptions(vars=[])
    with pytest.raises(ralphlib.exceptions.PromptTemplateError, match='syntax'):
        ralphlib.templater.render(options, '{% if %}', 1)


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


@hypothesis.given(hypothesis.strategies.text())
@hypothesis.settings(max_examples=20, deadline=10000)
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


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    parent=hypothesis.strategies.from_regex(r'[a-z][a-z0-9]{0,8}', fullmatch=True),
    stem=hypothesis.strategies.from_regex(r'[a-z][a-z0-9]{0,8}', fullmatch=True),
)
def test_task_file_slug_joins_parent_and_stem(parent: str, stem: str) -> None:
    assert ralphlib.templater.task_file_slug(f'x/{parent}/{stem}.md') == f'{parent}-{stem}'


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(path=hypothesis.strategies.text(alphabet='abcXY_ -./', min_size=1, max_size=30))
def test_task_file_slug_is_a_safe_name(path: str) -> None:
    slug = ralphlib.templater.task_file_slug(path)
    assert all(c.islower() or c.isdigit() or c == '-' for c in slug)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    variables=hypothesis.strategies.dictionaries(
        hypothesis.strategies.from_regex(r'v_[a-z0-9_]{0,8}', fullmatch=True),
        hypothesis.strategies.text(hypothesis.strategies.characters(exclude_characters='\x00'), max_size=20),
        max_size=4,
    ),
    iterations=hypothesis.strategies.integers(min_value=1, max_value=1000),
    data=hypothesis.strategies.data(),
)
def test_render_substitutes_every_var_and_the_iteration_unchanged(variables: dict[str, str], iterations: int, data: hypothesis.strategies.DataObject) -> None:
    iteration = data.draw(hypothesis.strategies.integers(min_value=1, max_value=iterations))
    options = ralphlib.options.RalpherOptions(iterations=iterations, vars=[f'{key}={value}' for key, value in variables.items()])
    prompt = '\x00'.join(['{{ iteration }}/{{ iterations }}', *(f'{{{{ {key} }}}}' for key in variables)])
    rendered = ralphlib.templater.render(options, prompt, iteration)
    assert rendered.split('\x00', len(variables)) == [f'{iteration}/{iterations}', *variables.values()]


def test_render_lists_the_worktree_setup_commands_in_order_with_worktree() -> None:
    options = ralphlib.options.RalpherOptions(worktree=True)
    options.settings = {'worktree_setup': SETUP_COMMANDS}
    assert ralphlib.templater.render(options, "{{ worktree_setup | join(',') }}", 1) == 'uv sync,pre-commit install'


def test_render_worktree_setup_is_empty_without_worktree() -> None:
    options = ralphlib.options.RalpherOptions()
    options.settings = {'worktree_setup': ['make deps']}
    assert ralphlib.templater.render(options, "{{ worktree_setup | join(',') }}", 1) == ''


def test_render_worktree_setup_is_empty_without_the_setting() -> None:
    options = ralphlib.options.RalpherOptions(worktree=True)
    assert ralphlib.templater.render(options, "{{ worktree_setup | join(',') }}", 1) == ''


def test_render_rejects_a_var_named_worktree_setup() -> None:
    options = ralphlib.options.RalpherOptions(vars=['worktree_setup=x'])
    with pytest.raises(ralphlib.exceptions.InvalidVarFormatError, match='built-in'):
        ralphlib.templater.render(options, '{{ worktree_setup }}', 1)


def test_render_worktree_setup_changes_in_a_template_leave_the_settings_alone() -> None:
    options = ralphlib.options.RalpherOptions(worktree=True)
    commands = ['npm ci']
    before = list(commands)
    options.settings = {'worktree_setup': commands}
    rendered = ralphlib.templater.render(options, "{{ worktree_setup.append('x') }}{{ worktree_setup | join(',') }}", 1)
    assert rendered == 'Nonenpm ci,x'
    assert commands == before


ONE_TASK_PROMPT = pathlib.Path(__file__).resolve().parents[2] / 'agents' / 'prompts' / 'one-task.md'


def render_one_task(worktree: bool, setup: list[str] | None) -> str:
    options = ralphlib.options.RalpherOptions(worktree=worktree, task_file='agents/tasks/x/tasks-1.md')
    if setup is not None:
        options.settings = {'worktree_setup': setup}
    return ralphlib.templater.render(options, ONE_TASK_PROMPT.read_text(), 1)


def test_one_task_prompt_lists_the_setup_commands_in_the_worktree_rules() -> None:
    rendered = render_one_task(True, SETUP_COMMANDS)
    rules = rendered.split('## Worktree rules', 1)[1].split('## Environment variables', 1)[0]
    assert rules.index('`uv sync`') < rules.index('`pre-commit install`')
    assert '<status>blocked</status>' in rules


@pytest.mark.parametrize(
    ('worktree', 'setup'),
    [
        (True, []),
        (True, None),
        (False, ['uv sync']),
    ],
)
def test_one_task_prompt_has_no_setup_block_without_commands(worktree: bool, setup: list[str] | None) -> None:
    rendered = render_one_task(worktree, setup)
    assert 'run these' not in rendered
    assert 'uv sync' not in rendered
