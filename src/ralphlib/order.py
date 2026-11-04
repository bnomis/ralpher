import dataclasses
import pathlib
import re

import ralphlib.exceptions

SETTINGS_HEADER = ['Setting', 'Value']
# auditme: accept[non-alphabetical-literal] column order is the table's meaning
ORDER_HEADER = ['#', 'Task list', 'Waits for', 'Stops for you', 'Status']
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
    return Order(settings=settings, rows=tuple(rows))


def is_checkpoint(cells: list[str]) -> bool:
    return unquote(cells[1]).replace('*', '').strip().lower() in ('checkpoint', 'final checkpoint')
