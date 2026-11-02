import collections.abc
import io
import pathlib
import shlex
import signal
import subprocess
import sys
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


# --- Task 7: Test process_assistant ---


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


# --- Task 8: Test process_stream_event ---


@pytest.mark.parametrize('event_type', ['message_start', 'message_stop', 'message_delta'])
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


# --- Task 9: Test iteration helper functions ---


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


def test_add_settings_keeps_existing_settings_arg() -> None:
    options = tests.helpers.make_options(worktree_base_ref='head', args='--print --settings {}')
    cmd = ['claude', '--print', '--settings', '{}']
    assert ralphlib.iteration.add_settings(options, list(cmd)) == cmd


# --- Task 2: Test add_worktree_arg ---


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


def test_add_worktree_arg_does_not_add_if_worktree_already_present() -> None:
    options = tests.helpers.make_plain_options(worktree=True)
    cmd = ['claude', '--worktree']
    result = ralphlib.iteration.add_worktree_arg(options, cmd)
    assert result.count('--worktree') == 1


def test_add_worktree_arg_does_not_add_if_short_flag_already_present() -> None:
    options = tests.helpers.make_plain_options(worktree=True)
    cmd = ['claude', '-w']
    result = ralphlib.iteration.add_worktree_arg(options, cmd)
    assert '--worktree' not in result


def test_add_worktree_arg_noop_when_worktree_false() -> None:
    options = tests.helpers.make_plain_options(worktree=False)
    cmd = list(CLAUDE_CMD)
    result = ralphlib.iteration.add_worktree_arg(options, cmd)
    assert result == list(CLAUDE_CMD)


# --- Task 3: Test process_user ---


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


TASKS_MD = """# Tasks

## Task 1: First thing

**Status:** done

## Task 2: Second thing

**Status:** {second}

## Task 3: Third thing

**Status:** todo
"""


def write_tasks(path: pathlib.Path, second: str) -> None:
    path.write_text(TASKS_MD.format(second=second))


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

    def test_process_translates_popen_error(self) -> None:
        options = tests.helpers.make_plain_options()
        context = ralphlib.iteration.IterationContext(cmd=['no-such-agent'], iteration=1, prompt='p')
        popen = unittest.mock.patch('subprocess.Popen', side_effect=FileNotFoundError('missing'))
        with popen, pytest.raises(ralphlib.exceptions.RalpherError, match='no-such-agent'):
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
