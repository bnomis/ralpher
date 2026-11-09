import dataclasses
import pathlib
import re

import git

import ralphlib.exceptions

SETTINGS_HEADER = ['Setting', 'Value']
# auditme: accept[non-alphabetical-literal] column order is the table's meaning
ORDER_HEADER = ['#', 'Task list', 'Waits for', 'Stops for you', 'Status']
IMPLICIT_CHECKPOINT = re.compile(r'^Checkpoint after (\S+): (.+?)\s*$')
TASK_LIST = re.compile(r'^([^/\s]+)/tasks-([^/\s]+)\.md$')
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
UNESCAPED_BAR = re.compile(r'(?<!\\)\|')
SEPARATOR_CELL = re.compile(r'^:?-+:?$')
DEFAULT_CHECKPOINT_EVERY = 3
DEFAULT_TEST_LOG = 'ralpher-logs/{spec}/tasks-{index}/final-tests.log'
DEFAULT_BRANCH = 'main'
DEFAULT_FAIL_PATTERN = 'FAILED'
DECISION_TRAILER = 'Queue-decision'
DECISION_LINE = re.compile(f'^{DECISION_TRAILER}:(.*)$', re.MULTILINE)
FIELD_SEPARATOR = '\x1f'
RECORD_SEPARATOR = '\x1e'
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
    label: str
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

    `label` is the exact label `set_status` takes for this checkpoint:
    `checkpoint:<n>` for an explicit row, `Checkpoint after <label>` for an
    implicit one. `position` is the index in `Order.rows` of the explicit
    checkpoint row, or of the list row the implicit checkpoint follows; `after`
    is the label of the last list the checkpoint covers.
    """

    label: str
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
    checkpoints = 0
    for number, cells in raw_rows:
        if is_checkpoint(cells):
            checkpoints += 1
            rows.append(CheckpointRow(label=f'checkpoint:{checkpoints}', final='final' in unquote(cells[1]).lower(), status=cells[4]))
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
            return RunCheckpoint(row.label, position, row.final, last_label)
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
        every = order.settings.checkpoint_every
        left = len(lists) - position - 1
        if not final and (since_checkpoint < every or left < every):
            continue
        status = implicit.get(row.label, 'todo')
        if status.startswith('passed'):
            since_checkpoint = 0
            continue
        label = f'Checkpoint after {row.label}'
        if is_open(status):
            return Resume(CheckpointRow(label=label, final=final, status=status))
        return RunCheckpoint(label, position, final, row.label)
    return Finished()


@dataclasses.dataclass(frozen=True)
class LogVerdict:
    passed: bool
    path: pathlib.Path
    fail_lines: tuple[str, ...]
    has_pass_line: bool


def check_test_log(order: Order, row: ListRow, root: pathlib.Path) -> LogVerdict:
    """Judge the final test log a list saved: it passes with its pass line and no fail match."""
    path = root / order.settings.test_log.format(spec=row.spec, index=row.index)
    if not path.is_file():
        return LogVerdict(passed=False, path=path, fail_lines=(), has_pass_line=False)
    fail = re.compile(order.settings.fail_pattern)
    lines = [ANSI_ESCAPE.sub('', line) for line in path.read_text(encoding='utf-8', errors='replace').splitlines()]
    has_pass_line = any(order.settings.pass_line in line for line in lines)
    fail_lines = tuple(line for line in lines if fail.search(line))
    return LogVerdict(passed=has_pass_line and not fail_lines, path=path, fail_lines=fail_lines, has_pass_line=has_pass_line)


def replace_cell(line: str, index: int, text: str) -> str:
    """Replace the text of one table cell, keeping its padding and every other byte."""
    bars = [m.start() for m in UNESCAPED_BAR.finditer(line)]
    start, end = bars[index] + 1, bars[index + 1]
    cell = line[start:end]
    lead = cell[: len(cell) - len(cell.lstrip())] or ' '
    trail = cell[len(cell.rstrip()) :] or ' '
    escaped = text.replace('|', '\\|')
    return f'{line[:start]}{lead}{escaped}{trail}{line[end:]}'


def strip_ending(line: str) -> tuple[str, str]:
    body = line.rstrip('\r\n')
    return body, line[len(body) :]


def set_status(path: pathlib.Path, label: str, status: str) -> None:
    """Rewrite one Status cell, leaving every other byte of the file unchanged.

    `label` is a list's label; `checkpoint:<n>` for the nth checkpoint row in
    the table; or `Checkpoint after <label>` for an implicit checkpoint's line,
    which is added below the order table the first time it is set.

    Raises:
        OrderFormatError: no row or line has that label.
    """
    lines = path.read_bytes().decode('utf-8').splitlines(keepends=True)
    nth = 0
    in_order = False
    last_table_line = -1
    target = -1
    for number, line in enumerate(lines):
        body, ending = strip_ending(line)
        if not body.lstrip().startswith('|'):
            in_order = False
            match = IMPLICIT_CHECKPOINT.match(body.strip())
            if match and label == f'Checkpoint after {match.group(1)}':
                lines[number] = f'{label}: {status}{ending}'
                path.write_bytes(''.join(lines).encode('utf-8'))
                return
            continue
        cells = split_cells(body)
        if cells == ORDER_HEADER:
            in_order = True
            continue
        if not in_order or all(SEPARATOR_CELL.match(cell) for cell in cells):
            continue
        last_table_line = number
        if len(cells) != len(ORDER_HEADER):
            continue
        if is_checkpoint(cells):
            nth += 1
            if label == f'checkpoint:{nth}':
                target = number
        elif cells[0] == label:
            target = number
    if target >= 0:
        body, ending = strip_ending(lines[target])
        lines[target] = replace_cell(body, 4, status) + ending
    elif label.startswith('Checkpoint after ') and last_table_line >= 0:
        body, ending = strip_ending(lines[last_table_line])
        ending = ending or '\n'
        lines[last_table_line] = body + ending
        lines.insert(last_table_line + 1, f'{ending}{label}: {status}{ending}')
    else:
        raise ralphlib.exceptions.OrderFormatError(f'{path}: no row labelled {label!r}')
    path.write_bytes(''.join(lines).encode('utf-8'))


def set_setting(path: pathlib.Path, name: str, value: str) -> None:
    """Rewrite one setting's Value cell in place, leaving every other byte unchanged.

    A known setting with no row is added as the last row of the settings
    table. Raises OrderFormatError for an unknown name, and for a value that
    makes the file fail read_order, in which case the file is left as it was.
    """
    if name not in KNOWN_SETTINGS:
        raise ralphlib.exceptions.OrderFormatError(f'{path}: unknown setting `{name}`')
    original = path.read_bytes()
    lines = original.decode('utf-8').splitlines(keepends=True)
    in_settings = False
    last_table_line = -1
    target = -1
    for number, line in enumerate(lines):
        body, _ = strip_ending(line)
        if not body.lstrip().startswith('|'):
            in_settings = False
            continue
        cells = split_cells(body)
        if cells == SETTINGS_HEADER:
            in_settings = True
            last_table_line = number
            continue
        if not in_settings:
            continue
        last_table_line = number
        if cells[0] == name and len(cells) == len(SETTINGS_HEADER):
            target = number
    if target >= 0:
        body, ending = strip_ending(lines[target])
        lines[target] = replace_cell(body, 1, value) + ending
    elif last_table_line >= 0:
        body, ending = strip_ending(lines[last_table_line])
        ending = ending or '\n'
        lines[last_table_line] = body + ending
        escaped = value.replace('|', '\\|')
        lines.insert(last_table_line + 1, f'| {name} | {escaped} |{ending}')
    else:
        raise ralphlib.exceptions.OrderFormatError(f'{path}: no settings table (header `Setting | Value`)')
    path.write_bytes(''.join(lines).encode('utf-8'))
    try:
        read_order(path)
    except ralphlib.exceptions.OrderFormatError:
        path.write_bytes(original)
        raise


@dataclasses.dataclass(frozen=True)
class Decision:
    commit: str
    date: str
    subject: str
    body: str
    task: str


def default_branch(repo: git.Repo) -> str:
    """The branch origin/HEAD points at, or main when it is unset."""
    try:
        return repo.git.symbolic_ref('--short', 'refs/remotes/origin/HEAD').removeprefix('origin/')
    except git.GitCommandError:
        return DEFAULT_BRANCH


def decisions_since(root: pathlib.Path, ref: str) -> list[Decision]:
    """Commits on the default branch since ref with a Queue-decision line, oldest first.

    The value is read from every such line in the message, wherever it sits: git parses
    trailers only in the last paragraph, and a line above it is still a decided stop.

    Raises:
        GitError: root is not a repository or ref does not resolve.
    """
    try:
        repo = git.Repo(root)
        repo.git.rev_parse('--verify', '--quiet', f'{ref}^{{commit}}')
    except git.GitError as e:
        raise ralphlib.exceptions.GitError(f'Cannot resolve {ref} in {root}') from e
    # auditme: accept[legacy-formatting-percent] git log placeholders, not Python formatting
    fields = ('%H', '%as', '%s', '%b', '%B')
    text = repo.git.log(
        '--reverse',
        f'--format={FIELD_SEPARATOR.join(fields)}{RECORD_SEPARATOR}',
        f'--grep=^{DECISION_TRAILER}:',
        f'{ref}..{default_branch(repo)}',
    )
    decisions = []
    for record in text.split(RECORD_SEPARATOR):
        if not record.strip():
            continue
        commit, date, subject, body, message = record.strip('\n').split(FIELD_SEPARATOR)
        task = ', '.join(value.strip() for value in DECISION_LINE.findall(message))
        decisions.append(Decision(commit=commit, date=date, subject=subject, body=body.strip(), task=task))
    return decisions
