import datetime
import functools
import os
import pathlib
import sys
from typing import TYPE_CHECKING

import loguru

import ralphlib.giter
import ralphlib.hooks
import ralphlib.iteration
import ralphlib.logger
import ralphlib.printer
import ralphlib.settings
import ralphlib.signals
import ralphlib.state
import ralphlib.templater
import ralphlib.types
import ralphlib.verifier

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


def loop(options: RalpherOptions) -> bool:
    _terminator = ralphlib.signals.GracefulTerminator(options)

    if options.cwd:
        cwd_path = pathlib.Path(options.cwd).resolve().expanduser()
        options.cwd = str(cwd_path)
        os.chdir(options.cwd)

    # check git status
    ralphlib.giter.check_git(options)

    # check prompt file exists and has content
    content = ''
    if options.prompt:
        if not os.path.isfile(options.prompt):
            sys.exit(f'Error: Prompt file "{options.prompt}" does not exist.')

        with open(options.prompt, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            sys.exit(f'Error: Prompt file "{options.prompt}" is empty.')

    elif options.prompts:
        content = options.prompts.strip()
        if not content:
            sys.exit('Error: Prompts provided via --prompts is empty.')

    content = content.strip()
    if not content:
        sys.exit('Error: No prompt provided. Use --prompt to read from a file or --prompts to provide on the cmd line.')

    # check task file exists and has content
    task_path = None
    if options.task_file:
        task_path = pathlib.Path(options.task_file).resolve().expanduser()
        if not task_path.is_file():
            sys.exit(f'Error: Task file "{options.task_file}" does not exist.')
        with open(task_path, 'r', encoding='utf-8') as f:
            task_content = f.read().strip()
        if not task_content:
            sys.exit(f'Error: Task file "{options.task_file}" is empty.')
        options.task_file = str(task_path)

    ralphlib.logger.init(options)

    start = datetime.datetime.now()
    now = start.isoformat()

    ralphlib.printer.prt(options, f'\n\n{"-" * 80}\n\n', 0)
    ralphlib.printer.prt(options, f'Start at {now}\n\n', 0)
    ralphlib.printer.prt(options, f'Agent:\n{options.agent}\n\n', 0)
    ralphlib.printer.prt(options, f'Args:\n{options.args}\n\n', 0)
    ralphlib.printer.prt(options, f'Prompt:\n{content}\n\n', 0)
    ralphlib.printer.prt(options, f'Iterations: {options.iterations}\n\n', 0)

    # hook
    ralphlib.hooks.event(
        options,
        event_type=ralphlib.types.RalpherEventType.START,
        event_context={'iteration': 0, 'prompt': content},
    )

    # state json
    new_state = {
        'start': now,
        'agent': options.agent,
        'args': options.args,
        'prompt': content,
        'max_iterations': options.iterations,
    }
    ralphlib.state.add_to_state(options, new_state)

    loop_times = []
    loop_tds = []
    exit_reason = 'completed all iterations'
    complete = error = termination = False

    for i in range(1, options.iterations + 1):
        if options.load_settings_on_loop:
            options = ralphlib.settings.load_settings(options)

        options.current_iteration = i
        loop_start = datetime.datetime.now()
        now = loop_start.isoformat()

        print_both(options, f'\n\n{"-" * 80}\n\n', i)
        p = ralphlib.templater.render(options, content, i)
        s = f'\nStarting iteration {i}/{options.iterations} at {now}\n\nPrompt:\n\n{p}\n\n'
        print_both(options, s, i)

        # state json
        iterations_key = ralphlib.logger.iteration_to_str(options, i)
        state_payload = {
            'start': loop_start.isoformat(),
        }
        ralphlib.state.add_to_state(options, state_payload, key1='iterations', key2=iterations_key)

        # hook
        ralphlib.hooks.event(
            options,
            event_type=ralphlib.types.RalpherEventType.ITERATION_START,
            event_context={'iteration': i, 'prompt': p},
        )

        # run the iteration
        try:
            complete, error = ralphlib.iteration.run(options, prompt=p, iteration=i)
        except Exception as e:
            loguru.logger.exception(f'Exception during iteration {i}: {e}')
            s = f'\nException during iteration {i}\n'
            ralphlib.printer.prt(options, s, 0)
            ralphlib.printer.prt(options, s, i)
            break

        loop_end = datetime.datetime.now()
        now = loop_end.isoformat()
        loop_td = loop_end - loop_start
        loop_tds.append(loop_td)
        options.iteration_count = i

        s = f'\nEnding iteration {i}/{options.iterations} at {now}\n'
        print_both(options, s, i)

        loop_time_str = timedelta_to_readable(loop_td)
        loop_times.append(loop_time_str)
        s = f'Time for iteration {i}: {loop_time_str}\n\n'
        print_both(options, s, i)
        print_both(options, f'\n\n{"-" * 80}\n\n', i)

        # state json
        state_payload = {
            'end': loop_end.isoformat(),
            'iteration_time_readable': loop_time_str,
            'iteration_time_seconds': loop_td.total_seconds(),
        }
        ralphlib.state.add_to_state(options, state_payload, key1='iterations', key2=iterations_key)

        # hook
        ralphlib.hooks.event(
            options,
            event_type=ralphlib.types.RalpherEventType.ITERATION_END,
            event_context={
                'iteration': i,
                'iteration_time_readable': loop_time_str,
                'iteration_time_seconds': loop_td.total_seconds(),
            },
        )

        if complete and options.task_file and not options.no_verify_stop and not error:
            complete = reject_unverified_stop(options, i, iterations_key)

        if complete or error or ralphlib.signals.get_should_exit():
            words = []
            message_type = ralphlib.types.MessageType.SYSTEM
            if complete:
                words.append('complete')
            if error:
                words.append('error')
                message_type = ralphlib.types.MessageType.ERROR
            if ralphlib.signals.get_should_exit():
                words.append('termination')
                termination = True
            exit_reason = ', '.join(words)

            s = f'\n{"=" * 5} Loop {exit_reason} signal received, stopping after {i} iteration{"s" if i != 1 else ""}. {"=" * 5}\n\n'
            print_both(options, s, i, message_type=message_type)
            break

    ralphlib.printer.prt(options, '\n\nLoop times\n\n', 0)
    num_loops = len(loop_times)
    num_loops_str_len = len(str(num_loops))
    for i, loop_time_str in enumerate(loop_times, start=1):
        s = f'{i:>{num_loops_str_len}}: {loop_time_str}\n'
        ralphlib.printer.prt(options, s, 0)

    end = datetime.datetime.now()
    now = end.isoformat()

    td = end - start
    readable = timedelta_to_readable(td)

    total_loop_time_td = functools.reduce(lambda acc, td: acc + td, loop_tds, datetime.timedelta(0))
    readable_loop_time = timedelta_to_readable(total_loop_time_td)
    ralpher_overhead_td = td - total_loop_time_td
    if ralpher_overhead_td.total_seconds() < 1:
        readable_overhead_time = 'none'
    else:
        readable_overhead_time = timedelta_to_readable(ralpher_overhead_td)
        if readable_overhead_time == '0':
            readable_overhead_time = 'none'

    ralphlib.printer.prt(options, f'\n\nEnd at {now}\n', 0)
    lines = [f'Total time: {readable}']
    if task_path:
        lines.append(f'tasks file: {task_path}')
    if readable_overhead_time != 'none':
        lines.append(f'loop time: {readable_loop_time}')
        lines.append(f'overhead: {readable_overhead_time}')

    lines.append(f'Exit reason: {exit_reason}')
    ralphlib.printer.prt(options, f'{"\n".join(lines)}\n', 0)

    # state json
    new_state = {
        'end': now,
        'exit_reason': exit_reason,
        'iterations_completed': num_loops,
        'total_time_readable': readable,
        'total_time_seconds': td.total_seconds(),
        'loop_time_readable': readable_loop_time,
        'loop_time_seconds': total_loop_time_td.total_seconds(),
        'overhead_time_readable': readable_overhead_time,
        'overhead_time_seconds': ralpher_overhead_td.total_seconds(),
    }
    ralphlib.state.add_to_state(options, new_state)

    # hook
    if error:
        ralphlib.hooks.event(
            options,
            event_type=ralphlib.types.RalpherEventType.ERROR,
            event_context={
                'iteration': 0,
                'exit_reason': exit_reason,
                'iterations_completed': num_loops,
                'total_time_readable': readable,
                'total_time_seconds': td.total_seconds(),
            },
        )

    ralphlib.hooks.event(
        options,
        event_type=ralphlib.types.RalpherEventType.END,
        event_context={
            'iteration': 0,
            'exit_reason': exit_reason,
            'iterations_completed': num_loops,
            'total_time_readable': readable,
            'total_time_seconds': td.total_seconds(),
        },
    )

    if complete and not (bool(error) or termination):
        print_cleanup_cmds(options)

    return bool(error) or termination


def reject_unverified_stop(options: RalpherOptions, iteration: int, iterations_key: str) -> bool:
    """Check a stop signal against the tasks file; return whether the loop should still stop."""
    check = ralphlib.verifier.check_stop(options)
    if not check.verified:
        loguru.logger.warning(f'Cannot verify stop signal, trusting it: {check.reason}')
        return True
    if check.all_done:
        return True

    lines = [f'\n{"=" * 5} Loop complete signal rejected, {len(check.not_done)} of {check.total} tasks not done {"=" * 5}']
    lines.extend(f'  Task {t.number}: {t.title} ({t.status or "no status"})' for t in check.not_done)
    print_both(options, '\n'.join(lines) + '\n\n', iteration, message_type=ralphlib.types.MessageType.SYSTEM)

    state_payload = {'stop_rejected': {'total': check.total, 'not_done': [t.number for t in check.not_done]}}
    ralphlib.state.add_to_state(options, state_payload, key1='iterations', key2=iterations_key)
    return False


def print_cleanup_cmds(options: RalpherOptions) -> None:
    cmds = cleanup_cmds(options)
    if cmds:
        lines = ['Probable cleanup commands...']
        lines.append(' && \\\n'.join([f'  {c}' for c in cmds]))
        ralphlib.printer.prt(options, f'{"\n".join(lines)}\n', 0)


def cleanup_cmds(options: RalpherOptions) -> list[str]:
    cmds = []
    if options.worktree and options.task_file:
        worktree = ralphlib.templater.task_file_slug(options.task_file)
        branch = f'worktree-{worktree}'
        cmds = [f'git merge --no-ff --no-edit {branch}']
        cmds.append(f'(git worktree unlock {worktree} 2>/dev/null || true)')
        cmds.append(f'git worktree remove --force {worktree}')
        cmds.append(f'git branch -d {branch}')
        cmds.append('git push')
    return cmds


def print_both(
    options: RalpherOptions,
    s: str,
    iteration: int,
    message_type: ralphlib.types.MessageType = ralphlib.types.MessageType.REGULAR,
) -> None:
    ralphlib.printer.prt(options, s, 0, message_type=message_type)
    ralphlib.printer.prt(options, s, iteration, dont_print=True, message_type=message_type)


def timedelta_to_readable(td: datetime.timedelta, show_seconds: bool = True) -> str:
    if td == datetime.timedelta(0):
        return '0'

    total_seconds = int(td.total_seconds())
    if total_seconds == 0:
        return '0'

    # Handle negative durations
    sign = '-' if total_seconds < 0 else ''
    total_seconds = abs(total_seconds)

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f'{days} day{"s" if days != 1 else ""}')
    if hours or days:  # show hours if there are days
        parts.append(f'{hours} hour{"s" if hours != 1 else ""}')
    if minutes or hours or days:
        parts.append(f'{minutes} minute{"s" if minutes != 1 else ""}')
    if show_seconds or not parts:  # always show seconds if nothing else
        parts.append(f'{seconds} second{"s" if seconds != 1 else ""}')

    return sign + ' '.join(parts)
