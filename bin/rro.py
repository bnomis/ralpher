#!/usr/bin/env python
"""rro: the command-line front end of /rro; every call prints one line of JSON."""

import dataclasses
import pathlib
import sys
import typing

import cappa
import orjson

import ralphlib.exceptions
import ralphlib.order

ERROR_EXIT = 2

Order = typing.Annotated[pathlib.Path, cappa.Arg(help='Path to the order file')]


@dataclasses.dataclass
class Next:
    """Choose the next step of the order"""

    order: Order


@dataclasses.dataclass
class CheckLog:
    """Check the final test log a list saved"""

    order: Order
    label: typing.Annotated[str, cappa.Arg(help="A list's label")]


@dataclasses.dataclass
class SetStatus:
    """Write one row's Status cell"""

    order: Order
    label: typing.Annotated[str, cappa.Arg(help="A list's label, `checkpoint:<n>`, or `Checkpoint after <label>`")]
    status: typing.Annotated[str, cappa.Arg(help='The new status text')]


@dataclasses.dataclass
class SetSetting:
    """Write one setting's Value cell"""

    order: Order
    name: typing.Annotated[str, cappa.Arg(help="A setting's name, such as `progress page`")]
    value: typing.Annotated[str, cappa.Arg(help='The new value')]


@dataclasses.dataclass
class Decisions:
    """List the decided stops since a commit"""

    order: Order
    since: typing.Annotated[str, cappa.Arg(long=True, help='Commit or ref to start after')]


@dataclasses.dataclass
class Rro:
    command: cappa.Subcommands[Next | CheckLog | SetStatus | SetSetting | Decisions]


def row_json(row: ralphlib.order.ListRow | ralphlib.order.CheckpointRow) -> dict[str, typing.Any]:
    kind = 'list' if isinstance(row, ralphlib.order.ListRow) else 'checkpoint'
    return {'type': kind, **dataclasses.asdict(row)}


def step_json(step: ralphlib.order.Step) -> dict[str, typing.Any]:
    match step:
        case ralphlib.order.RunList(row):
            return {'kind': 'run-list', 'row': row_json(row)}
        case ralphlib.order.RunCheckpoint():
            return {'kind': 'run-checkpoint', **dataclasses.asdict(step)}
        case ralphlib.order.Resume(row):
            return {'kind': 'resume', 'row': row_json(row)}
        case _:
            return {'kind': 'finished'}


def read_log_verdict(command: CheckLog, root: pathlib.Path) -> dict[str, typing.Any]:
    order = ralphlib.order.read_order(command.order)
    for row in order.rows:
        if isinstance(row, ralphlib.order.ListRow) and row.label == command.label:
            verdict = ralphlib.order.read_test_log_verdict(order, row, root)
            return {**dataclasses.asdict(verdict), 'path': str(verdict.path)}
    raise ralphlib.exceptions.OrderFormatError(f'{command.order}: no list labelled {command.label!r}')


def run(command: Next | CheckLog | SetStatus | SetSetting | Decisions) -> typing.Any:
    root = ralphlib.order.discover_root(command.order)
    match command:
        case Next():
            return step_json(ralphlib.order.next_step(ralphlib.order.read_order(command.order)))
        case CheckLog():
            return read_log_verdict(command, root)
        case SetStatus():
            ralphlib.order.set_status(command.order, command.label, command.status)
            return {'ok': True}
        case SetSetting():
            ralphlib.order.set_setting(command.order, command.name, command.value)
            return {'ok': True}
        case Decisions():
            return [dataclasses.asdict(d) for d in ralphlib.order.decisions_since(root, command.since)]


def main(argv: list[str] | None = None) -> None:
    args = cappa.parse(Rro, argv=argv)
    try:
        result = run(args.command)
    except ralphlib.exceptions.RalpherError as e:
        sys.stdout.write(orjson.dumps({'error': type(e).__name__, 'message': str(e)}).decode() + '\n')
        sys.exit(ERROR_EXIT)
    sys.stdout.write(orjson.dumps(result).decode() + '\n')


if __name__ == '__main__':
    main()
