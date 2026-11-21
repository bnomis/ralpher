import datetime
import pathlib
import shlex
import subprocess
import tempfile
import unittest.mock

import hypothesis
import hypothesis.strategies
import jinja2.sandbox
import pytest

import ralphlib.exceptions
import ralphlib.giter
import ralphlib.hooks
import ralphlib.options
import ralphlib.types
import ralphlib.verifier
import tests.helpers


@pytest.fixture(autouse=True)
def reset_hook_state() -> None:
    ralphlib.hooks.processed_hooks.clear()
    ralphlib.hooks.seen_task_ids.clear()
    ralphlib.hooks.clear_caches()


class TestEvent:
    def test_returns_early_when_no_hooks_configured(self) -> None:
        options = tests.helpers.make_options_with_settings(settings={})
        with unittest.mock.patch.object(ralphlib.hooks, 'run_hook') as mock_run:
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_run.assert_not_called()

    def test_returns_early_when_event_type_not_in_hooks(self) -> None:
        options = tests.helpers.make_options_with_settings(settings={'hooks': {'end': ['echo done']}})
        with unittest.mock.patch.object(ralphlib.hooks, 'run_hook') as mock_run:
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_run.assert_not_called()

    def test_passes_context_to_run_hook_for_matching_event(self) -> None:
        options = tests.helpers.make_options_with_settings(settings={'hooks': {'start': ['echo hello']}})
        with unittest.mock.patch.object(ralphlib.hooks, 'run_hook') as mock_run:
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_run.assert_called_once()
            cmd, context = mock_run.call_args[0]
            assert cmd == 'echo hello'
            assert context['event_type'] == 'start'

    def test_passes_no_context_when_hook_templates_false(self) -> None:
        options = tests.helpers.make_options_with_settings(
            settings={
                'hooks': {'start': ['echo raw']},
                'hook_templates': False,
            }
        )
        with unittest.mock.patch.object(ralphlib.hooks, 'run_hook') as mock_run:
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_run.assert_called_once_with('echo raw', None)

    def test_calls_run_hook_for_each_command_in_list(self) -> None:
        options = tests.helpers.make_options_with_settings(
            settings={
                'hooks': {'start': ['echo one', 'echo two', 'echo three']},
                'hook_templates': False,
            }
        )
        with unittest.mock.patch.object(ralphlib.hooks, 'run_hook') as mock_run:
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            assert mock_run.call_count == 3
            mock_run.assert_any_call('echo one', None)
            mock_run.assert_any_call('echo two', None)
            mock_run.assert_any_call('echo three', None)


class TestPreprocessHook:
    def test_renders_jinja2_template_with_context(self) -> None:
        result = ralphlib.hooks.preprocess_hook(
            'echo {{ event_type }} at {{ time_epoch }}',
            {'event_type': 'start', 'time_epoch': '1234567890'},
        )
        assert result == 'echo start at 1234567890'

    def test_passes_through_plain_strings(self) -> None:
        result = ralphlib.hooks.preprocess_hook(
            'echo hello world',
            {'event_type': 'start'},
        )
        assert result == 'echo hello world'


class TestMakeContext:
    def test_includes_expected_fields(self) -> None:
        options = tests.helpers.make_options_with_settings(iterations=5)
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['event_type'] == 'start'
        assert context['iterations'] == '5'
        assert 'datetime_utc' in context
        assert 'datetime_local' in context
        assert 'time_epoch' in context
        assert isinstance(context['time_epoch'], str)

    def test_resolves_task_file_when_set(self) -> None:
        options = tests.helpers.make_options_with_settings(iterations=1, task_file='tasks/my-task.md')
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['task_file'].endswith('/tasks/my-task.md')
        assert context['task_file_basename'] == 'my-task.md'
        assert context['task_file_number'] == ''
        assert context['task_file_stem'] == 'my-task'
        assert context['task_file_suffix'] == '.md'

    def test_non_numeric_task_file_suffix_gives_empty_number(self) -> None:
        options = tests.helpers.make_options_with_settings(iterations=1, task_file='tasks/my-task-abc.md')
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['task_file_number'] == ''

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('tasks-3', '3'),
            ('tasks-0.md', '0'),
            ('tasks-007.md', '007'),
            ('a-b-12.tar.gz', ''),
            ('tasks.md', ''),
            ('3.md', ''),
            ('tasks-.md', ''),
        ],
    )
    def test_task_file_number_cases(self, name: str, expected: str) -> None:
        options = tests.helpers.make_options_with_settings(iterations=1, task_file=f'tasks/{name}')
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['task_file_number'] == expected

    @hypothesis.settings(max_examples=20, deadline=10000)
    @hypothesis.given(
        prefix=hypothesis.strategies.text(alphabet='abc-', min_size=1, max_size=8),
        number=hypothesis.strategies.integers(min_value=0, max_value=10**6),
        suffix=hypothesis.strategies.sampled_from(['', '.md']),
    )
    def test_task_file_number_is_digits_after_last_dash(self, prefix: str, number: int, suffix: str) -> None:
        options = tests.helpers.make_options_with_settings(
            iterations=1,
            task_file=f'tasks/{prefix}-{number}{suffix}',
        )
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['task_file_number'] == str(number)

    def test_task_file_fields_are_empty_when_not_set(self) -> None:
        options = tests.helpers.make_options_with_settings(iterations=1)
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['task_file'] == ''
        assert context['task_file_basename'] == ''

    def test_merges_event_context(self) -> None:
        options = tests.helpers.make_options_with_settings(iterations=1)
        context = ralphlib.hooks.make_context(
            options,
            ralphlib.types.RalpherEventType.ERROR,
            {'error_msg': 'something failed'},
        )
        assert context['error_msg'] == 'something failed'
        assert context['event_type'] == 'error'


class TestRenderHookArgs:
    ALERTER = (
        '/opt/homebrew/bin/alerter --app-icon {{ralpher_root}}/img/ralpher.jpg '
        "--title '{{cwd|basename}} {{task_file|dirname|basename}} done' --message '{{task_title}}'"
    )

    def render(self, **context: str) -> list[str]:
        base = {
            'ralpher_root': '/src/ralpher',
            'cwd': '/src/probe',
            'task_file': '/src/probe/agents/tasks/audit-reviews/tasks-1.md',
            'task_title': 'plain title',
        }
        return ralphlib.hooks.render_hook_args(self.ALERTER, base | context)

    def test_apostrophe_in_value_does_not_break_the_parse(self) -> None:
        title = "Give each project's config.py a module name mypy can distinguish"
        assert self.render(task_title=title)[-1] == title

    def test_double_quotes_and_metacharacters_survive(self) -> None:
        title = 'He said "it\'s fine" & ran `rm -rf /` $HOME'
        assert self.render(task_title=title)[-1] == title

    def test_value_with_spaces_stays_one_argument(self) -> None:
        args = self.render(task_title='two words')
        assert args == [
            '/opt/homebrew/bin/alerter',
            '--app-icon',
            '/src/ralpher/img/ralpher.jpg',
            '--title',
            'probe audit-reviews done',
            '--message',
            'two words',
        ]

    def test_composite_argument_with_spacey_values_stays_one_argument(self) -> None:
        args = self.render(cwd='/src/my project')
        assert args[4] == 'my project audit-reviews done'

    def test_value_cannot_inject_extra_arguments(self) -> None:
        assert self.render(task_title="x' --sound Funky '")[-1] == "x' --sound Funky '"

    def test_value_cannot_forge_a_sentinel(self) -> None:
        forged = f'{ralphlib.hooks.HOOK_VALUE_SENTINEL}0{ralphlib.hooks.HOOK_VALUE_SENTINEL}'
        assert self.render(task_title=forged)[-1] == '0'

    def test_newlines_in_a_value_are_preserved(self) -> None:
        assert self.render(task_title='line one\nline two')[-1] == 'line one\nline two'


class TestRunHook:
    @unittest.mock.patch('subprocess.Popen')
    def test_calls_popen_with_correct_args(self, mock_popen: unittest.mock.MagicMock) -> None:
        ralphlib.hooks.run_hook('echo hello world')
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0] == ['echo', 'hello', 'world']

    @unittest.mock.patch('subprocess.Popen')
    def test_renders_context_when_given(self, mock_popen: unittest.mock.MagicMock) -> None:
        ralphlib.hooks.run_hook('echo {{ msg }}', {'msg': "it's here"})
        assert mock_popen.call_args[0][0] == ['echo', "it's here"]

    @unittest.mock.patch('subprocess.Popen')
    def test_warns_on_unbalanced_quotes_in_template(self, mock_popen: unittest.mock.MagicMock) -> None:
        with unittest.mock.patch('loguru.logger.opt') as mock_opt:
            ralphlib.hooks.run_hook("echo 'unclosed", {})
            mock_popen.assert_not_called()
            mock_opt.return_value.warning.assert_called_once()

    @unittest.mock.patch('subprocess.Popen')
    def test_warns_on_template_error(self, mock_popen: unittest.mock.MagicMock) -> None:
        with unittest.mock.patch('loguru.logger.opt') as mock_opt:
            ralphlib.hooks.run_hook('echo {{ unclosed', {})
            mock_popen.assert_not_called()
            mock_opt.return_value.warning.assert_called_once()

    @unittest.mock.patch('subprocess.Popen', side_effect=FileNotFoundError('not found'))
    def test_warns_on_subprocess_failure(self, mock_popen: unittest.mock.MagicMock) -> None:
        with unittest.mock.patch('loguru.logger.opt') as mock_opt:
            ralphlib.hooks.run_hook('nonexistent_cmd')
            mock_opt.return_value.warning.assert_called_once()
            assert 'nonexistent_cmd' in mock_opt.return_value.warning.call_args[0][0]

    @unittest.mock.patch('subprocess.Popen', side_effect=subprocess.SubprocessError('bad'))
    def test_warns_on_subprocess_error(self, mock_popen: unittest.mock.MagicMock) -> None:
        with unittest.mock.patch('loguru.logger.opt') as mock_opt:
            ralphlib.hooks.run_hook('some_cmd')
            mock_opt.return_value.warning.assert_called_once()

    @unittest.mock.patch('subprocess.Popen', side_effect=RuntimeError('boom'))
    def test_unexpected_error_propagates(self, mock_popen: unittest.mock.MagicMock) -> None:
        with pytest.raises(RuntimeError):
            ralphlib.hooks.run_hook('echo hi')


class TestMakeContextDomainErrors:
    def test_time_zone_failure_raises_ralpher_error(self) -> None:
        options = tests.helpers.make_options_with_settings()
        with unittest.mock.patch('tzlocal.get_localzone', side_effect=LookupError('no zone')), pytest.raises(ralphlib.exceptions.RalpherError):
            ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})


class TestTaskFileChoice:
    def test_unblock_prompt_uses_the_verifier_choice_without_worktree(self) -> None:
        options = tests.helpers.make_plain_options(task_file='tasks-1.md', worktree=False)
        with unittest.mock.patch.object(ralphlib.verifier, 'worktree_task_file', return_value=pathlib.Path('/wt/tasks-1.md')) as wt:
            assert ralphlib.hooks.unblock_prompt(options, '4') == 'unblock task 4 in task file tasks-1.md'
        wt.assert_not_called()

    def test_unblock_prompt_uses_the_worktree_copy_under_worktree(self) -> None:
        options = tests.helpers.make_plain_options(task_file='tasks-1.md', worktree=True)
        with unittest.mock.patch.object(ralphlib.verifier, 'worktree_task_file', return_value=pathlib.Path('/wt/tasks-1.md')):
            assert ralphlib.hooks.unblock_prompt(options, '4') == 'unblock task 4 in worktree task file /wt/tasks-1.md'

    def test_unblock_prompt_falls_back_when_the_worktree_is_missing(self) -> None:
        options = tests.helpers.make_plain_options(task_file='tasks-1.md', worktree=True)
        with unittest.mock.patch.object(ralphlib.verifier, 'worktree_task_file', return_value=None):
            assert ralphlib.hooks.unblock_prompt(options, '4') == (
                'unblock task 4 in task file tasks-1.md (the worktree tasks file could not be found, so this is the main tasks file)'
            )

    def test_duplicate_event_runs_no_git(self) -> None:
        options = tests.helpers.make_options_with_settings(settings={'hooks': {'start': ['echo dup']}}, worktree=True, task_file='t.md')
        with unittest.mock.patch.object(ralphlib.hooks, 'run_hook'):
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            with unittest.mock.patch.object(ralphlib.verifier, 'worktree_task_file') as wt:
                ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
        wt.assert_not_called()

    def test_last_commit_summary_looked_up_only_when_named(self) -> None:
        with unittest.mock.patch.object(ralphlib.giter, 'last_commit_summary', return_value='s') as summary:
            options = tests.helpers.make_options_with_settings(settings={'hooks': {'start': ['echo plain']}})
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            summary.assert_not_called()
            ralphlib.hooks.processed_hooks.clear()
            options = tests.helpers.make_options_with_settings(settings={'hooks': {'start': ['echo {{ last_commit_summary }}']}})
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            summary.assert_called_once()


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(value=hypothesis.strategies.text())
def test_render_hook_args_round_trips_any_value_as_one_argument(value: str) -> None:
    args = ralphlib.hooks.render_hook_args('notify --message {{ value }} --end', {'value': value})
    assert args == ['notify', '--message', value.replace(ralphlib.hooks.HOOK_VALUE_SENTINEL, ''), '--end']


def test_templates_compile_once_across_events() -> None:
    with unittest.mock.patch.object(ralphlib.hooks.jinja2.sandbox.SandboxedEnvironment, 'from_string', autospec=True) as from_string:
        ralphlib.hooks.compile_template('echo {{ a }}', True)
        ralphlib.hooks.compile_template('echo {{ a }}', True)
        ralphlib.hooks.compile_template('echo {{ a }}')
    assert from_string.call_count == 2


def test_render_hook_args_twice_gives_the_same_arguments() -> None:
    first = ralphlib.hooks.render_hook_args('notify {{ v }}', {'v': 'a b'})
    second = ralphlib.hooks.render_hook_args('notify {{ v }}', {'v': 'c "d"'})
    assert first == ['notify', 'a b']
    assert second == ['notify', 'c "d"']


def test_render_hook_args_cached_template_with_constant_output() -> None:
    cmd = 'echo {{ "a b" }} {{ v }}'
    assert ralphlib.hooks.render_hook_args(cmd, {'v': 'x'}) == ['echo', 'a b', 'x']
    assert ralphlib.hooks.render_hook_args(cmd, {'v': 'y'}) == ['echo', 'a b', 'y']


def test_quote_the_value() -> None:
    var = "Give each project's config.py a module name mypy can distinguish"
    s = f'/opt/homebrew/bin/alerter --title {shlex.quote("probe audit-reviews 57/7")} --message {shlex.quote(var)}'
    print(s)
    args = shlex.split(s)
    print(args)
    assert args[-1] == var


def test_quote_handles_double_quotes_too() -> None:
    var = """He said "it's fine" & ran `rm -rf /` $HOME"""
    args = shlex.split(f'alerter --message {shlex.quote(var)}')
    assert args == ['alerter', '--message', var]


def test_jinja_finalize_quotes_every_substitution() -> None:
    env = jinja2.sandbox.SandboxedEnvironment(finalize=lambda v: shlex.quote(str(v)))
    template = env.from_string('/opt/homebrew/bin/alerter --title {{ title }} --message {{ message }}')
    cmd = template.render(
        title='probe audit-reviews 57/7',
        message="Give each project's config.py a module name mypy can distinguish",
    )
    args = shlex.split(cmd)
    assert args[-1] == "Give each project's config.py a module name mypy can distinguish"


class TestLocalTimezone:
    @pytest.mark.parametrize('error', [LookupError('x'), OSError('x'), ValueError('x')])
    def test_lookup_failure_raises_ralpher_error(self, error: Exception) -> None:
        with (
            unittest.mock.patch.object(ralphlib.hooks.tzlocal, 'get_localzone', side_effect=error),
            pytest.raises(ralphlib.exceptions.RalpherError, match='local time zone') as excinfo,
        ):
            ralphlib.hooks.local_timezone()
        assert excinfo.value.__cause__ is error

    def test_returns_the_zone_and_caches_it(self) -> None:
        zone = datetime.UTC
        with unittest.mock.patch.object(ralphlib.hooks.tzlocal, 'get_localzone', return_value=zone) as mock_zone:
            assert ralphlib.hooks.local_timezone() is zone
            assert ralphlib.hooks.local_timezone() is zone
            mock_zone.assert_called_once()


class TestFixedContext:
    def test_empty_arguments_give_empty_values(self) -> None:
        context = ralphlib.hooks.fixed_context('', '')
        for key, value in context.items():
            if key != 'ralpher_root':
                assert value == '', key

    def test_cwd_only(self, tmp_path: pathlib.Path) -> None:
        context = ralphlib.hooks.fixed_context(str(tmp_path), '')
        assert context['cwd'] == str(tmp_path.resolve())
        assert context['cwd_basename'] == tmp_path.name
        assert context['cwd_dirname'] == str(tmp_path.resolve().parent)
        assert context['task_file'] == ''
        assert context['task_file_relative_path'] == ''

    def test_task_file_only_has_absolute_relative_path(self, tmp_path: pathlib.Path) -> None:
        task_file = tmp_path / 'sub' / 'tasks.md'
        context = ralphlib.hooks.fixed_context('', str(task_file))
        assert context['cwd'] == ''
        assert context['task_file'] == str(task_file.resolve())
        assert context['task_file_relative_path'] == str(task_file.resolve())
        assert context['task_file_basename'] == 'tasks.md'
        assert context['task_file_dir_basename'] == 'sub'
        assert context['task_file_stem'] == 'tasks'
        assert context['task_file_suffix'] == '.md'
        assert context['task_file_number'] == ''

    def test_task_file_inside_cwd_is_relative(self, tmp_path: pathlib.Path) -> None:
        context = ralphlib.hooks.fixed_context(str(tmp_path), str(tmp_path / 'sub' / 'tasks.md'))
        assert context['task_file_relative_path'] == str(pathlib.Path('sub') / 'tasks.md')

    def test_task_file_outside_cwd_stays_absolute(self, tmp_path: pathlib.Path) -> None:
        cwd = tmp_path / 'work'
        cwd.mkdir()
        task_file = tmp_path / 'other' / 'tasks.md'
        context = ralphlib.hooks.fixed_context(str(cwd), str(task_file))
        assert context['task_file_relative_path'] == str(task_file.resolve())

    def test_number_suffix_is_extracted(self, tmp_path: pathlib.Path) -> None:
        context = ralphlib.hooks.fixed_context(str(tmp_path), str(tmp_path / 'tasks-4.md'))
        assert context['task_file_number'] == '4'
        assert context['task_file_stem'] == 'tasks-4'

    def test_number_only_matches_at_end_of_stem(self, tmp_path: pathlib.Path) -> None:
        context = ralphlib.hooks.fixed_context(str(tmp_path), str(tmp_path / 'tasks-4-extra.md'))
        assert context['task_file_number'] == ''

    @hypothesis.given(
        segments=hypothesis.strategies.lists(hypothesis.strategies.from_regex(r'[a-z][a-z0-9]{0,8}', fullmatch=True), min_size=1, max_size=3),
        stem=hypothesis.strategies.from_regex(r'[a-z][a-z0-9]{0,8}', fullmatch=True),
        suffix=hypothesis.strategies.sampled_from(['', '.md', '.txt']),
    )
    def test_basename_and_relative_path_round_trip(self, segments: list[str], stem: str, suffix: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = pathlib.Path(tmp).resolve()
            task_file = cwd.joinpath(*segments, f'{stem}{suffix}')
            ralphlib.hooks.clear_caches()
            context = ralphlib.hooks.fixed_context(str(cwd), str(task_file))
        assert context['task_file_basename'] == context['task_file_stem'] + context['task_file_suffix']
        assert context['task_file_basename'] == f'{stem}{suffix}'
        assert cwd / context['task_file_relative_path'] == task_file


class TestLastCommitSummary:
    def test_empty_when_no_command_icon_or_sound_names_it(self) -> None:
        options = tests.helpers.make_options_with_settings(settings={'hook_icon': 'i', 'hook_sound': 's'})
        with unittest.mock.patch.object(ralphlib.giter, 'last_commit_summary') as mock_summary:
            assert ralphlib.hooks.last_commit_summary(options, ['echo one']) == ''
            mock_summary.assert_not_called()

    @pytest.mark.parametrize(
        ('commands', 'settings'),
        [
            (['echo {{ last_commit_summary }} now'], {}),
            (['echo two'], {'hook_icon': '{{ last_commit_summary }}'}),
            (['echo three'], {'hook_sound': '{{ last_commit_summary }}'}),
        ],
    )
    def test_calls_giter_when_named(self, commands: list[str], settings: dict[str, str]) -> None:
        options = tests.helpers.make_options_with_settings(settings=settings)
        with unittest.mock.patch.object(ralphlib.giter, 'last_commit_summary', return_value='abc fix') as mock_summary:
            assert ralphlib.hooks.last_commit_summary(options, commands) == 'abc fix'
            mock_summary.assert_called_once_with()

    def test_commands_none_always_calls(self) -> None:
        options = tests.helpers.make_options_with_settings(settings={})
        with unittest.mock.patch.object(ralphlib.giter, 'last_commit_summary', return_value='abc fix') as mock_summary:
            assert ralphlib.hooks.last_commit_summary(options, None) == 'abc fix'
            mock_summary.assert_called_once_with()
