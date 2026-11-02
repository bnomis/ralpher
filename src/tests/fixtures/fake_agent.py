"""A fake agent: prints a canned stream-JSON session. The last argument is the mode (the prompt)."""

import json
import sys
import typing


def emit(payload: dict[str, typing.Any]) -> None:
    sys.stdout.write(json.dumps(payload) + '\n')
    sys.stdout.flush()


def main() -> None:
    mode = sys.argv[-1]
    emit({'type': 'system', 'subtype': 'session_started'})
    emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'hello from the agent'}]}})
    emit({'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'ls'}}]}})
    emit({'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Mystery', 'input': {}}]}})
    sys.stderr.write('agent warning\n')
    sys.stderr.flush()
    if mode == 'stop':
        emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '<promise>COMPLETE</promise>'}]}})
    elif mode == 'error':
        emit({'type': 'result', 'is_error': True, 'result': 'agent failed'})
    else:
        emit({'type': 'result', 'is_error': False, 'result': 'done'})


if __name__ == '__main__':
    main()
