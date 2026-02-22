from unittest.mock import patch

import orjson

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
