from unittest.mock import patch

import orjson
import pytest

import ralphlib.iteration
import ralphlib.options
import ralphlib.types


def make_context() -> ralphlib.iteration.IterationContext:
    return ralphlib.iteration.IterationContext(
        cmd=[],
        iteration=1,
        prompt='test',
    )


def make_options(**kwargs) -> ralphlib.options.RalpherOptions:
    return ralphlib.options.RalpherOptions(**kwargs)


def test_process_line_system_type() -> None:
    options = make_options(quiet=True)
    context = make_context()
    line = orjson.dumps({'type': 'system', 'subtype': 'init'}).decode()
    message_type, message = ralphlib.iteration.process_line(options, context, line)
    assert message_type == ralphlib.types.MessageType.SYSTEM
    assert message == 'init'


def test_process_line_assistant_dispatches() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'assistant', 'message': {'content': []}}
    line = orjson.dumps(payload).decode()
    expected = (ralphlib.types.MessageType.TOOL_USE, 'mocked')

    with patch.object(ralphlib.iteration, 'process_assistant', return_value=expected) as mock_fn:
        result = ralphlib.iteration.process_line(options, context, line)
        mock_fn.assert_called_once()
        assert result == expected


def test_process_line_result_dispatches() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'result': 'ok'}
    line = orjson.dumps(payload).decode()
    expected = (ralphlib.types.MessageType.NONE, line)

    with patch.object(ralphlib.iteration, 'process_result', return_value=expected) as mock_fn:
        result = ralphlib.iteration.process_line(options, context, line)
        mock_fn.assert_called_once()
        assert result == expected


def test_process_line_user_dispatches() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'user', 'message': {}}
    line = orjson.dumps(payload).decode()
    expected = (ralphlib.types.MessageType.NONE, line)

    with patch.object(ralphlib.iteration, 'process_user', return_value=expected) as mock_fn:
        result = ralphlib.iteration.process_line(options, context, line)
        mock_fn.assert_called_once()
        assert result == expected


def test_process_line_stream_event_dispatches() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'stream_event', 'event': {'type': 'message_start'}}
    line = orjson.dumps(payload).decode()
    expected = (ralphlib.types.MessageType.NONE, '')

    with patch.object(ralphlib.iteration, 'process_stream_event', return_value=expected) as mock_fn:
        result = ralphlib.iteration.process_line(options, context, line)
        mock_fn.assert_called_once()
        assert result == expected


def test_process_line_unknown_ptype_returns_none() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'unknown_type'}
    line = orjson.dumps(payload).decode()

    with patch.object(ralphlib.iteration, 'print_error') as mock_print_error:
        message_type, message = ralphlib.iteration.process_line(options, context, line)
        assert message_type == ralphlib.types.MessageType.NONE
        assert message == line
        mock_print_error.assert_called_once()


def test_process_line_invalid_json_returns_error() -> None:
    options = make_options(quiet=True)
    context = make_context()
    line = 'this is not json'
    message_type, message = ralphlib.iteration.process_line(options, context, line)
    assert message_type == ralphlib.types.MessageType.ERROR
    assert message == line


def test_process_line_exception_returns_error() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'assistant'}
    line = orjson.dumps(payload).decode()

    with patch.object(
        ralphlib.iteration,
        'process_assistant',
        side_effect=RuntimeError('boom'),
    ):
        message_type, message = ralphlib.iteration.process_line(options, context, line)
        assert message_type == ralphlib.types.MessageType.ERROR
        assert message == line


def test_process_result_success_with_is_error_sets_error_flag() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'is_error': True, 'result': 'something failed'}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.ERROR
    assert message == 'something failed'
    assert ralphlib.iteration.get_error(context) is True


def test_process_result_with_stop_marker_sets_complete() -> None:
    options = make_options(quiet=True)
    context = make_context()
    result_text = 'output with <promise>COMPLETE</promise> marker'
    payload = {'type': 'result', 'subtype': 'success', 'result': result_text}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.COMPLETE
    assert message == ''
    assert ralphlib.iteration.get_complete(context) is True


def test_process_result_no_stop_marker_no_error_returns_none() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'result': 'normal output'}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line
    assert ralphlib.iteration.get_complete(context) is False
    assert ralphlib.iteration.get_error(context) is False


def test_process_result_custom_stop_markers_respected() -> None:
    options = make_options(quiet=True, stops=['DONE', 'FINISHED'])
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'result': 'task is FINISHED now'}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.COMPLETE
    assert message == ''
    assert ralphlib.iteration.get_complete(context) is True


def test_process_result_empty_result_returns_none() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'result', 'subtype': 'success', 'result': ''}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_result(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


# --- Task 7: Test process_assistant ---


def test_process_assistant_text_with_stop_marker_sets_complete() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {
        'type': 'assistant',
        'message': {
            'content': [
                {'type': 'text', 'text': 'output with <promise>COMPLETE</promise> marker'},
            ],
        },
    }
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.COMPLETE
    assert message == ''
    assert ralphlib.iteration.get_complete(context) is True


def test_process_assistant_text_without_stop_marker_returns_none() -> None:
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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

    with patch('loguru.logger.warning') as mock_warning:
        ralphlib.iteration.process_assistant(options, context, payload, line)
        mock_warning.assert_called()
        warning_msg = mock_warning.call_args[0][0]
        assert 'UnknownTool' in warning_msg
        assert 'not in known background tools list' in warning_msg

    assert 'tool_xyz' not in context.background_tools


def test_process_assistant_task_output_resolves_background_tool() -> None:
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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

    with patch('loguru.logger.warning') as mock_warning:
        message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)
        mock_warning.assert_called()

    assert message_type == ralphlib.types.MessageType.TOOL_USE
    assert 'UNKNOWN-TOOL' in message
    assert 'UNKNOWN-TOOL' in context.tools_used_set


def test_process_assistant_empty_message_returns_none() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'assistant', 'message': {}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


def test_process_assistant_empty_content_returns_none() -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'assistant', 'message': {'content': []}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_assistant(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == line


# --- Task 8: Test process_stream_event ---


@pytest.mark.parametrize('event_type', ['message_start', 'message_stop', 'message_delta'])
def test_process_stream_event_message_types_return_none(event_type: str) -> None:
    options = make_options(quiet=True)
    context = make_context()
    payload = {'type': 'stream_event', 'event': {'type': event_type}}
    line = orjson.dumps(payload).decode()

    message_type, message = ralphlib.iteration.process_stream_event(options, context, payload, line)

    assert message_type == ralphlib.types.MessageType.NONE
    assert message == ''


def test_process_stream_event_content_block_start_text_returns_content_start() -> None:
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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
    options = make_options(quiet=True)
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
