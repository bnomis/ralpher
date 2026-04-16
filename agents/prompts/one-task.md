Read the file {{ task_file }} and identify tasks. Tasks have a status: `todo`, `in-progress`, or `done`. Count the total number of tasks in the file.

Select exactly ONE task to work on: choose the first `todo` task whose dependencies are all `done`. If no task is eligible (all remaining `todo` tasks depend on `in-progress` tasks), stop and report which tasks are blocked and why.

Task titles have the general form:

```text
## Task <task-number>: <task-name>
```

To let the user know what you are working on, write the following to stdout:

```xml
<task>
<id>task-number</id>
<title>task-name</title>
<count>tasks-count</count>
</task>
```

In the above the variables have the following definitions:

- `task-number`: the number of the current task
- `task-name`: the name of the current task
- `tasks-count`: the total number of tasks in {{ task_file }}

If the task references a spec section, read the relevant spec before starting implementation.

Implement that single task:

1. Change its status to `in-progress`
2. Read the existing code that the task will modify or interact with
3. Implement the task, following any acceptance criteria listed with it, and following the project wide coding standards defined in @AGENTS.md
4. Run `ruff check` and `ruff format` on any new or changed files and fix errors
5. Run tests to verify the implementation
   - If tests fail: fix the issues. If a fix is beyond the scope of this task, add new tasks to {{ task_file }} to address the failures, leave this task as `in-progress`, and stop
   - If tests pass: mark any completed "acceptance criteria" and "subtasks" as done [x]
6. Change the task status to `done`
7. Commit the changes with git using a message that starts with the task number, e.g. "Task 3: add SearchBatch dataclass"

Throughout execution, print your current status to stdout: which task you're working on, what actions you're taking, and your reasoning.

After completing the task, check {{ task_file }} for any remaining `todo` or `in-progress` tasks.

If ALL tasks are now `done`, write exactly this to stdout:

```xml
<promise>COMPLETE</promise>
```

Otherwise, exit without the completion message (another invocation will handle the next task).
