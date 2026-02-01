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
        cappa.Arg(long=True, help='Agent command to execute'),
    ] = 'claude --verbose --include-partial-messages --print --dangerously-skip-permissions --output-format stream-json'
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
        cappa.Arg(long=True, help='Variables to set, in the form KEY=VALUE'),
    ] = dataclasses.field(default_factory=list)
    logdir: Annotated[
        str | None,
        cappa.Arg(long=True, help='Log directory, prepended to stdout/stderr/progress filenames'),
    ] = None
    stdout: Annotated[
        str | None,
        cappa.Arg(long=True, help='Write agent raw stdout to file in the logdir, iteration numbers will be appended'),
    ] = None
    stderr: Annotated[
        str | None,
        cappa.Arg(long=True, help='Write agent raw stderr to file in the logdir, iteration numbers will be appended'),
    ] = None
    progress: Annotated[
        str | None,
        cappa.Arg(long=True, help='Write parsed agent progress to file in the logdir, iteration numbers will be appended'),
    ] = None
    cwd: Annotated[
        str | None,
        cappa.Arg(long=True, help='Current working directory for the agent command'),
    ] = None


def parse_options() -> RalpherOptions:
    options: RalpherOptions = cappa.parse(RalpherOptions)
    return options
