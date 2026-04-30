# Run one task

{% if worktree %}

## Worktree rules

Before doing anything remember and follow these **important** rules about worktrees:

- ensure you change working directory to the worktree directory {{ worktree_name }} before starting
- ONLY edit and commit files in the worktree
- DO NOT work in the main branch
- If you cannot find the worktree, exit with an error message
{% endif %}

## Read the tasks file

Read the file {{ task_file }} and identify tasks.
Count the total number of tasks in the file.

Tasks have a status: `todo`, `in-progress`, or `done`.

Task titles have the general form:

```text
## Task <task-number>: <task-name>
```

## Look for `done` tasks with unchecked Subtasks and "Acceptance Criteria"

If any of the `done` tasks have unchecked [ ] Subtasks or "Acceptance Criteria". Check the status of the Subtask or "Acceptance Criteria" by examining the implementation. If the Subtask or "Acceptance Criteria" is implemented mark it as done [x]. If there are any unimplemented Subtasks or "Acceptance Criteria" change the task status to `in-progress`.

## Select a task

Select exactly ONE task to work on: choose the first `todo` task whose dependencies are all `done`. If no task is eligible (all remaining `todo` tasks depend on `in-progress` tasks), choose the first `in-progress` task.

If ALL tasks are `done`, write this completion message this to stdout:

```xml
<promise>COMPLETE</promise>
```

and exit.

## Before implementing the task

To let the user know what you are working on, write the following to stdout:

```xml
<task>
<id>task-number</id>
<title>task-name</title>
<count>tasks-count</count>
<status>start</status>
</task>
```

In the above the variables have the following definitions:

- `task-number`: the number of the current task
- `task-name`: the name of the current task
- `tasks-count`: the total number of tasks in {{ task_file }}

## Implement the chosen task

If the task references a spec section, read the relevant spec before starting implementation.

Implement that single task:

1. Change the task status to `in-progress`
2. Read the existing code the task will modify or interact with
3. Implement the task, following any acceptance criteria listed with it, and following the project wide coding standards defined in AGENTS.md
4. Run `ruff check` and `ruff format` on any new or changed files and fix errors
5. Run tests to verify the implementation
   - If tests fail: fix the issues. If a fix is beyond the scope of this task, add new tasks to {{ task_file }} to address the failures, leave this task as `in-progress`, and stop
   - If tests pass: mark any completed "acceptance criteria" and "subtasks" as done [x]
6. Change the task status to `done`
7. Commit the changes with git using a message that starts with the task number, e.g. "Task 3: add SearchBatch dataclass"

Throughout implementation, print your current status to stdout including: which task you're working on, what actions you're taking, and your reasoning.

## After implementing the task

To let the user know what you've finished the task, write the following to stdout:

```xml
<task>
<id>task-number</id>
<title>task-name</title>
<count>tasks-count</count>
<status>done</status>
</task>
```

The variables have the same definitions as for before implementing a task.

Then check {{ task_file }} for any remaining `todo` or `in-progress` tasks.

If ALL tasks are now `done`, write this completion message this to stdout:

```xml
<promise>COMPLETE</promise>
```

Otherwise, exit without the completion message (another invocation will handle the next task).
