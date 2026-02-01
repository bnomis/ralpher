import dataclasses
from typing import Annotated

import cappa


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
        cappa.Arg(help='Prompt as a positional argument, does not override --prompt', value_name='PROMPT'),
    ] = None
    quiet: Annotated[
        bool,
        cappa.Arg(long=True, help='Suppress output'),
    ] = False
    vars: Annotated[
        list[str],
        cappa.Arg(long=True, help='Variables to set, in the form KEY=VALUE. Will be passed as context to jinja2 when rendering prompts.'),
    ] = dataclasses.field(default_factory=list)
    logdir: Annotated[
        str | None,
        cappa.Arg(long=True, help='Directory to prepend to stdout/stderr/progress filenames'),
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
    cwd: Annotated[
        str | None,
        cappa.Arg(long=True, help='Current working directory for the agent command'),
    ] = None


def parse_options() -> RalpherOptions:
    options: RalpherOptions = cappa.parse(RalpherOptions)
    return options
