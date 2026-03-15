---
name: testplan
description: Develop tasks lists to implement tests
when_to_use: Triggers on: test plan, testing gaps, plan tests
allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill]
---

# Task development

Develop unit tests using pytest or property based tests using hypothesis - whichever makes the most sense for the code under test.

Examine the existing tests and source code and produce a list of tasks needed to fill any testing gaps. The goal is not 100% test coverage. Focus on functions with complex logic, edge cases, or that have caused bugs. Skip trivial getters/setters and simple pass-through functions. Focus on functions with branching logic, error handling, and state transitions

Write the task list into a new tasks file in the `@agents/tasks/tests/` folder.

## Tests location

Tests are in the `@src/tests/` directory.

Test files start with `test_`, testing function names start with `test_`.

## Running tests

After activating the environment with the command `source bin/activate.sh`
Run tests with the command `pytest`

## Workflow

1. Read any existing `tasks-*.md` files in `@agents/tasks/tests/` to understand prior work
2. Run pytest to identify current coverage and failures
3. Analyse the source code and existing tests and produce an implementation plan to increase the test coverage
4. Write the new task list into a new file in `@agents/tasks/tests/`

## Task sizing

The plan should consist of small, self-contained tasks. A self-contained task:

- Is a logical unit that can be implemented, tested, and integrated without breaking the system
- Typically corresponds to a single Python module or a focused change across a few files
- Should be completable in a single working session

## Task ordering

Tasks should be in implementation order. Take into account:

- Dependencies between tasks (explicit: "Task 3 depends on Task 1")
- Priority (high-priority tasks first when dependencies allow)
- Complexity (consider front-loading simpler tasks to build momentum)

## File output

Write the implementation plan to `@agents/tasks/tests/tasks-N.md`, where N is an index starting from 1.

If the file already exists DO NOT overwrite it. Instead increment N to create a unique filename (e.g., tasks-2.md, tasks-3.md).

## Task template

```markdown
---

## Task N: Test <module/function>
- [ ] test case 1
- [ ] test case 2
Notes: <any context>

---
```

## Completion checklist

Before finalising the task list, verify:

- [ ] No task is so large it should be split further
- [ ] Dependencies between tasks are explicitly stated
- [ ] Existing completed work is marked as done
- [ ] Task order respects dependency chains
- [ ] Prior task files were reviewed to avoid duplicating already-planned work
