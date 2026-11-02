import dataclasses
import pathlib
import shlex
import typing

import cappa

import ralphlib.exceptions
import ralphlib.settings

REFUSED_ARGS = {
    '--settings': "ralpher sets the agent's --settings itself; use --worktree-base-ref or ralpher's settings files",
    '--worktree': 'use ralpher --worktree, which names the worktree for the tasks file',
    '-w': 'use ralpher --worktree, which names the worktree for the tasks file',
}


@dataclasses.dataclass
class RalpherOptions:
    """ralpher

    a ralph loop
    """

    agent: typing.Annotated[
        str,
        cappa.Arg(long=True, help='Agent'),
    ] = 'claude'
    args: typing.Annotated[
        str,
        cappa.Arg(long=True, help='Agent args'),
    ] = '--verbose --include-partial-messages --print --dangerously-skip-permissions --output-format stream-json'
    iterations: typing.Annotated[
        int,
        cappa.Arg(long=True, help='Number of iterations to run'),
    ] = 3
    prompt: typing.Annotated[
        str | None,
        cappa.Arg(long=True, help='Read prompt from file'),
    ] = None
    prompts: typing.Annotated[
        str | None,
        cappa.Arg(long=True, help='Prompt as a positional argument, does not override --prompt', value_name='PROMPT'),
    ] = None
    task_file: typing.Annotated[
        str | None,
        cappa.Arg(
            long='--task-file',
            help='Path to tasks file. If --worktree is set, the worktree will be named after the tasks file (without extension)',
        ),
    ] = None
    settings_file: typing.Annotated[
        str | None,
        cappa.Arg(
            long='--settings-file',
            help='Path to settings file. Overrides ~/.ralpher/settings.json',
        ),
    ] = None
    load_settings_on_loop: typing.Annotated[
        bool,
        cappa.Arg(long=True, help='Load settings on each loop iteration'),
    ] = False
    cleanup: typing.Annotated[
        bool,
        cappa.Arg(long=True, help='Print cleanup commands'),
    ] = False
    quiet: typing.Annotated[
        bool,
        cappa.Arg(long=True, help='Suppress output'),
    ] = False
    worktree: typing.Annotated[
        bool,
        cappa.Arg(long=True, help='Use worktrees (add --worktree) named for the tasks file if it exists'),
    ] = False
    worktree_base_ref: typing.Annotated[
        typing.Literal['fresh', 'head'] | None,
        cappa.Arg(
            long='--worktree-base-ref',
            help='Add worktree.baseRef setting to the cli arguments, i.e. override your default settings. See https://code.claude.com/docs/en/settings-reference#worktree-baseref',
        ),
    ] = None
    skip_git_check: typing.Annotated[
        bool,
        cappa.Arg(long='--skip-git-check', help='Dont do git checks (not committed/pushed etc.) before starting'),
    ] = False
    vars: typing.Annotated[
        list[str],
        cappa.Arg(
            long=True, help='Variables to set, in the form KEY=VALUE. Will be passed as context to jinja2 when rendering prompts. Can be given multiple times.'
        ),
    ] = dataclasses.field(default_factory=list)
    logdir: typing.Annotated[
        str | None,
        cappa.Arg(long=True, help='Directory to prepend to stdout/stderr/progress/state filenames'),
    ] = None
    stdout: typing.Annotated[
        str | None,
        cappa.Arg(long=True, help='Write raw agent stdout to STDOUT file in logdir, iteration numbers are appended to the filename'),
    ] = None
    stderr: typing.Annotated[
        str | None,
        cappa.Arg(long=True, help='Write raw agent stderr to STDERR file in logdir, iteration numbers are appended to the filename'),
    ] = None
    progress: typing.Annotated[
        str | None,
        cappa.Arg(long=True, help='Write parsed agent stdout to PROGRESS file in logdir, iteration numbers are appended to the filename'),
    ] = None
    errors: typing.Annotated[
        str | None,
        cappa.Arg(long=True, help='Write errors to ERRORS file in logdir, iteration numbers are appended to the filename'),
    ] = None
    state: typing.Annotated[
        str | None,
        cappa.Arg(long=True, help='Write ralpher state to JSON STATE file in logdir. Useful for debugging.'),
    ] = None
    cwd: typing.Annotated[
        str | None,
        cappa.Arg(long=True, help='Current working directory for the agent command'),
    ] = None
    stops: typing.Annotated[
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
    no_verify_stop: typing.Annotated[
        bool,
        cappa.Arg(
            long='--no-verify-stop',
            help='Trust a stop marker without checking that every task in the tasks file is done',
        ),
    ] = False
    settings: dict[str, typing.Any] = dataclasses.field(init=False, default_factory=dict)
    """Set at run time by `settings.load_settings`."""
    current_iteration: int = dataclasses.field(init=False, default=0)
    """Set at run time: the iteration in progress."""
    iteration_count: int = dataclasses.field(init=False, default=0)
    """Set at run time: the iterations finished so far."""

    worktree_task_path: pathlib.Path | None = dataclasses.field(init=False, default=None)
    """Set at run time: the tasks file inside the agent's worktree, cached once found and cleared at the start of each iteration."""

    def __post_init__(self) -> None:
        if self.iterations < 1:
            raise ralphlib.exceptions.InvalidIterationsError(f'--iterations must be at least 1, got {self.iterations}')
        try:
            args = shlex.split(self.args)
        except ValueError as e:
            raise ralphlib.exceptions.InvalidArgsError(f'Cannot parse --args {self.args!r} (unbalanced quote?)') from e
        for arg in args:
            flag = arg.split('=', 1)[0] if arg.startswith('--') else arg
            if flag in REFUSED_ARGS:
                raise ralphlib.exceptions.InvalidArgsError(f'--args holds {flag}: {REFUSED_ARGS[flag]}')


def resolve_paths(options: RalpherOptions) -> RalpherOptions:
    """Replace `cwd` and `task_file` with their resolved paths."""
    if options.cwd:
        options.cwd = str(pathlib.Path(options.cwd).resolve().expanduser())
    if options.task_file:
        options.task_file = str(pathlib.Path(options.task_file).resolve().expanduser())
    return options


def load_options() -> RalpherOptions:
    """Parse the command line, resolve `cwd` and `task_file`, and read the settings files."""
    options: RalpherOptions = cappa.parse(RalpherOptions)
    return ralphlib.settings.load_settings(resolve_paths(options))
