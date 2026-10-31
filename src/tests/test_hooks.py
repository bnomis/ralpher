from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import ralphlib.hooks
import ralphlib.options
import ralphlib.types


@pytest.fixture(autouse=True)
def reset_hook_state() -> None:
    ralphlib.hooks.processed_hooks.clear()
    ralphlib.hooks.seen_task_ids.clear()


def make_options(**kwargs: Any) -> ralphlib.options.RalpherOptions:
    settings = kwargs.pop('settings', {})
    options = ralphlib.options.RalpherOptions(**kwargs)
    options.settings = settings
    return options


class TestEvent:
    def test_returns_early_when_no_hooks_configured(self) -> None:
        options = make_options(settings={})
        with patch.object(ralphlib.hooks, 'run_hook') as mock_run:
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_run.assert_not_called()

    def test_returns_early_when_event_type_not_in_hooks(self) -> None:
        options = make_options(settings={'hooks': {'end': ['echo done']}})
        with patch.object(ralphlib.hooks, 'run_hook') as mock_run:
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_run.assert_not_called()

    def test_passes_context_to_run_hook_for_matching_event(self) -> None:
        options = make_options(settings={'hooks': {'start': ['echo hello']}})
        with patch.object(ralphlib.hooks, 'run_hook') as mock_run:
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_run.assert_called_once()
            cmd, context = mock_run.call_args[0]
            assert cmd == 'echo hello'
            assert context['event_type'] == 'start'

    def test_passes_no_context_when_hook_templates_false(self) -> None:
        options = make_options(
            settings={
                'hooks': {'start': ['echo raw']},
                'hook_templates': False,
            }
        )
        with patch.object(ralphlib.hooks, 'run_hook') as mock_run:
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_run.assert_called_once_with('echo raw', None)

    def test_calls_run_hook_for_each_command_in_list(self) -> None:
        options = make_options(
            settings={
                'hooks': {'start': ['echo one', 'echo two', 'echo three']},
                'hook_templates': False,
            }
        )
        with patch.object(ralphlib.hooks, 'run_hook') as mock_run:
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
        options = make_options(iterations=5)
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['event_type'] == 'start'
        assert context['iterations'] == '5'
        assert 'datetime_utc' in context
        assert 'datetime_local' in context
        assert 'time_epoch' in context
        assert isinstance(context['time_epoch'], str)

    def test_resolves_task_file_when_set(self) -> None:
        options = make_options(iterations=1, task_file='tasks/my-task.md')
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['task_file'].endswith('/tasks/my-task.md')
        assert context['task_file_basename'] == 'my-task.md'
        assert context['task_file_number'] == ''
        assert context['task_file_stem'] == 'my-task'
        assert context['task_file_suffix'] == '.md'

    def test_non_numeric_task_file_suffix_gives_empty_number(self) -> None:
        options = make_options(iterations=1, task_file='tasks/my-task-abc.md')
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['task_file_number'] == ''

    def test_task_file_fields_are_empty_when_not_set(self) -> None:
        options = make_options(iterations=1)
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['task_file'] == ''
        assert context['task_file_basename'] == ''

    def test_merges_event_context(self) -> None:
        options = make_options(iterations=1)
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
            'cwd': '/src/litrev',
            'task_file': '/src/litrev/agents/tasks/audit-reviews/tasks-1.md',
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
            'litrev audit-reviews done',
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
    @patch('subprocess.Popen')
    def test_calls_popen_with_correct_args(self, mock_popen: MagicMock) -> None:
        ralphlib.hooks.run_hook('echo hello world')
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0] == ['echo', 'hello', 'world']

    @patch('subprocess.Popen')
    def test_renders_context_when_given(self, mock_popen: MagicMock) -> None:
        ralphlib.hooks.run_hook('echo {{ msg }}', {'msg': "it's here"})
        assert mock_popen.call_args[0][0] == ['echo', "it's here"]

    @patch('subprocess.Popen')
    def test_logs_exception_on_unbalanced_quotes_in_template(self, mock_popen: MagicMock) -> None:
        with patch('loguru.logger.exception') as mock_log:
            ralphlib.hooks.run_hook("echo 'unclosed", {})
            mock_popen.assert_not_called()
            mock_log.assert_called_once()

    @patch('subprocess.Popen', side_effect=FileNotFoundError('not found'))
    def test_logs_exception_on_subprocess_failure(self, mock_popen: MagicMock) -> None:
        with patch('loguru.logger.exception') as mock_log:
            ralphlib.hooks.run_hook('nonexistent_cmd')
            mock_log.assert_called_once()
            log_msg = mock_log.call_args[0][0]
            assert 'nonexistent_cmd' in log_msg
