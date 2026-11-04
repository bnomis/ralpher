import dataclasses
import pathlib
import re

import ralphlib.exceptions

SETTINGS_HEADER = ['Setting', 'Value']
# auditme: accept[non-alphabetical-literal] column order is the table's meaning
ORDER_HEADER = ['#', 'Task list', 'Waits for', 'Stops for you', 'Status']
IMPLICIT_CHECKPOINT = re.compile(r'^Checkpoint after (\S+): (.+?)\s*$')
TASK_LIST = re.compile(r'^([^/\s]+)/tasks-([^/\s]+)\.md$')
SEPARATOR_CELL = re.compile(r'^:?-+:?$')
DEFAULT_CHECKPOINT_EVERY = 3
DEFAULT_TEST_LOG = 'ralpher-logs/{spec}/tasks-{index}/final-tests.log'
DEFAULT_FAIL_PATTERN = 'FAILED'
REQUIRED_SETTINGS = ('checkpoint command', 'test pass line')
KNOWN_SETTINGS = (
    'always wait for',
    'checkpoint command',
    'checkpoint every',
    'progress page',
    'test fail pattern',
    'test log',
    'test pass line',
)


@dataclasses.dataclass(frozen=True)
class OrderSettings:
    checkpoint_command: str
    checkpoint_every: int
    test_log: str
    pass_line: str
    fail_pattern: str
    wait_rules: tuple[str, ...]
    progress_page: str | None


@dataclasses.dataclass(frozen=True)
class ListRow:
    label: str
    task_list: str
    waits_for: tuple[str, ...]
    stops_for_you: str
    status: str

    @property
    def spec(self) -> str:
        return self.task_list.split('/', 1)[0]

    @property
    def index(self) -> str:
        match = TASK_LIST.match(self.task_list)
        return match.group(2) if match else ''


@dataclasses.dataclass(frozen=True)
class CheckpointRow:
    final: bool
    status: str


@dataclasses.dataclass(frozen=True)
class Order:
    settings: OrderSettings
    rows: tuple[ListRow | CheckpointRow, ...]
    implicit: tuple[tuple[str, str], ...] = ()


@dataclasses.dataclass(frozen=True)
class RunList:
    row: ListRow


@dataclasses.dataclass(frozen=True)
class RunCheckpoint:
    """A checkpoint is due.

    `position` is the index in `Order.rows` of the explicit checkpoint row, or
    of the list row the implicit checkpoint follows; `after` is the label of
    the last list the checkpoint covers.
    """

    position: int
    final: bool
    after: str


@dataclasses.dataclass(frozen=True)
class Resume:
    row: ListRow | CheckpointRow


@dataclasses.dataclass(frozen=True)
class Finished:
    pass


Step = RunList | RunCheckpoint | Resume | Finished


def split_cells(line: str) -> list[str]:
    body = line.strip()
    body = body.removeprefix('|').removesuffix('|')
    return [cell.strip().replace('\\|', '|') for cell in re.split(r'(?<!\\)\|', body)]


def unquote(value: str) -> str:
    return value.replace('`', '').strip()


def find_root(path: pathlib.Path) -> pathlib.Path:
    """The nearest directory above the order file that holds `agents/tasks/`.

    Raises:
        OrderFormatError: no ancestor directory holds `agents/tasks/`.
    """
    for parent in path.resolve().parents:
        if (parent / 'agents' / 'tasks').is_dir():
            return parent
    raise ralphlib.exceptions.OrderFormatError(f'{path}: no agents/tasks/ directory above the order file')


def build_settings(values: dict[str, str], lines: dict[str, int], header_line: int, path: pathlib.Path) -> OrderSettings:
    for name in REQUIRED_SETTINGS:
        if not values.get(name):
            raise ralphlib.exceptions.OrderFormatError(f'{path}:{header_line}: missing required setting `{name}`')
    every = DEFAULT_CHECKPOINT_EVERY
    if values.get('checkpoint every'):
        text = values['checkpoint every']
        if not text.isascii() or not text.isdigit() or int(text) < 1:
            raise ralphlib.exceptions.OrderFormatError(f'{path}:{lines["checkpoint every"]}: `checkpoint every` must be a positive integer, got {text!r}')
        every = int(text)
    rules = tuple(rule.strip() for rule in values.get('always wait for', '').split(',') if rule.strip())
    return OrderSettings(
        checkpoint_command=values['checkpoint command'],
        checkpoint_every=every,
        test_log=values.get('test log') or DEFAULT_TEST_LOG,
        pass_line=values['test pass line'],
        fail_pattern=values.get('test fail pattern') or DEFAULT_FAIL_PATTERN,
        wait_rules=rules,
        progress_page=values.get('progress page') or None,
    )


def read_order(path: pathlib.Path) -> Order:
    """Parse an order file.

    Raises:
        OrderFormatError: naming the line, on any fault in the file.
    """
    text = path.read_text(encoding='utf-8')
    root = find_root(path)
    values: dict[str, str] = {}
    lines: dict[str, int] = {}
    settings_line = 0
    order_line = 0
    mode = ''
    raw_rows: list[tuple[int, list[str]]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith('|'):
            mode = ''
            continue
        cells = split_cells(line)
        if cells == SETTINGS_HEADER:
            if settings_line:
                raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: second settings table')
            mode, settings_line = 'settings', number
            continue
        if cells == ORDER_HEADER:
            if order_line:
                raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: second order table')
            mode, order_line = 'order', number
            continue
        if all(SEPARATOR_CELL.match(cell) for cell in cells):
            continue
        if mode == 'settings':
            name = cells[0]
            if len(cells) != len(SETTINGS_HEADER):
                raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: settings row needs two cells')
            if name not in KNOWN_SETTINGS:
                raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: unknown setting `{name}`')
            values[name] = unquote(cells[1])
            lines[name] = number
        elif mode == 'order':
            if len(cells) != len(ORDER_HEADER):
                raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: order row needs {len(ORDER_HEADER)} cells, found {len(cells)}')
            raw_rows.append((number, cells))
    if not settings_line:
        raise ralphlib.exceptions.OrderFormatError(f'{path}: no settings table (header `Setting | Value`)')
    if not order_line:
        raise ralphlib.exceptions.OrderFormatError(f'{path}: no order table')
    settings = build_settings(values, lines, settings_line, path)
    labels: set[str] = set()
    for number, cells in raw_rows:
        label = cells[0]
        if is_checkpoint(cells):
            continue
        if not label or re.search(r'\s', label):
            raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: label {label!r} is empty or has spaces')
        if label in labels:
            raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: duplicate label `{label}`')
        labels.add(label)
    rows: list[ListRow | CheckpointRow] = []
    for number, cells in raw_rows:
        if is_checkpoint(cells):
            rows.append(CheckpointRow(final='final' in unquote(cells[1]).lower(), status=cells[4]))
            continue
        task_list = unquote(cells[1])
        if not TASK_LIST.match(task_list):
            raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: task list {task_list!r} is not of the form <spec>/tasks-<index>.md')
        if not (root / 'agents' / 'tasks' / task_list).is_file():
            raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: task list {task_list!r} does not exist under agents/tasks/')
        waits = () if cells[2] in ('', '-') else tuple(part.strip() for part in cells[2].split(','))
        for wait in waits:
            if wait not in labels:
                raise ralphlib.exceptions.OrderFormatError(f'{path}:{number}: `Waits for` label `{wait}` is not in the table')
        rows.append(ListRow(cells[0], task_list, waits, cells[3], cells[4]))
    implicit = tuple((match.group(1), match.group(2)) for line in text.splitlines() if (match := IMPLICIT_CHECKPOINT.match(line.strip())))
    return Order(settings=settings, rows=tuple(rows), implicit=implicit)


def is_checkpoint(cells: list[str]) -> bool:
    return unquote(cells[1]).replace('*', '').strip().lower() in ('checkpoint', 'final checkpoint')


def is_merged(row: ListRow | CheckpointRow) -> bool:
    return row.status.startswith('merged')


def is_open(status: str) -> bool:
    return status == 'running' or status.startswith(('failed', 'waiting:'))


def next_step(order: Order) -> Step:
    """The first row not yet merged or passed, in table order.

    Raises:
        WaitsForUnmetError: the next list waits for a list that is not merged.
    """
    lists = [row for row in order.rows if isinstance(row, ListRow)]
    explicit = len(lists) != len(order.rows)
    implicit = dict(order.implicit)
    merged = {row.label for row in lists if is_merged(row)}
    since_checkpoint = 0
    last_label = ''
    for position, row in enumerate(order.rows):
        if isinstance(row, CheckpointRow):
            if row.status.startswith('passed'):
                continue
            if is_open(row.status):
                return Resume(row)
            return RunCheckpoint(position, row.final, last_label)
        last_label = row.label
        if is_open(row.status):
            return Resume(row)
        if not is_merged(row):
            for label in row.waits_for:
                if label not in merged:
                    raise ralphlib.exceptions.WaitsForUnmetError(f'list {row.label} waits for list {label}, which is not merged')
            return RunList(row)
        if explicit:
            continue
        since_checkpoint += 1
        final = row is lists[-1]
        if since_checkpoint < order.settings.checkpoint_every and not final:
            continue
        status = implicit.get(row.label, 'todo')
        if status.startswith('passed'):
            since_checkpoint = 0
            continue
        if is_open(status):
            return Resume(CheckpointRow(final=final, status=status))
        return RunCheckpoint(position, final, row.label)
    return Finished()
