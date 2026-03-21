from typing import Any
from unittest.mock import MagicMock, patch

import ralphlib.hooks
import ralphlib.options
import ralphlib.types


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

    def test_calls_preprocess_and_run_hook_for_matching_event(self) -> None:
        options = make_options(settings={'hooks': {'start': ['echo hello']}})
        with (
            patch.object(ralphlib.hooks, 'preprocess_hook', return_value='echo hello') as mock_pre,
            patch.object(ralphlib.hooks, 'run_hook') as mock_run,
        ):
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_pre.assert_called_once()
            mock_run.assert_called_once_with('echo hello')

    def test_skips_template_preprocessing_when_hook_templates_false(self) -> None:
        options = make_options(
            settings={
                'hooks': {'start': ['echo raw']},
                'hook_templates': False,
            }
        )
        with (
            patch.object(ralphlib.hooks, 'preprocess_hook') as mock_pre,
            patch.object(ralphlib.hooks, 'run_hook') as mock_run,
        ):
            ralphlib.hooks.event(options, ralphlib.types.RalpherEventType.START, {})
            mock_pre.assert_not_called()
            mock_run.assert_called_once_with('echo raw')

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
            mock_run.assert_any_call('echo one')
            mock_run.assert_any_call('echo two')
            mock_run.assert_any_call('echo three')


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

    def test_includes_task_file_when_set(self) -> None:
        options = make_options(iterations=1, task_file='tasks/my-task.md')
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert context['task_file'] == 'tasks/my-task.md'

    def test_excludes_task_file_when_not_set(self) -> None:
        options = make_options(iterations=1)
        context = ralphlib.hooks.make_context(options, ralphlib.types.RalpherEventType.START, {})
        assert 'task_file' not in context

    def test_merges_event_context(self) -> None:
        options = make_options(iterations=1)
        context = ralphlib.hooks.make_context(
            options,
            ralphlib.types.RalpherEventType.ERROR,
            {'error_msg': 'something failed'},
        )
        assert context['error_msg'] == 'something failed'
        assert context['event_type'] == 'error'


class TestRunHook:
    @patch('subprocess.Popen')
    def test_calls_popen_with_correct_args(self, mock_popen: MagicMock) -> None:
        ralphlib.hooks.run_hook('echo hello world')
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0] == ['echo', 'hello', 'world']

    @patch('subprocess.Popen', side_effect=FileNotFoundError('not found'))
    def test_logs_exception_on_subprocess_failure(self, mock_popen: MagicMock) -> None:
        with patch('loguru.logger.exception') as mock_log:
            ralphlib.hooks.run_hook('nonexistent_cmd')
            mock_log.assert_called_once()
            log_msg = mock_log.call_args[0][0]
            assert 'nonexistent_cmd' in log_msg
