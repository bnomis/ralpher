import dataclasses
from typing import Annotated

import cappa

import ralphlib.settings


@dataclasses.dataclass
class RalpherOptions:
    """ralpher

    a ralph loop
    """

    agent: Annotated[
        str,
        cappa.Arg(long=True, help='Agent'),
    ] = 'claude'
    args: Annotated[
        str,
        cappa.Arg(long=True, help='Agent args'),
    ] = '--verbose --include-partial-messages --print --dangerously-skip-permissions --output-format stream-json'
    iterations: Annotated[
        int,
        cappa.Arg(long=True, help='Number of iterations to run'),
    ] = 3
    prompt: Annotated[
        str | None,
        cappa.Arg(long=True, help='Read prompt from file'),
    ] = None
    prompts: Annotated[
        str | None,
        cappa.Arg(long=True, help='Prompt as a positional argument, does not override --prompt', value_name='PROMPT'),
    ] = None
    task_file: Annotated[
        str | None,
        cappa.Arg(
            long='--task-file',
            help='Path to tasks file. If --worktree is set, the worktree will be named after the tasks file (without extension)',
        ),
    ] = None
    settings_file: Annotated[
        str | None,
        cappa.Arg(
            long='--settings-file',
            help='Path to settings file. Overrides ~/.ralpher/settings.json',
        ),
    ] = None
    load_settings_on_loop: Annotated[
        bool,
        cappa.Arg(long=True, help='Load settings on each loop iteration'),
    ] = False
    cleanup: Annotated[
        bool,
        cappa.Arg(long=True, help='Print cleanup commands'),
    ] = False
    quiet: Annotated[
        bool,
        cappa.Arg(long=True, help='Suppress output'),
    ] = False
    worktree: Annotated[
        bool,
        cappa.Arg(long=True, help='Use worktrees (add --worktree) named for the tasks file if it exists'),
    ] = False
    skip_git_check: Annotated[
        bool,
        cappa.Arg(long='--skip-git-check', help='Dont do git checks (not committed/pushed etc.) before starting'),
    ] = False
    vars: Annotated[
        list[str],
        cappa.Arg(
            long=True, help='Variables to set, in the form KEY=VALUE. Will be passed as context to jinja2 when rendering prompts. Can be given multiple times.'
        ),
    ] = dataclasses.field(default_factory=list)
    logdir: Annotated[
        str | None,
        cappa.Arg(long=True, help='Directory to prepend to stdout/stderr/progress/state filenames'),
    ] = None
    stdout: Annotated[
        str | None,
        cappa.Arg(long=True, help='Write raw agent stdout to STDOUT file in logdir, iteration numbers are appended to the filename'),
    ] = None
    stderr: Annotated[
        str | None,
        cappa.Arg(long=True, help='Write raw agent stderr to STDERR file in logdir, iteration numbers are appended to the filename'),
    ] = None
    progress: Annotated[
        str | None,
        cappa.Arg(long=True, help='Write parsed agent stdout to PROGRESS file in logdir, iteration numbers are appended to the filename'),
    ] = None
    errors: Annotated[
        str | None,
        cappa.Arg(long=True, help='Write errors to ERRORS file in logdir, iteration numbers are appended to the filename'),
    ] = None
    state: Annotated[
        str | None,
        cappa.Arg(long=True, help='Write ralpher state to JSON STATE file in logdir. Useful for debugging.'),
    ] = None
    cwd: Annotated[
        str | None,
        cappa.Arg(long=True, help='Current working directory for the agent command'),
    ] = None
    stops: Annotated[
        list[str],
        cappa.Arg(
            long=True,
            help='Completion marker strings to look for in agent output to indicate completion. Can be given multiple times. Default: ["&lt;promise&gt;COMPLETE&lt;/promise&gt;"]',
        ),
    ] = dataclasses.field(
        default_factory=lambda: [
            '<promise>COMPLETE</promise>',
        ]
    )
    no_verify_stop: Annotated[
        bool,
        cappa.Arg(
            long='--no-verify-stop',
            help='Trust a stop marker without checking that every task in the tasks file is done',
        ),
    ] = False
    settings: dict = dataclasses.field(init=False, default_factory=dict)
    current_iteration: int = dataclasses.field(init=False, default=0)
    iteration_count: int = dataclasses.field(init=False, default=0)


def parse_options() -> RalpherOptions:
    options: RalpherOptions = cappa.parse(RalpherOptions)
    return ralphlib.settings.load_settings(options)
