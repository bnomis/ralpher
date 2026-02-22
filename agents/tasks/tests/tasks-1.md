# Test Tasks

Current state: 1 test exists (`test_templater.py` — basic template rendering).
Pytest: 1 passed.

---

## Task 1: Test `looper.timedelta_to_readable` `done`

Pure function with significant branching: zero, negative, sub-second, pluralisation, `show_seconds` flag, multi-unit combinations.

- [x] Zero timedelta returns `'0'`
- [x] Sub-second timedelta (e.g. 500ms) returns `'0'`
- [x] Seconds only (e.g. 45s) — singular and plural
- [x] Minutes and seconds (e.g. 2m 30s)
- [x] Hours, minutes, seconds (e.g. 1h 5m 10s)
- [x] Days, hours, minutes, seconds (e.g. 2d 3h 0m 5s) — includes zero-valued intermediate units
- [x] Negative timedelta produces leading `-`
- [x] `show_seconds=False` suppresses seconds when other units exist
- [x] `show_seconds=False` still shows seconds when it's the only unit
- [x] Exact 1-unit boundaries: exactly 1 day, 1 hour, 1 minute, 1 second — singular forms

Notes: Use `hypothesis` with `st.timedeltas()` for property-based edge-case discovery alongside explicit cases.

---

## Task 2: Test `templater.render` — additional edge cases `done`

Existing test covers basic variable substitution. Gaps remain around missing vars, the auto-injected `iteration` variable, and vars without `=`.

- [x] `iteration` context variable is set to the string of the iteration number
- [x] Var without `=` sign is silently skipped
- [x] Var with multiple `=` signs splits only on first (e.g. `key=val=ue`)
- [x] Empty vars list — only `iteration` is available
- [x] Template referencing undefined variable raises or returns empty (document actual behaviour)

Notes: None.

---

## Task 3: Test `logger` path construction functions `done`

`iteration_to_str`, `log_file`, and `state_file` have path manipulation logic and branching on `logdir`.

- [x] `iteration_to_str` zero-pads based on `options.iterations` width (e.g. iterations=100, iteration=3 → `'003'`)
- [x] `iteration_to_str` with single-digit max (iterations=5, iteration=3 → `'3'`)
- [x] `log_file` constructs correct path with logdir set
- [x] `log_file` constructs correct path without logdir (relative path)
- [x] `log_file` handles filenames with multiple dots (e.g. `output.log.txt`)
- [x] `state_file` returns `None` when `options.state` is not set
- [x] `state_file` prepends logdir when set
- [x] `state_file` returns plain path when logdir is not set
- [x] `log_dir` raises `ValueError` when logdir is not set

Notes: Use `tmp_path` fixture for filesystem assertions where needed.

---

## Task 4: Test `state.add_to_state` / `load_state` / `save_state` `done`

Nested key update logic with 3 branches (no keys, key1, key1+key2) and error cases for non-dict values.

- [x] `add_to_state` with no keys merges into top-level state
- [x] `add_to_state` with `key1` only creates/updates a nested dict
- [x] `add_to_state` with `key1` and `key2` creates/updates a doubly-nested dict
- [x] Sequential `add_to_state` calls accumulate state correctly
- [x] `add_to_state` when `options.state` is None is a no-op
- [x] `ValueNotADict` raised when `key1` path hits a non-dict value
- [x] `ValueNotADict` raised when `key1/key2` path hits a non-dict value
- [x] `load_state` returns empty dict for non-existent file
- [x] `load_state` returns `None` when `options.state` is not set
- [x] `save_state` is a no-op when `options.state` is not set

Notes: Depends on Task 3 (uses `logger.state_file` and `logger.log_file`). Use `tmp_path` fixture for file I/O.

---

## Task 5: Test `iteration.process_line` — JSON dispatch `done`

Top-level dispatcher that parses JSON and routes to sub-processors. Focus on dispatch logic and error handling rather than duplicating sub-processor tests.

- [x] Valid `system` type returns `SYSTEM` message with subtype content
- [x] Valid `assistant` type dispatches correctly (mock `process_assistant`)
- [x] Valid `result` type dispatches correctly (mock `process_result`)
- [x] Valid `user` type dispatches correctly (mock `process_user`)
- [x] Valid `stream_event` type dispatches correctly (mock `process_stream_event`)
- [x] Unknown `ptype` returns `NONE` (and calls `print_error`)
- [x] Invalid JSON returns `ERROR` message type
- [x] Exception during processing returns `ERROR` message type

Notes: Use mocks for the sub-processor functions to keep this test focused on dispatch.

---

## Task 6: Test `iteration.process_result` `done`

Error detection and completion marker detection with branching on `subtype`, `is_error`, and stop markers.

- [x] `subtype='success'` with `is_error=True` sets error flag and returns `ERROR`
- [x] Result containing a stop marker sets complete flag and returns `COMPLETE`
- [x] Result without stop marker and no error returns `NONE`
- [x] Custom stop markers in `options.stops` are respected
- [x] Empty result string returns `NONE`

Notes: None.

---

## Task 7: Test `iteration.process_assistant` `done`

Completion detection via stop markers in text blocks, tool use tracking, and background tool handling.

- [x] Text content containing stop marker sets complete and returns `COMPLETE`
- [x] Text content without stop marker returns `NONE`
- [x] Tool use adds tool name to `tools_used_set`
- [x] Tool use returns `TOOL_USE` with formatted tool name and input
- [x] Tool with `run_in_background=True` in known tools list is tracked in `background_tools`
- [x] Tool with `run_in_background=True` not in known tools list logs warning
- [x] Tool use for a `TaskOutput`/`TaskStop` referencing a known background ID resolves to the original tool info
- [x] Tool use without `name` field logs warning and uses `'UNKNOWN-TOOL'`
- [x] Empty message/content returns `NONE`

Notes: Depends on Task 6 conceptually (shared `IterationContext`), but can be implemented independently.

---

## Task 8: Test `iteration.process_stream_event` `done`

Event type routing for streaming output.

- [x] `message_start`, `message_stop`, `message_delta` return `NONE` with empty string
- [x] `content_block_start` with `type=text` returns `CONTENT_START` with text
- [x] `content_block_start` with `type=tool_use` returns `NONE`
- [x] `content_block_stop` returns `CONTENT_STOP`
- [x] `content_block_delta` with `type=text_delta` returns `CONTENT_DELTA` with text
- [x] `content_block_delta` with `type=input_json_delta` returns `NONE`
- [x] Unknown event type returns `NONE` with original line

Notes: None.

---

## Task 9: Test `iteration` helper functions

Small utility functions with branching logic.

- [ ] `input_field_to_content` returns first matching regular field value
- [ ] `input_field_to_content` returns formatted todos when no regular fields match
- [ ] `input_field_to_content` returns empty string when no fields match
- [ ] `get_run_in_background` returns `True` when `run_in_background` is boolean `True`
- [ ] `get_run_in_background` returns `False` when field is missing or non-boolean
- [ ] `indent_lines` indents multi-line string
- [ ] `indent_lines` returns empty string for empty input
- [ ] `newline_required` returns `True` for `COMPLETE`, `ERROR`, `SYSTEM`, `TOOL_USE`
- [ ] `newline_required` returns `True` for `CONTENT_STOP` after `CONTENT_START` or `CONTENT_DELTA`
- [ ] `newline_required` returns `False` for `CONTENT_STOP` without preceding content type
- [ ] `newline_required` returns `False` for `CONTENT_DELTA`

Notes: None.

---

## Task 10: Test `signals.GracefulTerminator`

State machine with double-press detection, interval window, and SIGTERM handling.

- [ ] First SIGINT sets `first_press` but does not shut down
- [ ] Second SIGINT within interval triggers shutdown and sets `should_exit`
- [ ] Second SIGINT after interval resets (acts like first press again)
- [ ] SIGTERM immediately triggers shutdown
- [ ] Calling handler when `is_shutting_down=True` calls `sys.exit(1)`
- [ ] `set_should_exit` / `get_should_exit` round-trip correctly

Notes: Mock `signal.signal` to avoid modifying real signal handlers. Test the handler method directly rather than sending real signals.

---

## Completion checklist

- [x] No task is so large it should be split further
- [x] Dependencies between tasks are explicitly stated (Task 4 depends on Task 3)
- [x] Existing completed work is marked as done (n/a — no prior task files)
- [x] Task order respects dependency chains
- [x] Prior task files were reviewed to avoid duplicating already-planned work (no prior files exist)
