# Run one task

You will work on exactly one task and then exit. Do not loop.

{% if worktree %}

## Worktree rules

Before doing anything, remember and follow these rules:

- If you cannot find the worktree, exit with an error message
- ensure you change working directory to the worktree directory {{ worktree_name }} before starting
- ONLY edit and commit files in the worktree
- ONLY read/modify/commit the tasks file in the worktree
{% endif %}

## Read the tasks file

Read the tasks file {{ task_file_relative_path }}{% if worktree %} in the worktree{% endif %} and identify tasks.
Count the total number of tasks in the file.

Tasks have a status: `todo`, `in-progress`, or `done`.

Task titles have the general form:

```text
## Task <task-number>: <task-name>
```

## Confirm task file integrity

Before you do any work, check the integrity of the tasks file{% if worktree %} in the worktree{% endif %} by following the steps below.

### Check for `done` tasks with unchecked [ ] Subtasks or "Acceptance Criteria"

For all the `done` tasks in the tasks file, look for unchecked [ ] Subtasks or "Acceptance Criteria";
check the implementation status of the unchecked Subtasks or "Acceptance Criteria" by examining the implementation.
If any unchecked Subtasks or "Acceptance Criteria" are implemented, mark them as done [x] in the tasks file.
If there are any unimplemented Subtasks or "Acceptance Criteria", change the task status to `in-progress`.

### Check for done tasks without `done` status

Use `git log`{% if worktree %} in the worktree{% endif %} to check which tasks have been `done`.

If the `git log` `done` tasks do not have `done` status in the tasks file,
check the implementation to verify the status of the task and its Subtasks and "Acceptance Criteria".

Mark all implementation complete but unchecked Subtasks and "Acceptance Criteria" as done [x].

If everything in the task, Subtasks, and "Acceptance Criteria" is complete, change the task status to `done`.
Otherwise, change the task status to `in-progress`.

## Select a task

If ALL tasks are `done`, write this message to stdout on a new line with nothing else on the line:

```xml
<promise>COMPLETE</promise>
```

and exit.

Otherwise, select exactly ONE task to work on: choose the first `todo` task whose dependencies are all `done`.

If no task is eligible (all remaining `todo` tasks depend on `in-progress` tasks), choose the first `in-progress` task.

If the chosen task needs operator/human input before it can run, e.g. an answer to a question, write the following task block (see [task blocks](#task-blocks) below) to stdout:

```xml
<task>
<id>task-number</id>
<title>task-name</title>
<index>task-index</index>
<count>tasks-count</count>
<status>operator</status>
</task>
```

and exit.

## `<task>` blocks

Let the user know what you are working on by writing `<task>` blocks to your standard out. Do not use `bash printf` or `bash echo` - actually write to your standard out from your process.

`<task>` blocks have the form below:

```xml
<task>
<id>task-number</id>
<title>task-name</title>
<index>task-index</index>
<count>tasks-count</count>
<status>start|done|blocked|operator</status>
</task>
```

In the above the variables have the following definitions:

- `task-number`: the number of the current task
- `task-name`: the name of the current task
- `task-index`: the index, starting from 1, of the current task in {{ task_file_relative_path }}
- `tasks-count`: the total number of tasks in {{ task_file_relative_path }}
- `status`: one of `start`, `done`, `blocked`, or `operator`

## Implement the selected task

1. To let the user know what you are working on, write a `<task>` block to stdout with `<status>start</status>`.
2. If the selected task references a spec, read the relevant spec before starting implementation.
3. Change the task status to `in-progress` in {{ task_file_relative_path }}{% if worktree %} in the worktree{% endif %}.
4. Read any existing code the task will modify or interact with.
5. Implement the task, following any acceptance criteria listed with it, and following the project wide coding standards defined in AGENTS.md.
6. Run every check the project defines on the new or changed files, and fix
   what they report. Read the set from the repository rather than assuming it -
   a check you do not name is a check that does not run:
   - `.pre-commit-config.yaml`: run `pre-commit run --all-files`, and run it
     again with `--hook-stage pre-push` if any hook declares
     `stages: [pre-push]`. Those hooks do not fire on a commit, so nothing in
     this loop reaches them otherwise.
   - any verification script under `bin/`, `scripts/` or `tools/`, especially a
     whole-tree audit or duplication check - the hits it finds are cross-file,
     so this task is the first point at which they can be seen at all.
   Treat every hit as blocking. Reading a check's output and continuing past it
   leaves the finding for whoever merges the branch, by which time nobody holds
   the context that would fix it cheaply. Fix it, or record the deliberate
   exception the project's own convention provides, before step 8.
7. Run tests to verify the implementation
   - If tests fail and the fix is in scope: fix the issues, re-run, repeat
     until tests pass.
   - If tests fail and the fix is beyond the scope of this task: add new
     tasks to {{ task_file_relative_path }}, leave this task as `in-progress`, write a
     `<task>` block with `<status>blocked</status>`, and exit.
   - Once tests pass: mark completed "acceptance criteria" and "subtasks"
     as done [x], then continue to step 8.
8. Change the task status to `done` in {{ task_file_relative_path }}{% if worktree %} in the worktree{% endif %}.
9. Commit the changes with git{% if worktree %} in the worktree{% endif %} using a message that starts with the task number, e.g. "Task 3: add SearchBatch dataclass".

Throughout implementation, print your current status to stdout including: which task you're working on, what actions you're taking, and your reasoning.

## Finish and exit

To let the user know what you've finished the task, write a `<task>` block to stdout with `<status>done</status>`.

### Check for more `todo` or `in-progress` tasks

Check {{ task_file_relative_path }}{% if worktree %} in the worktree{% endif %} for tasks with status `todo` or `in-progress`.

If there are tasks with status `todo` or `in-progress`,
DO NOT start a new task, EXIT now.

### Check for all tasks done

If ALL tasks are `done`, write this message to stdout on a new line with nothing else on the line:

```xml
<promise>COMPLETE</promise>
```

and exit.
