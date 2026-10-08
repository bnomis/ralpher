from hypothesis import given, settings, strategies as st

import ralphlib.verifier

STATUSES = ['todo', 'in-progress', 'done']


def test_headings_with_and_without_status() -> None:
    text = '## Task 1: First\n\n**Status:** todo\n\n## Task 2: Second\n\nno status here\n'
    assert ralphlib.verifier.parse_tasks(text) == [
        ralphlib.verifier.TaskStatus(1, 'First', 'todo'),
        ralphlib.verifier.TaskStatus(2, 'Second', ''),
    ]


def test_status_is_lowercased() -> None:
    tasks = ralphlib.verifier.parse_tasks('## Task 3: T\n**Status:** Done\n')
    assert tasks[0].status == 'done'


def test_first_status_line_wins() -> None:
    tasks = ralphlib.verifier.parse_tasks('## Task 1: T\n**Status:** todo\n**Status:** done\n')
    assert tasks[0].status == 'todo'


def test_status_does_not_leak_to_next_heading() -> None:
    text = '## Task 1: A\n**Status:** done\n## Not a task\n**Status:** todo\n'
    tasks = ralphlib.verifier.parse_tasks(text)
    assert [t.status for t in tasks] == ['done']


def test_fenced_example_is_ignored() -> None:
    text = '```text\n## Task 9: Example\n**Status:** todo\n```\n\n~~~\n## Task 8: Other\n~~~\n\n## Task 1: Real\n**Status:** done\n'
    tasks = ralphlib.verifier.parse_tasks(text)
    assert tasks == [ralphlib.verifier.TaskStatus(1, 'Real', 'done')]


def test_no_headings() -> None:
    assert ralphlib.verifier.parse_tasks('# Title\n\nSome text\n') == []
    assert ralphlib.verifier.parse_tasks('') == []


@settings(max_examples=20, deadline=10000)
@given(
    st.lists(
        st.tuples(
            st.integers(min_value=1, max_value=999),
            st.from_regex(r'[A-Za-z][A-Za-z0-9 ]{0,20}', fullmatch=True),
            st.sampled_from(STATUSES),
        ),
        max_size=10,
    )
)
def test_round_trip(entries: list[tuple[int, str, str]]) -> None:
    text = '# Tasks\n\n' + ''.join(f'## Task {n}: {title}\n\n**Status:** {status}\n**Priority:** high\n\n' for n, title, status in entries)
    tasks = ralphlib.verifier.parse_tasks(text)
    assert [(t.number, t.status) for t in tasks] == [(n, s) for n, _, s in entries]
