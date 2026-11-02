# Prompts

## Giving the prompt

| Option | Use |
|--------|-----|
| `--prompt FILE` | read the prompt from a file |
| `--prompts TEXT` | give the prompt on the command line |

`--prompt` wins when both are given. ralpher exits with an error if the file
is missing or empty, or if neither option gives any text. Leading and
trailing whitespace is stripped.

## Templates

The prompt is a [Jinja](https://jinja.palletsprojects.com/en/stable/templates/)
template, rendered before every iteration. Every value is a string, except
`worktree`, which is a boolean.

| Variable | Value |
|----------|-------|
| `iteration` | this iteration's number, from 1 |
| `iterations` | `--iterations` |
| `task_file` | absolute path of `--task-file`, or empty |
| `task_file_relative_path` | `--task-file` relative to `--cwd` when it is inside it, otherwise absolute; empty without a tasks file |
| `worktree` | `true` with `--worktree` |
| `worktree_name` | the worktree's name, with `--worktree` and `--task-file`; otherwise empty |
| anything from `--vars` | its value |

```jinja
You are on iteration {{ iteration }} of {{ iterations }}.
{% if worktree %}
Work only in the worktree {{ worktree_name }}.
{% endif %}
Read {{ task_file_relative_path }} and do the first task whose status is todo.
```

## `--vars`

```shell
ralpher.sh --prompt PROMPT.md --vars area=parser --vars max_files=5
```

Each `--vars KEY=VALUE` adds a variable; split at the first `=`, so values can
contain `=`. A value with no `=`, or a key that names a built-in variable
(`iteration`, `iterations`, `task_file`, `task_file_relative_path`, `worktree`,
`worktree_name`), stops the run before the `start` hook with an error and exit
status 1.

## Writing a prompt for a loop

Each iteration starts with no memory of the last, so a loop prompt:

- says where the state is: a tasks file, a TODO list, `git log`;
- asks for one unit of work, then an exit, so each iteration is short and
  its context small;
- says exactly when to print the stop marker, on a line of its own, and when
  not to: an agent told only "print COMPLETE when done" may print it after
  its own unit of work;
- asks the agent to commit, so the next iteration, and you, can see what
  happened.

## The bundled one-task prompt

`agents/prompts/one-task.md` in ralpher's checkout is the prompt
[`rrq.sh`](../reference/scripts.md#rrqsh) uses. Per iteration, it tells the
agent to:

1. check the tasks file's integrity: a `done` task with unchecked boxes is
   reopened, and work found in `git log` but not marked is marked;
2. print the stop marker if every task is `done`;
3. pick the first `todo` task whose dependencies are `done`, otherwise the
   first `in-progress` one;
4. stop with an `operator` task block if the task needs a human;
5. announce it with a `start` task block, mark it `in-progress`, implement
   it, run every check the project defines (pre-commit, including the
   `pre-push` stage, and verification scripts), run the tests;
6. mark it `done`, commit with a message starting `Task <n>:`, print a `done`
   task block, and exit.

A task whose tests fail for reasons outside its scope is left `in-progress`,
new tasks are added for the fix, and the agent prints a `blocked` task block.
Copy the prompt and edit it for your own conventions; pass your copy with
`--prompt`.
