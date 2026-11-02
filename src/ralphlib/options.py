import dataclasses
import pathlib
import shlex
import typing

import cappa

import ralphlib.settings


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
    current_iteration: int = dataclasses.field(init=False, default=0)
    iteration_count: int = dataclasses.field(init=False, default=0)

    passed_worktree_base_ref: str | None = dataclasses.field(init=False, default=None)
    """`--worktree-base-ref`, unless `--args` holds its own `--settings`, which then wins."""
    worktree_task_path: pathlib.Path | None = dataclasses.field(init=False, default=None)
    """The tasks file inside the agent's worktree, cached once found; cleared at the start of each iteration."""

    def __post_init__(self) -> None:
        args = shlex.split(self.args)
        if '--settings' not in args:
            self.passed_worktree_base_ref = self.worktree_base_ref

    def args_override_warnings(self) -> list[str]:
        """Describe each ralpher option that a flag in `--args` overrides."""
        args = shlex.split(self.args)
        warnings = []
        if self.worktree and ('--worktree' in args or '-w' in args):
            warnings.append('--args holds --worktree/-w: it wins, and ralpher adds no worktree name')
        if self.worktree_base_ref and '--settings' in args:
            warnings.append('--args holds --settings: it wins, and --worktree-base-ref is not passed')
        return warnings


def parse_options() -> RalpherOptions:
    options: RalpherOptions = cappa.parse(RalpherOptions)
    return ralphlib.settings.load_settings(options)
