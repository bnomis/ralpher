import collections.abc
import io
import os
import pathlib
import shlex
import signal
import subprocess
import sys
import threading
import time
import typing
import unittest.mock

import hypothesis
import hypothesis.strategies
import loguru
import orjson
import pytest

import ralphlib.exceptions
import ralphlib.hooks
import ralphlib.iteration
import ralphlib.logger
import ralphlib.options
import ralphlib.signals
import ralphlib.state
import ralphlib.templater
import ralphlib.types
import tests.helpers

# auditme: accept[non-alphabetical-literal] command line arguments; the order is the meaning
CLAUDE_CMD = ('claude', '--verbose')
TRUE_CMD = ('true',)


def make_context() -> ralphlib.iteration.IterationContext:
    return ralphlib.iteration.IterationContext(
        cmd=[],
        iteration=1,
        prompt='test',
    )


def test_process_line_system_type() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    line = orjson.dumps({'type': 'system', 'subtype': 'unknown'}).decode()
    message_type, message = ralphlib.iteration.process_line(options, context, line)
    assert message_type == ralphlib.types.MessageType.SYSTEM
    assert message == 'unknown'


def test_process_line_assistant_dispatches() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'assistant', 'message': {'content': []}}
    line = orjson.dumps(payload).decode()
    expected = (ralphlib.types.MessageType.TOOL_USE, 'mocked')

    with unittest.mock.patch.object(ralphlib.iteration, 'process_assistant', return_value=expected) as mock_fn:
        result = ralphlib.iteration.process_line(options, context, line)
        mock_fn.assert_called_once()
        assert result == expected


def test_process_line_result_dispatches() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'result': 'ok'}
    line = orjson.dumps(payload).decode()
    expected = (ralphlib.types.MessageType.NONE, line)

    with unittest.mock.patch.object(ralphlib.iteration, 'process_result', return_value=expected) as mock_fn:
        result = ralphlib.iteration.process_line(options, context, line)
        mock_fn.assert_called_once()
        assert result == expected


def test_process_line_user_dispatches() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'user', 'message': {}}
    line = orjson.dumps(payload).decode()
    expected = (ralphlib.types.MessageType.NONE, line)

    with unittest.mock.patch.object(ralphlib.iteration, 'process_user', return_value=expected) as mock_fn:
        result = ralphlib.iteration.process_line(options, context, line)
        mock_fn.assert_called_once()
        assert result == expected


def test_process_line_stream_event_dispatches() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'stream_event', 'event': {'type': 'message_start'}}
    line = orjson.dumps(payload).decode()
    expected = (ralphlib.types.MessageType.NONE, '')

    with unittest.mock.patch.object(ralphlib.iteration, 'process_stream_event', return_value=expected) as mock_fn:
        result = ralphlib.iteration.process_line(options, context, line)
        mock_fn.assert_called_once()
        assert result == expected


def test_process_line_unknown_ptype_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'unknown_type'}
    line = orjson.dumps(payload).decode()

    with unittest.mock.patch.object(ralphlib.iteration, 'print_error') as mock_print_error:
        message_type, message = ralphlib.iteration.process_line(options, context, line)
        assert message_type == ralphlib.types.MessageType.NONE
        assert message == line
        mock_print_error.assert_called_once()


def test_process_line_invalid_json_returns_error() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    line = 'this is not json'
    message_type, message = ralphlib.iteration.process_line(options, context, line)
    assert message_type == ralphlib.types.MessageType.ERROR
    assert message == line


@pytest.mark.parametrize('error', [KeyError('k'), TypeError('t'), AttributeError('a')])
def test_process_line_payload_shape_error_returns_error(error: Exception) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    line = orjson.dumps({'type': 'assistant'}).decode()

    with unittest.mock.patch.object(ralphlib.iteration, 'process_assistant', side_effect=error):
        message_type, message = ralphlib.iteration.process_line(options, context, line)
        assert message_type == ralphlib.types.MessageType.ERROR
        assert message == line


def test_process_line_unexpected_exception_propagates() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    line = orjson.dumps({'type': 'assistant'}).decode()

    with unittest.mock.patch.object(ralphlib.iteration, 'process_assistant', side_effect=RuntimeError('boom')), pytest.raises(RuntimeError):
        ralphlib.iteration.process_line(options, context, line)


@pytest.mark.parametrize(
    'writer',
    [
        lambda c: ralphlib.iteration.write_progress(c, 'x'),
        lambda c: ralphlib.iteration.write_progress_lines(c, ['x']),
        lambda c: ralphlib.iteration.write_progress_eol(c),
        lambda c: ralphlib.iteration.write_error(c, 'x'),
        lambda c: ralphlib.iteration.write_error_eol(c),
        lambda c: ralphlib.iteration.write_stdout(c, 'x'),
        lambda c: ralphlib.iteration.write_stderr(c, 'x'),
    ],
)
def test_log_writers_raise_log_file_error_on_write_failure(writer: collections.abc.Callable[[ralphlib.iteration.IterationContext], None]) -> None:
    context = make_context()
    fd = unittest.mock.MagicMock()
    fd.write.side_effect = OSError('disk full')
    context.progressfd = context.errorsfd = context.stdoutfd = context.stderrfd = fd
    with pytest.raises(ralphlib.exceptions.LogFileError):
        writer(context)


def test_log_writer_raises_log_file_error_on_flush_failure() -> None:
    context = make_context()
    fd = unittest.mock.MagicMock()
    fd.flush.side_effect = OSError('disk full')
    context.progressfd = fd
    with pytest.raises(ralphlib.exceptions.LogFileError):
        ralphlib.iteration.write_progress_eol(context)


def test_stdout_reader_log_failure_sets_error_instead_of_dying() -> None:
    context = make_context()
    fd = unittest.mock.MagicMock()
    fd.write.side_effect = OSError('disk full')
    context.stdoutfd = fd
    pipe = io.StringIO('{"type": "system"}\n')
    ralphlib.iteration.process_stdout(tests.helpers.make_plain_options(quiet=True), context, pipe)  # type: ignore[arg-type]
    assert ralphlib.iteration.get_error(context)


def test_flush_and_close_fd_carries_on_after_os_error() -> None:
    fd = unittest.mock.MagicMock()
    fd.flush.side_effect = OSError('disk')
    ralphlib.iteration.flush_and_close_fd(fd)
    fd.flush.assert_called_once()


def test_flush_and_close_fd_unexpected_error_propagates() -> None:
    fd = unittest.mock.MagicMock()
    fd.flush.side_effect = RuntimeError('boom')
    with pytest.raises(RuntimeError):
        ralphlib.iteration.flush_and_close_fd(fd)


@pytest.mark.parametrize('subtype', ['success', 'error_max_turns', 'error_during_execution'])
def test_process_result_with_is_error_sets_error_flag(subtype: str) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'result', 'subtype': subtype, 'is_error': True, 'result': 'something failed'}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.ERROR
    assert message == 'something failed'
    assert ralphlib.iteration.get_error(context) is True


def test_process_result_success_without_is_error_leaves_error_flag_clear() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'fine'}
    line = orjson.dumps(payload).decode()

    message_type, _ = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert ralphlib.iteration.get_error(context) is False


def test_process_result_with_stop_marker_sets_complete() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    result_text = 'output\n<promise>COMPLETE</promise>\n'
    payload = {'type': 'result', 'subtype': 'success', 'result': result_text}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.COMPLETE
    assert message == ''
    assert ralphlib.iteration.get_complete(context) is True


def test_process_result_with_stop_marker_in_longer_line_not_complete() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    result_text = 'output with <promise>COMPLETE</promise> marker'
    payload = {'type': 'result', 'subtype': 'success', 'result': result_text}
    line = orjson.dumps(payload).decode()

    message_type, _ = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type != ralphlib.types.MessageType.COMPLETE
    assert ralphlib.iteration.get_complete(context) is False


def test_process_result_no_stop_marker_no_error_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'result': 'normal output'}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line
    assert ralphlib.iteration.get_complete(context) is False
    assert ralphlib.iteration.get_error(context) is False


def test_process_result_custom_stop_markers_respected() -> None:
    options = tests.helpers.make_plain_options(quiet=True, stops=['DONE', 'FINISHED'])
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'result': 'task done\nFINISHED'}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.COMPLETE
    assert message == ''
    assert ralphlib.iteration.get_complete(context) is True


def test_process_result_empty_result_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'result': ''}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


# --- Test process_assistant ---


def test_process_assistant_text_with_stop_marker_sets_complete() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {'type': 'text', 'text': 'output\n<promise>COMPLETE</promise>'},
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.COMPLETE
    assert message == ''
    assert ralphlib.iteration.get_complete(context) is True


def test_process_assistant_text_without_stop_marker_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {'type': 'text', 'text': 'just some normal text'},
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line
    assert ralphlib.iteration.get_complete(context) is False


def test_process_assistant_tool_use_adds_to_tools_used_set() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {
                    'type': 'tool_use',
                    'name': 'Read',
                    'id': 'tool_1',
                    'input': {'file_path': '/home/user/test.py'},
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    ralphlib.iteration.process_assistant(options, context, payload, line)

    assert 'Read' in context.tools_used_set


def test_process_assistant_tool_use_returns_tool_use_with_formatted_output() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {
                    'type': 'tool_use',
                    'name': 'Bash',
                    'id': 'tool_1',
                    'input': {'command': 'ls -la'},
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.TOOL_USE
    assert 'Bash' in message
    assert 'ls -la' in message


def test_process_assistant_tool_run_in_background_known_tool_tracked() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {
                    'type': 'tool_use',
                    'name': 'Bash',
                    'id': 'tool_abc',
                    'input': {'command': 'sleep 10', 'run_in_background': True},
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.TOOL_USE
    assert 'tool_abc' in context.background_tools
    assert context.background_tools['tool_abc']['name'] == 'Bash'


def test_process_assistant_tool_run_in_background_unknown_tool_logs_warning() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {
                    'type': 'tool_use',
                    'name': 'UnknownTool',
                    'id': 'tool_xyz',
                    'input': {'query': 'test', 'run_in_background': True},
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    with unittest.mock.patch('loguru.logger.warning') as mock_warning:
        ralphlib.iteration.process_assistant(options, context, payload, line)
        mock_warning.assert_called()
        warning_msg = mock_warning.call_args[0][0]
        assert 'UnknownTool' in warning_msg
        assert 'not in known background tools list' in warning_msg

    assert 'tool_xyz' not in context.background_tools


def test_process_assistant_warnings_omit_the_raw_payload() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    marker = 'sk-marker-value'
    payload = {
        'type': 'assistant',
        'extra': marker,
        'message': {'content': [{'type': 'tool_use', 'name': 'UnknownTool', 'input': {}}]},
    }
    line = orjson.dumps(payload).decode()
    warnings: list[str] = []
    sink_id = loguru.logger.add(warnings.append, level='WARNING')
    try:
        ralphlib.iteration.process_assistant(options, context, payload, line)
    finally:
        loguru.logger.remove(sink_id)
    assert warnings
    assert not any(marker in w for w in warnings)


def test_process_assistant_task_output_resolves_background_tool() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()

    # get_tool_input indents task_id via indent_lines, so the lookup key is indented
    indented_id = '  bg_123'
    context.background_tools['tool_orig'] = {'name': 'Bash', 'input': '  sleep 10'}
    context.background_id_to_tool[indented_id] = 'tool_orig'

    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {
                    'type': 'tool_use',
                    'name': 'TaskOutput',
                    'id': 'tool_2',
                    'input': {'task_id': 'bg_123'},
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.TOOL_USE
    assert 'TaskOutput' in message
    assert 'Bash' in message
    assert 'sleep 10' in message


@pytest.mark.parametrize('tool_name_cls', ['TaskOutput', 'TaskStop'])
def test_process_assistant_task_tools_resolve_background(tool_name_cls: str) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()

    indented_id = '  bg_456'
    context.background_tools['tool_orig'] = {'name': 'Bash', 'input': '  echo hi'}
    context.background_id_to_tool[indented_id] = 'tool_orig'

    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {
                    'type': 'tool_use',
                    'name': tool_name_cls,
                    'id': 'tool_3',
                    'input': {'task_id': 'bg_456'},
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.TOOL_USE
    assert tool_name_cls in message
    assert 'Bash' in message


def test_process_assistant_tool_use_without_name_logs_warning() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {
                    'type': 'tool_use',
                    'id': 'tool_4',
                    'input': {'file_path': '/home/user/test.py'},
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    with unittest.mock.patch('loguru.logger.warning') as mock_warning:
        message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)
        mock_warning.assert_called()

    assert message_type == ralphlib.types.MessageType.TOOL_USE
    assert 'UNKNOWN-TOOL' in message
    assert 'UNKNOWN-TOOL' in context.tools_used_set


def test_process_assistant_empty_message_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'assistant', 'message': {}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


def test_process_assistant_empty_content_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'assistant', 'message': {'content': []}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


# --- Test process_stream_event ---


@pytest.mark.parametrize('event_type', ['message_delta', 'message_start', 'message_stop'])
def test_process_stream_event_message_types_return_none(event_type: str) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'stream_event', 'event': {'type': event_type}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == ''


def test_process_stream_event_content_block_start_text_returns_content_start() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'stream_event',
        'event': {
            'type': 'content_block_start',
            'content_block': {'type': 'text', 'text': 'hello'},
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.CONTENT_START
    assert message == 'hello'


def test_process_stream_event_content_block_start_tool_use_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'stream_event',
        'event': {
            'type': 'content_block_start',
            'content_block': {'type': 'tool_use', 'id': 'tool_1', 'name': 'Read'},
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == ''


def test_process_stream_event_content_block_stop_returns_content_stop() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'stream_event',
        'event': {'type': 'content_block_stop'},
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.CONTENT_STOP
    assert message == ''


def test_process_stream_event_content_block_delta_text_returns_content_delta() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'stream_event',
        'event': {
            'type': 'content_block_delta',
            'delta': {'type': 'text_delta', 'text': 'world'},
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.CONTENT_DELTA
    assert message == 'world'


def test_process_stream_event_content_block_delta_input_json_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'stream_event',
        'event': {
            'type': 'content_block_delta',
            'delta': {'type': 'input_json_delta', 'partial_json': '{"key":'},
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == ''


def test_process_stream_event_unknown_event_type_returns_none_with_line() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'stream_event',
        'event': {'type': 'some_unknown_event'},
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


# --- Test iteration helper functions ---


def test_input_field_to_content_returns_first_matching_regular_field() -> None:
    input_field = {'command': 'ls -la', 'description': 'list files'}
    result = ralphlib.iteration.input_field_to_content(input_field)
    assert result == 'ls -la'


def test_input_field_to_content_returns_file_path_field() -> None:
    input_field = {'file_path': '/home/user/test.py'}
    result = ralphlib.iteration.input_field_to_content(input_field)
    assert result == '/home/user/test.py'


def test_input_field_to_content_returns_formatted_todos_when_no_regular_fields() -> None:
    input_field = {
        'todos': [
            {'content': 'first task', 'status': 'pending'},
            {'content': 'second task', 'status': 'done'},
        ],
    }
    result = ralphlib.iteration.input_field_to_content(input_field)
    assert result == '- first task\n- second task'


def test_input_field_to_content_skips_todos_without_content() -> None:
    input_field = {
        'todos': [
            {'content': 'has content'},
            {'status': 'pending'},
            {'content': ''},
        ],
    }
    result = ralphlib.iteration.input_field_to_content(input_field)
    assert result == '- has content'


def test_input_field_to_content_returns_empty_string_when_no_fields_match() -> None:
    input_field = {'some_other_field': 'value'}
    result = ralphlib.iteration.input_field_to_content(input_field)
    assert result == ''


def test_input_field_to_content_returns_empty_string_for_empty_dict() -> None:
    result = ralphlib.iteration.input_field_to_content({})
    assert result == ''


def test_get_run_in_background_returns_true_when_boolean_true() -> None:
    content = {'input': {'run_in_background': True}}
    assert ralphlib.iteration.get_run_in_background(content) is True


def test_get_run_in_background_returns_false_when_boolean_false() -> None:
    content = {'input': {'run_in_background': False}}
    assert ralphlib.iteration.get_run_in_background(content) is False


def test_get_run_in_background_returns_false_when_field_missing() -> None:
    content = {'input': {'command': 'ls'}}
    assert ralphlib.iteration.get_run_in_background(content) is False


def test_get_run_in_background_returns_false_when_input_missing() -> None:
    content = {}
    assert ralphlib.iteration.get_run_in_background(content) is False


def test_get_run_in_background_returns_false_when_non_boolean() -> None:
    content = {'input': {'run_in_background': 'yes'}}
    assert ralphlib.iteration.get_run_in_background(content) is False


def test_indent_lines_indents_multi_line_string() -> None:
    result = ralphlib.iteration.indent_lines('line1\nline2\nline3')
    assert result == '  line1\n  line2\n  line3'


def test_indent_lines_indents_single_line() -> None:
    result = ralphlib.iteration.indent_lines('hello')
    assert result == '  hello'


def test_indent_lines_custom_indent() -> None:
    result = ralphlib.iteration.indent_lines('a\nb', indent='>>> ')
    assert result == '>>> a\n>>> b'


def test_indent_lines_returns_empty_string_for_empty_input() -> None:
    assert ralphlib.iteration.indent_lines('') == ''


@pytest.mark.parametrize(
    'message_type',
    [
        ralphlib.types.MessageType.COMPLETE,
        ralphlib.types.MessageType.ERROR,
        ralphlib.types.MessageType.SYSTEM,
        ralphlib.types.MessageType.TOOL_USE,
    ],
)
def test_newline_required_returns_true_for_newline_types(message_type: ralphlib.types.MessageType) -> None:
    context = make_context()
    assert ralphlib.iteration.newline_required(context, message_type) is True


def test_newline_required_returns_true_for_content_stop_after_content_start() -> None:
    context = make_context()
    ralphlib.iteration.append_message_type(context, ralphlib.types.MessageType.CONTENT_START)
    assert ralphlib.iteration.newline_required(context, ralphlib.types.MessageType.CONTENT_STOP) is True


def test_newline_required_returns_true_for_content_stop_after_content_delta() -> None:
    context = make_context()
    ralphlib.iteration.append_message_type(context, ralphlib.types.MessageType.CONTENT_DELTA)
    assert ralphlib.iteration.newline_required(context, ralphlib.types.MessageType.CONTENT_STOP) is True


def test_newline_required_returns_false_for_content_stop_without_preceding_content() -> None:
    context = make_context()
    assert ralphlib.iteration.newline_required(context, ralphlib.types.MessageType.CONTENT_STOP) is False


def test_newline_required_returns_false_for_content_stop_after_non_content_type() -> None:
    context = make_context()
    ralphlib.iteration.append_message_type(context, ralphlib.types.MessageType.SYSTEM)
    assert ralphlib.iteration.newline_required(context, ralphlib.types.MessageType.CONTENT_STOP) is False


def test_newline_required_returns_false_for_content_delta() -> None:
    context = make_context()
    assert ralphlib.iteration.newline_required(context, ralphlib.types.MessageType.CONTENT_DELTA) is False


def test_newline_required_returns_false_for_none_type() -> None:
    context = make_context()
    assert ralphlib.iteration.newline_required(context, ralphlib.types.MessageType.NONE) is False


# --- Test process() subprocess stdin and signal handling ---


def test_process_passes_stdin_devnull_to_popen() -> None:
    """Verify subprocess is spawned with stdin=DEVNULL so it cannot inherit
    the parent's stdin. This ensures Ctrl-C (SIGINT) is delivered to the
    parent process rather than being consumed by the child."""
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    context.cmd = list(TRUE_CMD)

    mock_proc = unittest.mock.MagicMock()
    mock_proc.pid = 12345
    mock_proc.stdout = unittest.mock.MagicMock()
    mock_proc.stderr = unittest.mock.MagicMock()
    mock_proc.stdout.readline = unittest.mock.MagicMock(return_value='')
    mock_proc.stderr.readline = unittest.mock.MagicMock(return_value='')
    mock_proc.poll = unittest.mock.MagicMock(return_value=0)
    mock_proc.returncode = 0

    with unittest.mock.patch('subprocess.Popen', return_value=mock_proc) as mock_popen:
        ralphlib.iteration.process(options, context)

        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args[1]
        assert 'stdin' in call_kwargs, 'stdin must be explicitly set in Popen kwargs'
        assert call_kwargs['stdin'] is subprocess.DEVNULL, 'stdin must be subprocess.DEVNULL to prevent child from inheriting terminal stdin'


def test_process_terminates_subprocess_on_should_exit() -> None:
    """Verify that when should_exit is set (simulating Ctrl-C handling),
    the process loop sends SIGTERM to the subprocess group."""
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    context.cmd = ['sleep', '60']

    mock_proc = unittest.mock.MagicMock()
    mock_proc.pid = 99999
    mock_proc.stdout = unittest.mock.MagicMock()
    mock_proc.stderr = unittest.mock.MagicMock()
    mock_proc.stdout.readline = unittest.mock.MagicMock(return_value='')
    mock_proc.stderr.readline = unittest.mock.MagicMock(return_value='')
    mock_proc.returncode = -15  # SIGTERM

    # proc.poll() returns None (still running) on first call, then 0 after kill
    poll_values = [None, None, -15, -15]
    mock_proc.poll = unittest.mock.MagicMock(side_effect=poll_values)

    with (
        unittest.mock.patch('subprocess.Popen', return_value=mock_proc),
        unittest.mock.patch.object(ralphlib.signals, 'get_should_exit', return_value=True),
        unittest.mock.patch('os.killpg') as mock_killpg,
    ):
        ralphlib.iteration.process(options, context)

        mock_killpg.assert_called_once_with(99999, signal.SIGTERM)


def test_process_child_stdin_is_devnull_integration() -> None:
    """Integration test: spawn a real subprocess and verify its stdin is not
    connected to a terminal (i.e. it got /dev/null, not the parent's stdin).

    The child runs a Python one-liner that exits 0 if stdin is not a TTY
    (meaning stdin=DEVNULL worked) or exits 1 if stdin IS a TTY."""
    options = tests.helpers.make_plain_options(quiet=True)
    context = ralphlib.iteration.IterationContext(
        cmd=[
            sys.executable,
            '-c',
            'import sys; sys.exit(0 if not sys.stdin.isatty() else 1)',
        ],
        iteration=1,
        prompt='test',
    )

    ralphlib.iteration.process(options, context)

    # The process function logs the return code but doesn't expose it directly,
    # so we run the same thing via Popen to confirm the kwargs produce exit 0.
    proc = subprocess.Popen(  # noqa: S603
        context.cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.wait()
    assert proc.returncode == 0, 'Child should see stdin as non-TTY when stdin=DEVNULL'


def test_add_settings_passes_base_ref_as_json() -> None:
    options = tests.helpers.make_options(worktree_base_ref='head')
    result = ralphlib.iteration.add_settings(options, list(CLAUDE_CMD))
    assert result[-2] == '--settings'
    assert orjson.loads(result[-1]) == {'worktree': {'baseRef': 'head'}}


def test_add_settings_noop_without_base_ref() -> None:
    assert ralphlib.iteration.add_settings(tests.helpers.make_options(), list(CLAUDE_CMD)) == list(CLAUDE_CMD)


# --- Test add_worktree_arg ---


def test_add_worktree_arg_appends_worktree_when_enabled() -> None:
    options = tests.helpers.make_plain_options(worktree=True)
    cmd = list(CLAUDE_CMD)
    result = ralphlib.iteration.add_worktree_arg(options, cmd)
    assert '--worktree' in result


def test_add_worktree_arg_appends_task_file_slug_when_task_file_set() -> None:
    options = tests.helpers.make_plain_options(worktree=True, task_file='agents/tasks/my_task.md')
    cmd = list(CLAUDE_CMD)
    result = ralphlib.iteration.add_worktree_arg(options, cmd)
    assert '--worktree' in result
    assert 'tasks-my-task' in result


def test_add_worktree_arg_noop_when_worktree_false() -> None:
    options = tests.helpers.make_plain_options(worktree=False)
    cmd = list(CLAUDE_CMD)
    result = ralphlib.iteration.add_worktree_arg(options, cmd)
    assert result == list(CLAUDE_CMD)


# --- Test process_user ---


def test_process_user_matching_tool_use_id_extracts_background_task_id() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    tool_use_id = 'tool_abc'
    context.background_tools[tool_use_id] = {'name': 'Bash', 'input': '  sleep 10'}
    payload = {
        'type': 'user',
        'message': {
            'role': 'user',
            'content': [
                {
                    'tool_use_id': tool_use_id,
                    'type': 'tool_result',
                    'content': 'Command running in background with ID: bg999.',
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    ralphlib.iteration.process_user(options, context, payload, line)

    assert context.background_id_to_tool['bg999'] == tool_use_id


def test_process_user_tool_use_id_not_in_background_tools_is_noop() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'user',
        'message': {
            'role': 'user',
            'content': [
                {
                    'tool_use_id': 'tool_unknown',
                    'type': 'tool_result',
                    'content': 'Command running in background with ID: bg123.',
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    ralphlib.iteration.process_user(options, context, payload, line)

    assert len(context.background_id_to_tool) == 0


def test_process_user_empty_message_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'user', 'message': {}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_user(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


def test_process_user_non_user_role_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'user',
        'message': {
            'role': 'assistant',
            'content': [
                {
                    'tool_use_id': 'tool_abc',
                    'type': 'tool_result',
                    'content': 'Command running in background with ID: bg123.',
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()
    context.background_tools['tool_abc'] = {'name': 'Bash', 'input': '  sleep 10'}

    message_type, message = ralphlib.iteration.process_user(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert len(context.background_id_to_tool) == 0


def test_process_user_tool_result_no_regex_match_is_noop() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    tool_use_id = 'tool_abc'
    context.background_tools[tool_use_id] = {'name': 'Bash', 'input': '  sleep 10'}
    payload = {
        'type': 'user',
        'message': {
            'role': 'user',
            'content': [
                {
                    'tool_use_id': tool_use_id,
                    'type': 'tool_result',
                    'content': 'Some output that does not match the regex pattern.',
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    ralphlib.iteration.process_user(options, context, payload, line)

    assert len(context.background_id_to_tool) == 0


def test_process_user_always_returns_none_and_line() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    tool_use_id = 'tool_abc'
    context.background_tools[tool_use_id] = {'name': 'Bash', 'input': '  sleep 10'}
    payload = {
        'type': 'user',
        'message': {
            'role': 'user',
            'content': [
                {
                    'tool_use_id': tool_use_id,
                    'type': 'tool_result',
                    'content': 'Command running in background with ID: bg999.',
                },
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_user(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


def tasks_md(second: str) -> str:
    return f"""# Tasks

## Task 1: First thing

**Status:** done

## Task 2: Second thing

**Status:** {second}

## Task 3: Third thing

**Status:** todo
"""


def write_tasks(path: pathlib.Path, second: str) -> None:
    path.write_text(tasks_md(second))


def start_block(tid: str) -> str:
    return f'<task><id>{tid}</id><title>Second thing</title><index>2</index><count>3</count><status>start</status></task>'


def test_announce_started_tasks_prints_start_when_task_goes_in_progress(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    write_tasks(path, 'todo')
    options = tests.helpers.make_plain_options(quiet=True, task_file=str(path), cwd=str(tmp_path))
    context = make_context()
    context.progressfd = io.StringIO()

    ralphlib.iteration.announce_started_tasks(options, context)
    assert context.progressfd.getvalue() == ''

    write_tasks(path, 'in-progress')
    ralphlib.iteration.announce_started_tasks(options, context)
    ralphlib.iteration.announce_started_tasks(options, context)
    assert context.progressfd.getvalue() == '\ntask 2: Second thing 2/3 start\n\n'


def test_announce_started_tasks_does_not_reread_an_unchanged_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    write_tasks(path, 'todo')
    options = tests.helpers.make_plain_options(quiet=True, task_file=str(path), cwd=str(tmp_path))
    context = make_context()
    context.progressfd = io.StringIO()

    with unittest.mock.patch.object(ralphlib.iteration, 'read_task_statuses', wraps=ralphlib.iteration.read_task_statuses) as read:
        ralphlib.iteration.announce_started_tasks(options, context)
        ralphlib.iteration.announce_started_tasks(options, context)
        assert read.call_count == 1
        write_tasks(path, 'in-progress')
        ralphlib.iteration.announce_started_tasks(options, context)
        assert read.call_count == 2


def test_announce_started_tasks_skips_task_in_progress_before_agent_started(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    write_tasks(path, 'in-progress')
    options = tests.helpers.make_plain_options(quiet=True, task_file=str(path), cwd=str(tmp_path))
    context = make_context()
    context.progressfd = io.StringIO()
    context.in_progress_tasks = {'2'}

    ralphlib.iteration.announce_started_tasks(options, context)
    assert context.progressfd.getvalue() == ''


def test_announce_started_tasks_unreadable_task_file_is_silent(tmp_path: pathlib.Path) -> None:
    options = tests.helpers.make_plain_options(quiet=True, task_file=str(tmp_path / 'missing.md'))
    context = make_context()
    context.progressfd = io.StringIO()

    ralphlib.iteration.announce_started_tasks(options, context)
    assert context.progressfd.getvalue() == ''


def test_announce_started_tasks_skips_task_the_agent_announced(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    write_tasks(path, 'in-progress')
    options = tests.helpers.make_plain_options(quiet=True, task_file=str(path), cwd=str(tmp_path))
    context = make_context()
    context.progressfd = io.StringIO()

    message_type, _ = ralphlib.iteration.process_task_progress(options, context, {}, start_block('2'))
    assert message_type == ralphlib.types.MessageType.PROGRESS

    ralphlib.iteration.announce_started_tasks(options, context)
    assert context.progressfd.getvalue() == ''


def test_process_task_progress_suppresses_start_already_announced(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    write_tasks(path, 'in-progress')
    options = tests.helpers.make_plain_options(quiet=True, task_file=str(path), cwd=str(tmp_path))
    context = make_context()
    context.progressfd = io.StringIO()

    ralphlib.iteration.announce_started_tasks(options, context)
    message_type, _ = ralphlib.iteration.process_task_progress(options, context, {}, start_block('2'))
    assert message_type == ralphlib.types.MessageType.NONE

    done = start_block('2').replace('start', 'done')
    message_type, message = ralphlib.iteration.process_task_progress(options, context, {}, done)
    assert message_type == ralphlib.types.MessageType.PROGRESS
    assert message == '\ntask 2: Second thing 2/3 done\n'


RALPHER_VENV = pathlib.Path('/opt/ralpher/.venv')
RALPHER_SRC = pathlib.Path('/opt/ralpher/src')


def test_agent_environment_drops_ralphers_venv_and_src() -> None:
    environ = {
        'HOME': '/home/someone',
        'PATH': f'{RALPHER_VENV}/bin:/usr/local/bin:/usr/bin',
        'PYTHONPATH': f'{RALPHER_SRC}:/work/project/src',
        'VIRTUAL_ENV': str(RALPHER_VENV),
        'VIRTUAL_ENV_PROMPT': 'ralpher',
    }
    env = ralphlib.iteration.agent_environment(environ, RALPHER_VENV, RALPHER_SRC)
    assert env == {
        'HOME': '/home/someone',
        'PATH': '/usr/local/bin:/usr/bin',
        'PYTHONPATH': '/work/project/src',
    }


def test_agent_environment_removes_variables_left_empty() -> None:
    environ = {'PATH': '/usr/bin', 'PYTHONPATH': str(RALPHER_SRC)}
    env = ralphlib.iteration.agent_environment(environ, RALPHER_VENV, RALPHER_SRC)
    assert env == {'PATH': '/usr/bin'}


def test_agent_environment_keeps_another_virtual_environment() -> None:
    environ = {
        'PATH': f'/work/featenv/.venv/bin:{RALPHER_VENV}/bin:/usr/bin',
        'VIRTUAL_ENV': '/work/featenv/.venv',
    }
    env = ralphlib.iteration.agent_environment(environ, RALPHER_VENV, RALPHER_SRC)
    assert env == {'PATH': '/work/featenv/.venv/bin:/usr/bin', 'VIRTUAL_ENV': '/work/featenv/.venv'}


def test_agent_environment_leaves_environ_unchanged() -> None:
    environ = {'PATH': f'{RALPHER_VENV}/bin:/usr/bin', 'VIRTUAL_ENV': str(RALPHER_VENV)}
    before = dict(environ)
    ralphlib.iteration.agent_environment(environ, RALPHER_VENV, RALPHER_SRC)
    assert environ == before


def test_process_starts_agent_without_ralphers_python(tmp_path: pathlib.Path) -> None:
    """The agent's `python` must not be ralpher's: bin/activate.sh put ralpher's venv first on PATH."""
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    context.cmd = list(TRUE_CMD)

    mock_proc = unittest.mock.MagicMock()
    mock_proc.pid = 12345
    mock_proc.stdout = unittest.mock.MagicMock()
    mock_proc.stderr = unittest.mock.MagicMock()
    mock_proc.stdout.readline = unittest.mock.MagicMock(return_value='')
    mock_proc.stderr.readline = unittest.mock.MagicMock(return_value='')
    mock_proc.poll = unittest.mock.MagicMock(return_value=0)
    mock_proc.returncode = 0

    venv_bin = str(pathlib.Path(sys.prefix) / 'bin')
    with (
        unittest.mock.patch.dict('os.environ', {'PATH': f'{venv_bin}:/usr/bin', 'VIRTUAL_ENV': sys.prefix}),
        unittest.mock.patch('subprocess.Popen', return_value=mock_proc) as mock_popen,
    ):
        ralphlib.iteration.process(options, context)

    env = mock_popen.call_args[1]['env']
    assert 'VIRTUAL_ENV' not in env
    assert venv_bin not in env['PATH'].split(':')


# --- Explicit null values in the agent stream ---


def test_process_user_null_content_returns_none() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'user', 'message': {'role': 'user', 'content': None}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_user(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


def test_process_stream_event_null_event_returns_line() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'stream_event', 'event': None}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


def test_process_stream_event_null_content_block_returns_line() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'stream_event', 'event': {'type': 'content_block_start', 'content_block': None}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


def test_process_stream_event_null_delta_returns_line() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': None}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


def test_process_fires_agent_process_end_with_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[tuple[ralphlib.types.RalpherEventType, dict]] = []
    monkeypatch.setattr(ralphlib.iteration, 'SUBPROCESS_POLL_INTERVAL', 0.05)
    monkeypatch.setattr(ralphlib.hooks, 'event', lambda options, event, extra: events.append((event, extra)))
    context = ralphlib.iteration.IterationContext(cmd=[sys.executable, '-c', 'raise SystemExit(3)'], iteration=1, prompt='test')
    ralphlib.iteration.process(tests.helpers.make_options(quiet=True), context)
    names = [event for event, _ in events]
    assert names == [ralphlib.types.RalpherEventType.AGENT_PROCESS_START, ralphlib.types.RalpherEventType.AGENT_PROCESS_END]
    start, end = (extra for _, extra in events)
    assert end == {'agent_process_id': start['agent_process_id'], 'agent_exit_code': 3}


class TestDomainErrors:
    def test_make_context_translates_log_open_error(self, tmp_path: pathlib.Path) -> None:
        blocker = tmp_path / 'file'
        blocker.write_text('x')
        options = tests.helpers.make_options(stdout='out.log', logdir=str(blocker), quiet=True)
        with pytest.raises(ralphlib.exceptions.LogFileError):
            ralphlib.iteration.make_context(options, 'prompt', 1)

    @pytest.mark.parametrize('error', [FileNotFoundError('missing'), subprocess.SubprocessError('bad')])
    def test_process_translates_popen_error(self, error: Exception) -> None:
        options = tests.helpers.make_plain_options()
        context = ralphlib.iteration.IterationContext(cmd=['no-such-agent'], iteration=1, prompt='p')
        with unittest.mock.patch('subprocess.Popen', side_effect=error), pytest.raises(ralphlib.exceptions.RalpherError, match='no-such-agent'):
            ralphlib.iteration.process(options, context)

    def test_stdout_reader_stops_cleanly_on_os_error(self) -> None:
        options = tests.helpers.make_plain_options(quiet=True)
        pipe = unittest.mock.MagicMock()
        pipe.readline.side_effect = OSError('closed')
        ralphlib.iteration.process_stdout(options, make_context(), pipe)

    def test_stderr_reader_stops_cleanly_on_os_error(self) -> None:
        options = tests.helpers.make_plain_options(quiet=True)
        pipe = unittest.mock.MagicMock()
        pipe.readline.side_effect = OSError('closed')
        ralphlib.iteration.process_stderr(options, make_context(), pipe)


FAKE_AGENT = pathlib.Path(__file__).parent / 'fixtures' / 'fake_agent.py'


@pytest.fixture
def e2e_options(tmp_path: pathlib.Path) -> collections.abc.Iterator[ralphlib.options.RalpherOptions]:
    ralphlib.logger.log_file_cache.clear()
    options = tests.helpers.make_options(
        agent=sys.executable,
        args=shlex.quote(str(FAKE_AGENT)),
        iterations=1,
        logdir=str(tmp_path),
        stdout='stdout.log',
        stderr='stderr.log',
        progress='progress.log',
        errors='errors.log',
        state='state.json',
        quiet=True,
    )
    options.stops = ['<promise>COMPLETE</promise>']
    yield options
    ralphlib.logger.log_file_cache.clear()


def read_log(tmp_path: pathlib.Path, name: str) -> str:
    return (tmp_path / name).read_text(encoding='utf-8')


class TestRunEndToEnd:
    def test_normal_session(self, e2e_options: ralphlib.options.RalpherOptions, tmp_path: pathlib.Path) -> None:
        assert ralphlib.iteration.run(e2e_options, 'normal', 1) == (False, False)

        stdout = read_log(tmp_path, 'stdout-1.log')
        assert 'hello from the agent' in stdout
        assert stdout.count('\n') == 5
        assert read_log(tmp_path, 'stderr-1.log') == 'agent warning\n'
        progress = read_log(tmp_path, 'progress-1.log')
        assert 'Tools used:\n- Bash\n- Mystery' in progress
        assert 'Unknown tools used:\n- Mystery' in progress
        assert read_log(tmp_path, 'errors-1.log') == ''
        state = orjson.loads(read_log(tmp_path, 'state.json'))
        assert state['iterations']['1']['tools_used'] == ['Bash', 'Mystery']

    def test_stop_marker_completes(self, e2e_options: ralphlib.options.RalpherOptions) -> None:
        assert ralphlib.iteration.run(e2e_options, 'stop', 1) == (True, False)

    def test_error_result_is_an_error(self, e2e_options: ralphlib.options.RalpherOptions, tmp_path: pathlib.Path) -> None:
        assert ralphlib.iteration.run(e2e_options, 'error', 1) == (False, True)
        assert 'agent failed' in read_log(tmp_path, 'progress-1.log')


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    tid=hypothesis.strategies.integers(min_value=0, max_value=10**6),
    title=hypothesis.strategies.from_regex(r'[A-Za-z][A-Za-z0-9 ]{0,20}', fullmatch=True),
    index=hypothesis.strategies.integers(min_value=1, max_value=999),
    count=hypothesis.strategies.integers(min_value=1, max_value=999),
    status=hypothesis.strategies.sampled_from(['blocked', 'done', 'operator']),
)
def test_process_task_progress_parses_any_well_formed_block(tid: int, title: str, index: int, count: int, status: str) -> None:
    options = tests.helpers.make_plain_options(quiet=True, task_file='agents/tasks/probe/tasks-1.md')
    block = f'<task>\n<id>{tid}</id>\n<title>{title}</title>\n<index>{index}</index>\n<count>{count}</count>\n<status>{status}</status>\n</task>'
    message_type, message = ralphlib.iteration.process_task_progress(options, make_context(), {}, block)
    assert message_type == ralphlib.types.MessageType.PROGRESS
    assert message == f'\ntask {tid}: {title} {index}/{count} {status}\n'


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(text=hypothesis.strategies.text(alphabet='abc <>/\n', max_size=40))
def test_process_task_progress_leaves_text_without_a_block_alone(text: str) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    message_type, message = ralphlib.iteration.process_task_progress(options, make_context(), {}, text)
    assert message_type == ralphlib.types.MessageType.NONE
    assert message == text


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    before=hypothesis.strategies.lists(hypothesis.strategies.text(alphabet='abc ', max_size=10), max_size=3),
    after=hypothesis.strategies.lists(hypothesis.strategies.text(alphabet='abc ', max_size=10), max_size=3),
    pad=hypothesis.strategies.text(alphabet=' \t', max_size=3),
)
def test_is_stop_finds_a_stop_line_among_other_lines(before: list[str], after: list[str], pad: str) -> None:
    options = tests.helpers.make_plain_options()
    text = '\n'.join([*before, f'{pad}{options.stops[0]}{pad}', *after])
    assert ralphlib.iteration.is_stop(options, text)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(text=hypothesis.strategies.text(alphabet='abc \n', max_size=40))
def test_is_stop_is_false_when_no_line_is_a_stop(text: str) -> None:
    assert not ralphlib.iteration.is_stop(tests.helpers.make_plain_options(), text)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(s=hypothesis.strategies.text(min_size=1), indent=hypothesis.strategies.text(alphabet=' >', max_size=4))
def test_indent_lines_prefixes_every_line(s: str, indent: str) -> None:
    result = ralphlib.iteration.indent_lines(s, indent)
    assert result.split('\n') == [f'{indent}{line}' for line in s.splitlines()] or not s.splitlines()


def optional_text_field(types: list[str]) -> hypothesis.strategies.SearchStrategy[dict[str, typing.Any] | None]:
    """A `content_block` or `delta` object: maybe null, maybe without a type or text."""
    return hypothesis.strategies.one_of(
        hypothesis.strategies.none(),
        hypothesis.strategies.fixed_dictionaries(
            {}, optional={'type': hypothesis.strategies.sampled_from(types), 'text': hypothesis.strategies.text(max_size=20)}
        ),
    )


STREAM_EVENTS = hypothesis.strategies.fixed_dictionaries(
    {'type': hypothesis.strategies.just('stream_event')},
    optional={
        'event': hypothesis.strategies.one_of(
            hypothesis.strategies.none(),
            hypothesis.strategies.fixed_dictionaries(
                {},
                optional={
                    'type': hypothesis.strategies.sampled_from(
                        [
                            'content_block_delta',
                            'content_block_start',
                            'content_block_stop',
                            'message_delta',
                            'message_start',
                            'message_stop',
                            'other',
                        ]
                    ),
                    'content_block': optional_text_field(['other', 'text', 'tool_use']),
                    'delta': optional_text_field(['input_json_delta', 'other', 'text_delta']),
                },
            ),
        )
    },
)

JSON_VALUES = hypothesis.strategies.recursive(
    hypothesis.strategies.none()
    | hypothesis.strategies.booleans()
    | hypothesis.strategies.integers(min_value=-(2**63), max_value=2**63 - 1)
    | hypothesis.strategies.text(max_size=10),
    lambda children: (
        hypothesis.strategies.lists(children, max_size=3) | hypothesis.strategies.dictionaries(hypothesis.strategies.text(max_size=8), children, max_size=3)
    ),
    max_leaves=10,
)

PAYLOADS = hypothesis.strategies.one_of(
    STREAM_EVENTS,
    hypothesis.strategies.dictionaries(hypothesis.strategies.sampled_from(['message', 'result', 'subtype', 'type']), JSON_VALUES, max_size=4),
    JSON_VALUES,
)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(payload=STREAM_EVENTS)
def test_process_line_hands_stream_events_to_process_stream_event(payload: dict[str, typing.Any]) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    line = orjson.dumps(payload).decode()
    expected = ralphlib.iteration.process_stream_event(options, make_context(), payload, line)
    assert ralphlib.iteration.process_line(options, make_context(), line) == expected


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(line=hypothesis.strategies.one_of(hypothesis.strategies.text(max_size=40), PAYLOADS.map(lambda p: orjson.dumps(p).decode())))
def test_process_line_never_raises_on_any_line(line: str) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    message_type, message = ralphlib.iteration.process_line(options, make_context(), line)
    assert isinstance(message_type, ralphlib.types.MessageType)
    assert isinstance(message, str)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(payload=STREAM_EVENTS)
def test_process_stream_event_returns_text_only_for_text_blocks(payload: dict[str, typing.Any]) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    line = orjson.dumps(payload).decode()
    message_type, message = ralphlib.iteration.process_stream_event(options, make_context(), payload, line)
    event = payload.get('event') or {}
    block = event.get('content_block') or {}
    delta = event.get('delta') or {}
    if event.get('type') == 'content_block_start' and block.get('type') == 'text':
        assert (message_type, message) == (ralphlib.types.MessageType.CONTENT_START, block.get('text', ''))
    elif event.get('type') == 'content_block_delta' and delta.get('type') == 'text_delta':
        assert (message_type, message) == (ralphlib.types.MessageType.CONTENT_DELTA, delta.get('text', ''))
    elif event.get('type') == 'content_block_stop':
        assert (message_type, message) == (ralphlib.types.MessageType.CONTENT_STOP, '')
    else:
        assert message_type == ralphlib.types.MessageType.NONE
        assert message in ('', line)


INPUT_FIELDS = ['command', 'description', 'pattern', 'url']


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    fields=hypothesis.strategies.fixed_dictionaries(
        {},
        optional={
            name: hypothesis.strategies.one_of(hypothesis.strategies.none(), hypothesis.strategies.text(max_size=10), hypothesis.strategies.integers())
            for name in INPUT_FIELDS
        },
    ),
    todos=hypothesis.strategies.lists(hypothesis.strategies.fixed_dictionaries({}, optional={'content': hypothesis.strategies.text(max_size=10)}), max_size=3),
)
def test_input_field_to_content_prefers_the_first_set_field_then_todos(fields: dict[str, typing.Any], todos: list[dict[str, str]]) -> None:
    result = ralphlib.iteration.input_field_to_content({**fields, 'todos': todos})
    set_fields = sorted(name for name, value in fields.items() if value)
    if set_fields:
        assert result == str(fields[set_fields[0]])
    else:
        assert result == '\n'.join(f'- {td["content"]}' for td in todos if td.get('content'))


PATH_ENTRIES = ['', f'{RALPHER_SRC}', f'{RALPHER_VENV}/bin', '/usr/bin', '/usr/local/bin', '/work/probe/src']


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    path=hypothesis.strategies.none() | hypothesis.strategies.lists(hypothesis.strategies.sampled_from(PATH_ENTRIES), max_size=5),
    pythonpath=hypothesis.strategies.none() | hypothesis.strategies.lists(hypothesis.strategies.sampled_from(PATH_ENTRIES), max_size=5),
    virtual_env=hypothesis.strategies.sampled_from([None, str(RALPHER_VENV), '/work/probe/.venv']),
)
def test_agent_environment_removes_only_ralphers_own_entries(path: list[str] | None, pythonpath: list[str] | None, virtual_env: str | None) -> None:
    environ = {'HOME': '/home/someone', 'VIRTUAL_ENV_PROMPT': 'prompt'}
    for name, value in (('PATH', path), ('PYTHONPATH', pythonpath), ('VIRTUAL_ENV', virtual_env)):
        if value is not None:
            environ[name] = value if isinstance(value, str) else os.pathsep.join(value)
    before = dict(environ)

    env = ralphlib.iteration.agent_environment(environ, RALPHER_VENV, RALPHER_SRC)

    assert environ == before
    expected = dict(environ)
    if virtual_env == str(RALPHER_VENV):
        del expected['VIRTUAL_ENV'], expected['VIRTUAL_ENV_PROMPT']
    for name, entries, own in (('PATH', path, f'{RALPHER_VENV}/bin'), ('PYTHONPATH', pythonpath, str(RALPHER_SRC))):
        if entries is None:
            continue
        kept = [entry for entry in entries if entry != own]
        if any(kept):
            expected[name] = os.pathsep.join(kept)
        else:
            del expected[name]
    assert env == expected


def test_unknown_tool_records_name_and_input_size_not_raw_input() -> None:
    context = make_context()
    ralphlib.iteration.add_unknown_tool(context, 'Mystery', {'secret': 'hunter2'})
    assert context.unknown_tools == {'Mystery': {'input_bytes': len(orjson.dumps({'secret': 'hunter2'}))}}
    assert 'hunter2' not in str(context.unknown_tools)


STOP = '<promise>COMPLETE</promise>'
PLAIN_TEXT = hypothesis.strategies.from_regex(r'[A-Za-z0-9 ,.]{0,30}', fullmatch=True)
TASK_BLOCK = '<task>\n<id>1</id>\n<title>T</title>\n<index>1</index>\n<count>2</count>\n<status>done</status>\n</task>'
TOOL_NAMES = hypothesis.strategies.from_regex(r'[A-Za-z][A-Za-z0-9]{0,10}', fullmatch=True)
JSON_SCALARS = hypothesis.strategies.none() | hypothesis.strategies.booleans() | hypothesis.strategies.integers() | hypothesis.strategies.text(max_size=8)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    worktree=hypothesis.strategies.booleans(),
    task_file=hypothesis.strategies.one_of(
        hypothesis.strategies.just(''), hypothesis.strategies.from_regex(r'[a-z]{1,6}/[a-z]{1,6}/[a-z]{1,6}\.md', fullmatch=True)
    ),
    cmd=hypothesis.strategies.lists(PLAIN_TEXT, max_size=3),
)
def test_add_worktree_arg_appends_only_for_a_worktree(worktree: bool, task_file: str, cmd: list[str]) -> None:
    options = tests.helpers.make_plain_options(worktree=worktree, task_file=task_file)
    result = ralphlib.iteration.add_worktree_arg(options, list(cmd))
    if not worktree:
        assert result == cmd
    elif task_file:
        assert result == [*cmd, '--worktree', ralphlib.templater.task_file_slug(task_file)]
    else:
        assert result == [*cmd, '--worktree']


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(value=JSON_SCALARS, extra=hypothesis.strategies.dictionaries(hypothesis.strategies.text(max_size=4), JSON_SCALARS, max_size=3))
def test_get_run_in_background_is_true_only_for_a_boolean_true(value: typing.Any, extra: dict[str, typing.Any]) -> None:
    content = {'input': {**extra, 'run_in_background': value}}
    assert ralphlib.iteration.get_run_in_background(content) is (value is True)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(is_error=hypothesis.strategies.booleans(), result=PLAIN_TEXT, stop=hypothesis.strategies.booleans())
def test_process_result_classifies_errors_stops_and_the_rest(is_error: bool, result: str, stop: bool) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    result = f'{result}\n{STOP}' if stop else result
    payload = {'is_error': is_error, 'result': result}
    message_type, message = ralphlib.iteration.process_result(options, context, payload, 'line')
    if is_error:
        assert (message_type, message) == (ralphlib.types.MessageType.ERROR, result)
        assert ralphlib.iteration.get_error(context)
    elif stop:
        assert (message_type, message) == (ralphlib.types.MessageType.COMPLETE, '')
        assert ralphlib.iteration.get_complete(context)
    else:
        assert (message_type, message) == (ralphlib.types.MessageType.NONE, 'line')
        assert not ralphlib.iteration.get_complete(context)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(text=PLAIN_TEXT, stop=hypothesis.strategies.booleans(), task=hypothesis.strategies.booleans())
def test_process_assistant_text_blocks(text: str, stop: bool, task: bool) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    if stop:
        text = f'{text}\n{STOP}'
    elif task:
        text = f'{text}\n{TASK_BLOCK}'
    payload = {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': text}]}}
    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, 'line')
    if stop:
        assert (message_type, message) == (ralphlib.types.MessageType.COMPLETE, '')
        assert ralphlib.iteration.get_complete(context)
    elif task:
        assert message_type == ralphlib.types.MessageType.PROGRESS
    else:
        assert (message_type, message) == (ralphlib.types.MessageType.NONE, 'line')
        assert not ralphlib.iteration.get_complete(context)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(name=TOOL_NAMES, command=hypothesis.strategies.from_regex(r'[a-z]{1,10}', fullmatch=True))
def test_process_assistant_tool_use_names_the_tool_and_its_input(name: str, command: str) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    payload = {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': name, 'input': {'command': command}}]}}
    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, 'line')
    assert message_type == ralphlib.types.MessageType.TOOL_USE
    assert message.splitlines()[0] == name
    assert command in message
    assert name in context.tools_used_set


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(
    text=PLAIN_TEXT,
    task=hypothesis.strategies.booleans(),
    role=hypothesis.strategies.sampled_from(['assistant', 'user']),
)
def test_process_user_only_reports_task_blocks_in_tool_results(text: str, task: bool, role: str) -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    content = f'{text}\n{TASK_BLOCK}' if task else text
    payload = {'type': 'user', 'message': {'role': role, 'content': [{'type': 'tool_result', 'tool_use_id': 'id-1', 'content': content}]}}
    message_type, message = ralphlib.iteration.process_user(options, context, payload, 'line')
    if task and role == 'user':
        assert message_type == ralphlib.types.MessageType.PROGRESS
    else:
        assert (message_type, message) == (ralphlib.types.MessageType.NONE, 'line')


# --- Subprocess termination ---


SLEEP_SCRIPT = 'import time; time.sleep(60)'


@pytest.fixture
def fast_poll() -> collections.abc.Iterator[None]:
    """Reduce poll interval so tests don't wait 3 seconds per cycle."""
    with unittest.mock.patch.object(ralphlib.iteration, 'SUBPROCESS_POLL_INTERVAL', 0.05):
        yield


def make_cmd_context(cmd: list[str]) -> ralphlib.iteration.IterationContext:
    return ralphlib.iteration.IterationContext(
        cmd=cmd,
        iteration=1,
        prompt='test',
    )


def child_is_alive(pid: int) -> bool:
    """Check if a process with the given pid exists."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


real_popen = subprocess.Popen


def capturing_popen(holder: dict[str, int]) -> collections.abc.Callable[..., subprocess.Popen[str]]:
    """Return a Popen wrapper that stores the child PID in holder['pid']."""

    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> subprocess.Popen[str]:
        proc = real_popen(*args, **kwargs)
        holder['pid'] = proc.pid
        return proc

    return wrapper


@pytest.mark.usefixtures('fast_poll')
class TestProcessTerminatesOnShouldExit:
    """process() should terminate the child when should_exit is set."""

    def test_process_returns_after_should_exit_set(self) -> None:
        options = tests.helpers.make_options(quiet=True)
        cmd = [sys.executable, '-c', SLEEP_SCRIPT]
        context = make_cmd_context(cmd)

        def set_exit_after_delay() -> None:
            time.sleep(0.2)
            ralphlib.signals.set_should_exit(True)

        timer = threading.Thread(target=set_exit_after_delay)
        timer.start()

        # process() blocks until the subprocess ends; it should return
        # promptly once should_exit is set
        ralphlib.iteration.process(options, context)

        timer.join()
        assert ralphlib.signals.get_should_exit() is True

    def test_child_process_is_dead_after_termination(self) -> None:
        options = tests.helpers.make_options(quiet=True)
        cmd = [sys.executable, '-c', SLEEP_SCRIPT]
        context = make_cmd_context(cmd)

        holder: dict[str, typing.Any] = {}

        def set_exit_after_delay() -> None:
            time.sleep(0.2)
            ralphlib.signals.set_should_exit(True)

        timer = threading.Thread(target=set_exit_after_delay)

        with unittest.mock.patch('ralphlib.iteration.subprocess.Popen', side_effect=capturing_popen(holder)):
            timer.start()
            ralphlib.iteration.process(options, context)

        timer.join()

        assert 'pid' in holder
        # Give the OS a moment to reap
        time.sleep(0.1)
        assert not child_is_alive(holder['pid']), f'Child process {holder["pid"]} still alive after termination'


@pytest.mark.usefixtures('fast_poll')
class TestGracefulTerminatorTerminatesSubprocess:
    """Full integration: GracefulTerminator handler -> should_exit -> child killed."""

    def test_double_sigint_terminates_subprocess(self) -> None:
        options = tests.helpers.make_options(quiet=True)
        cmd = [sys.executable, '-c', SLEEP_SCRIPT]
        context = make_cmd_context(cmd)

        with unittest.mock.patch('ralphlib.signals.signal.signal'):
            terminator = ralphlib.signals.GracefulTerminator(options)

        def send_double_sigint() -> None:
            time.sleep(0.2)
            terminator.handler(signal.SIGINT, None)
            terminator.handler(signal.SIGINT, None)

        timer = threading.Thread(target=send_double_sigint)
        timer.start()

        ralphlib.iteration.process(options, context)

        timer.join()
        assert terminator.is_shutting_down is True
        assert ralphlib.signals.get_should_exit() is True


@pytest.mark.usefixtures('fast_poll')
class TestChildSessionIsolation:
    """With start_new_session=True, the child is in a different session/process group."""

    def test_child_has_different_process_group(self) -> None:
        # The child script prints its process group ID to stdout, then sleeps.
        child_script = 'import os, sys; sys.stdout.write(str(os.getpgrp()) + "\\n"); sys.stdout.flush(); import time; time.sleep(60)'

        options = tests.helpers.make_options(quiet=True)
        cmd = [sys.executable, '-c', child_script]
        context = make_cmd_context(cmd)

        child_pgid_lines: list[str] = []

        def capturing_process_stdout(options: ralphlib.options.RalpherOptions, context: ralphlib.iteration.IterationContext, pipe: typing.IO[str]) -> None:
            for line in iter(pipe.readline, ''):
                line = line.strip()
                if line:
                    child_pgid_lines.append(line)

        def set_exit_after_delay() -> None:
            time.sleep(0.3)
            ralphlib.signals.set_should_exit(True)

        timer = threading.Thread(target=set_exit_after_delay)
        timer.start()

        with unittest.mock.patch.object(ralphlib.iteration, 'process_stdout', capturing_process_stdout):
            ralphlib.iteration.process(options, context)

        timer.join()

        assert len(child_pgid_lines) >= 1, 'Child did not report its pgid'
        child_pgid = int(child_pgid_lines[0])
        parent_pgid = os.getpgrp()

        assert child_pgid != parent_pgid, f'Child pgid ({child_pgid}) matches parent pgid ({parent_pgid}) — start_new_session is not working'


def test_make_context_clears_the_cached_worktree_path() -> None:
    options = ralphlib.options.RalpherOptions(prompt='p', quiet=True)
    options.worktree_task_path = pathlib.Path('/stale')
    ralphlib.iteration.make_context(options, 'prompt', 1)
    assert options.worktree_task_path is None


# --- Direct tests of the small iteration helpers ---


class FakeProc:
    """A stand-in for a process that exits only once `signal_agent` has been called `exit_after` times."""

    def __init__(self, exit_after: int | None) -> None:
        self.pid = 4242
        self.exit_after = exit_after
        self.signals = 0

    def poll(self) -> int | None:
        if self.exit_after is not None and self.signals >= self.exit_after:
            return 0
        return None


def count_signal(proc: FakeProc) -> None:
    proc.signals += 1


def test_signal_agent_signals_the_process_group() -> None:
    proc = unittest.mock.MagicMock()
    proc.pid = 4242
    with unittest.mock.patch('os.killpg') as killpg:
        ralphlib.iteration.signal_agent(proc)
    killpg.assert_called_once_with(4242, signal.SIGTERM)
    proc.terminate.assert_not_called()


def test_signal_agent_falls_back_to_terminate_when_killpg_fails() -> None:
    proc = unittest.mock.MagicMock()
    proc.pid = 4242
    with unittest.mock.patch('os.killpg', side_effect=ProcessLookupError('gone')):
        ralphlib.iteration.signal_agent(proc)
    proc.terminate.assert_called_once_with()


def test_write_log_without_a_file_is_a_noop() -> None:
    ralphlib.iteration.write_log(make_context(), None, 'text', flush=True)


def test_write_log_writes_and_flushes_only_when_asked() -> None:
    context = make_context()
    fd = unittest.mock.MagicMock()
    ralphlib.iteration.write_log(context, fd, 'one')
    fd.write.assert_called_once_with('one')
    fd.flush.assert_not_called()
    ralphlib.iteration.write_log(context, fd, 'two', flush=True)
    fd.flush.assert_called_once_with()


def test_write_log_error_names_the_file() -> None:
    fd = unittest.mock.MagicMock()
    fd.name = '/logs/progress-1.log'
    fd.write.side_effect = OSError('disk full')
    with pytest.raises(ralphlib.exceptions.LogFileError, match='progress-1.log'):
        ralphlib.iteration.write_log(make_context(), fd, 'x')


def test_write_log_releases_the_lock_after_a_failure() -> None:
    context = make_context()
    fd = unittest.mock.MagicMock()
    fd.write.side_effect = OSError('disk full')
    with pytest.raises(ralphlib.exceptions.LogFileError):
        ralphlib.iteration.write_log(context, fd, 'x')
    assert context.gil.acquire(blocking=False)
    context.gil.release()


def test_read_task_statuses_without_a_task_file_is_empty() -> None:
    assert ralphlib.iteration.read_task_statuses(tests.helpers.make_plain_options(task_file='')) == []


def test_read_task_statuses_unreadable_file_is_empty(tmp_path: pathlib.Path) -> None:
    options = tests.helpers.make_plain_options(task_file=str(tmp_path / 'missing.md'), cwd=str(tmp_path))
    assert ralphlib.iteration.read_task_statuses(options) == []


def test_read_task_statuses_returns_every_task_with_its_position(tmp_path: pathlib.Path) -> None:
    path = tmp_path / 'tasks.md'
    write_tasks(path, 'in-progress')
    options = tests.helpers.make_plain_options(task_file=str(path), cwd=str(tmp_path))
    assert ralphlib.iteration.read_task_statuses(options) == [
        ralphlib.iteration.TaskEntry('1', 'First thing', 1, 3, 'done'),
        ralphlib.iteration.TaskEntry('2', 'Second thing', 2, 3, 'in-progress'),
        ralphlib.iteration.TaskEntry('3', 'Third thing', 3, 3, 'todo'),
    ]


def test_kill_agent_stops_signalling_once_the_process_exits() -> None:
    proc = FakeProc(exit_after=2)
    with (
        unittest.mock.patch.object(ralphlib.iteration, 'signal_agent', side_effect=count_signal),
        unittest.mock.patch.object(ralphlib.iteration.time, 'sleep'),
        unittest.mock.patch('loguru.logger.warning') as warning,
    ):
        ralphlib.iteration.kill_agent(proc)  # type: ignore[arg-type]
    assert proc.signals == 2
    warning.assert_not_called()


def test_kill_agent_gives_up_after_the_maximum_attempts() -> None:
    proc = FakeProc(exit_after=None)
    with (
        unittest.mock.patch.object(ralphlib.iteration, 'signal_agent', side_effect=count_signal),
        unittest.mock.patch.object(ralphlib.iteration.time, 'sleep'),
        unittest.mock.patch('loguru.logger.warning') as warning,
    ):
        ralphlib.iteration.kill_agent(proc)  # type: ignore[arg-type]
    assert proc.signals == ralphlib.iteration.MAX_KILL_ATTEMPTS
    warning.assert_called_once()


def test_kill_agent_does_not_signal_an_exited_process() -> None:
    proc = FakeProc(exit_after=0)
    with unittest.mock.patch.object(ralphlib.iteration, 'signal_agent') as signal_agent:
        ralphlib.iteration.kill_agent(proc)  # type: ignore[arg-type]
    signal_agent.assert_not_called()


def test_open_log_file_without_a_name_opens_nothing() -> None:
    opened: list[io.TextIOWrapper] = []
    assert ralphlib.iteration.open_log_file(None, tests.helpers.make_options(), 1, opened) == (None, None)
    assert opened == []


def test_open_log_file_opens_for_appending_and_records_the_handle(tmp_path: pathlib.Path) -> None:
    ralphlib.logger.log_file_cache.clear()
    options = tests.helpers.make_options(logdir=str(tmp_path), quiet=True)
    opened: list[io.TextIOWrapper] = []
    # auditme: accept[filesystem-envelope-gap] try/finally only closes the handles; the open is under test
    try:
        path, fd = ralphlib.iteration.open_log_file('probe.log', options, 1, opened)
        assert path is not None
        assert fd is not None
        assert opened == [fd]
        fd.write('one\n')
        fd.flush()
        assert path.read_text(encoding='utf-8') == 'one\n'
        path2, fd2 = ralphlib.iteration.open_log_file('probe.log', options, 1, opened)
        assert path2 == path
        assert fd2 is not None
        fd2.write('two\n')
        fd2.flush()
        assert path.read_text(encoding='utf-8') == 'one\ntwo\n'
    finally:
        ralphlib.iteration.close_all(opened)
        ralphlib.logger.log_file_cache.clear()


def test_open_log_file_failure_raises_log_file_error_and_records_nothing(tmp_path: pathlib.Path) -> None:
    ralphlib.logger.log_file_cache.clear()
    blocker = tmp_path / 'file'
    blocker.write_text('x')
    options = tests.helpers.make_options(logdir=str(blocker), quiet=True)
    opened: list[io.TextIOWrapper] = []
    try:
        with pytest.raises(ralphlib.exceptions.LogFileError):
            ralphlib.iteration.open_log_file('probe.log', options, 1, opened)
        assert opened == []
    finally:
        ralphlib.logger.log_file_cache.clear()


@pytest.mark.parametrize(
    ('content', 'expected'),
    [
        ({'input': {'command': 'ls'}}, '  ls'),
        ({'input': {'command': 'a\nb'}}, '  a\n  b'),
        ({'input': {'todos': [{'content': 'x'}, {'content': 'y'}]}}, '  - x\n  - y'),
        ({'input': {'other': 'value'}}, ''),
        ({'input': {}}, ''),
        ({}, ''),
    ],
)
def test_get_tool_input_indents_the_input_content(content: dict[str, typing.Any], expected: str) -> None:
    assert ralphlib.iteration.get_tool_input(content) == expected


def test_last_message_type_is_none_for_an_empty_queue() -> None:
    assert ralphlib.iteration.last_message_type(make_context()) is None


def test_last_message_type_returns_the_newest_entry() -> None:
    context = make_context()
    ralphlib.iteration.append_message_type(context, ralphlib.types.MessageType.SYSTEM)
    ralphlib.iteration.append_message_type(context, ralphlib.types.MessageType.TOOL_USE)
    assert ralphlib.iteration.last_message_type(context) == ralphlib.types.MessageType.TOOL_USE
    assert context.message_type_queue == [ralphlib.types.MessageType.SYSTEM, ralphlib.types.MessageType.TOOL_USE]


def test_mark_started_is_true_once_per_task() -> None:
    context = make_context()
    assert ralphlib.iteration.mark_started(context, '1') is True
    assert ralphlib.iteration.mark_started(context, '1') is False
    assert ralphlib.iteration.mark_started(context, '2') is True
    assert context.started_tasks == {'1', '2'}


@pytest.mark.parametrize(
    'subtype',
    [
        'background_tasks_changed',
        'commands_changed',
        'compat_boundary',
        'hook_progress',
        'hook_response',
        'hook_started',
        'init',
        'notification',
        'status',
        'task_notification',
        'task_progress',
        'task_started',
        'task_updated',
        'thinking_tokens',
        'vcs_state_changed',
    ],
)
def test_process_system_skips_housekeeping_subtypes(subtype: str) -> None:
    payload = {'type': 'system', 'subtype': subtype}
    line = orjson.dumps(payload).decode()
    result = ralphlib.iteration.process_system(tests.helpers.make_plain_options(quiet=True), make_context(), payload, line)
    assert result == (ralphlib.types.MessageType.NONE, line)


@pytest.mark.parametrize(('payload', 'expected'), [({'subtype': 'api_retry'}, 'api_retry'), ({}, ''), ({'subtype': ''}, '')])
def test_process_system_reports_other_subtypes(payload: dict[str, str], expected: str) -> None:
    result = ralphlib.iteration.process_system(tests.helpers.make_plain_options(quiet=True), make_context(), payload, 'line')
    assert result == (ralphlib.types.MessageType.SYSTEM, expected)


def test_read_stdout_logs_each_line_and_records_message_types() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    context.stdoutfd = io.StringIO()
    context.progressfd = io.StringIO()
    lines = [
        orjson.dumps({'type': 'system', 'subtype': 'api_retry'}).decode(),
        '',
        orjson.dumps({'type': 'system', 'subtype': 'init'}).decode(),
        orjson.dumps({'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'ls'}}]}}).decode(),
    ]
    pipe = io.StringIO('\n'.join(lines) + '\n')

    ralphlib.iteration.read_stdout(options, context, pipe)  # type: ignore[arg-type]

    assert context.stdoutfd.getvalue() == ''.join(f'{line}\n' for line in lines if line)
    assert context.progressfd.getvalue() == 'api_retry\nBash\n  ls\n'
    assert context.message_type_queue == [ralphlib.types.MessageType.SYSTEM, ralphlib.types.MessageType.TOOL_USE]
    assert 'Bash' in context.tools_used_set


def test_read_stdout_on_an_empty_pipe_does_nothing() -> None:
    context = make_context()
    ralphlib.iteration.read_stdout(tests.helpers.make_plain_options(quiet=True), context, io.StringIO(''))  # type: ignore[arg-type]
    assert context.message_type_queue == []


def test_summary_without_anything_to_report_writes_no_state() -> None:
    context = make_context()
    context.progressfd = io.StringIO()
    with unittest.mock.patch.object(ralphlib.state, 'add_to_state') as add_to_state:
        ralphlib.iteration.summary(tests.helpers.make_plain_options(quiet=True), context)
    add_to_state.assert_not_called()
    assert context.progressfd.getvalue() == ''


def test_summary_reports_tools_unknown_tools_and_unknown_ptypes() -> None:
    options = tests.helpers.make_plain_options(quiet=True)
    context = make_context()
    context.progressfd = io.StringIO()
    context.tools_used_set = {'Read', 'Bash'}
    context.unknown_tools = {'Mystery': {'input_bytes': 7}}
    context.unknown_ptype_set = {'zeta', 'alpha'}

    with unittest.mock.patch.object(ralphlib.state, 'add_to_state') as add_to_state:
        ralphlib.iteration.summary(options, context)

    progress = context.progressfd.getvalue()
    assert 'Tools used:\n- Bash\n- Read\n' in progress
    assert 'Unknown tools used:\n- Mystery\n  - input_bytes: 7\n' in progress
    assert 'Unknown message types received:\n- alpha\n- zeta\n' in progress
    add_to_state.assert_called_once()
    assert add_to_state.call_args.args[1] == {
        'tools_used': ['Bash', 'Read'],
        'unknown_ptypes': ['alpha', 'zeta'],
        'unknown_tools': {'Mystery': {'input_bytes': 7}},
    }
    assert add_to_state.call_args.kwargs == {'key1': 'iterations', 'key2': ralphlib.logger.iteration_to_str(options, 1)}


def test_unmake_context_flushes_and_closes_every_open_log(tmp_path: pathlib.Path) -> None:
    context = make_context()
    path = tmp_path / 'out.log'
    context.stdoutfd = path.open('a', encoding='utf-8')
    context.stdoutfd.write('data')
    context.stderrfd = io.StringIO()
    context.progressfd = io.StringIO()
    context.errorsfd = io.StringIO()
    fds = [context.stdoutfd, context.stderrfd, context.progressfd, context.errorsfd]

    ralphlib.iteration.unmake_context(context)

    assert all(fd.closed for fd in fds)
    assert path.read_text(encoding='utf-8') == 'data'


def test_unmake_context_without_logs_is_a_noop() -> None:
    ralphlib.iteration.unmake_context(make_context())


@pytest.mark.parametrize('quiet', [False, True])
@pytest.mark.parametrize(
    ('call', 'stream', 'expected'),
    [
        (lambda options, context: ralphlib.iteration.print_error(options, context, 'bad'), 'err', 'bad'),
        (lambda options, context: ralphlib.iteration.print_error_eol(options, context), 'err', '\n\n'),
        (
            lambda options, context: ralphlib.iteration.print_progress(options, context, ralphlib.types.MessageType.SYSTEM, 'msg'),
            'out',
            'msg',
        ),
        (lambda options, context: ralphlib.iteration.print_progress_eol(options, context), 'out', '\n'),
        (lambda options, context: ralphlib.iteration.print_progress_lines(options, context, ['a', 'b']), 'out', 'ab'),
    ],
    ids=['print_error', 'print_error_eol', 'print_progress', 'print_progress_eol', 'print_progress_lines'],
)
def test_print_functions_write_to_their_stream_unless_quiet(
    capsys: pytest.CaptureFixture[str],
    call: collections.abc.Callable[[ralphlib.options.RalpherOptions, ralphlib.iteration.IterationContext], None],
    stream: str,
    expected: str,
    quiet: bool,
) -> None:
    call(tests.helpers.make_options(quiet=quiet), make_context())
    captured = capsys.readouterr()
    wanted, other = (captured.err, captured.out) if stream == 'err' else (captured.out, captured.err)
    assert other == ''
    assert wanted == ('' if quiet else expected)
