---
name: testplan
description: Analyse source code and tests to produce a plan for filling testing gaps
when_to_use: |
    Use this skill whenever the user mentions:
        - test plan
        - testing gaps
        - plan tests
allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill]
---

# Test plan development

Invoke as:
    /testplan [scope]

Where `[scope]` is an optional argument specifying what to plan tests for. If no argument is provided, plan tests for the entire project.

Scope examples:

- `/testplan` -- full test plan (all source modules)
- `/testplan src/<project>/<file>.py` -- test plan for a single module
- `/testplan <spec>` -- test plan for a spec and its implementation

## Goals

Develop unit tests using pytest or property-based tests using hypothesis — whichever makes the most sense for the code under test.

The goal is not 100% test coverage. Focus on:

- Functions with branching logic, error handling, or state transitions
- Edge cases and boundary conditions
- Code that has caused bugs

Skip trivial getters/setters and simple pass-through functions.

## Workflow

### 1. Establish scope

- **Full plan** (no argument): analyse all source modules under `src/` and their tests under `src/tests/`
- **Module plan** (file path given): analyse that module and its corresponding test file
- **Spec plan** (spec name given): resolve to `agents/specs/<SLUG>/spec.md` (see the `specdev` skill for slugification rules), identify the implementation modules, and analyse their tests

### 2. Gather context

1. Read `AGENTS.md` for project structure and testing conventions
2. Read the source modules in scope
3. Read existing test files for modules in scope
4. Read any prior plan files in `agents/test-plans/` to avoid repeating recommendations
5. List available tests with `uv run pytest --co -q` scoped to modules in scope

### 3. Identify gaps

For each source module in scope:

1. Map public functions and classes
2. Check which have corresponding test cases
3. Assess whether existing tests cover meaningful scenarios (not just happy path)
4. Note functions that lack tests but warrant them per the [Goals](#goals)

### 4. Write the plan file

Cap the plan at 20 recommendations. If more gaps exist, note the total count in the Summary and recommend a focused follow-up plan.

Write findings to `agents/test-plans/plan-N.md` using the [Plan template](#plan-template) below.

To determine N: check existing files in `agents/test-plans/` and use the next available number starting from 1. If the directory does not exist, create it.

**Do not overwrite existing plan files.** Always increment N.

### 5. Act on findings

- **If there are recommendations:** use the `taskdev` skill to create a task list.

```
/taskdev agents/test-plans/plan-N.md
```

- **If there are no recommendations:** tell the user where the plan file was written.

### 6. Version control

1. Check for uncommitted changes with `git status`
2. If uncommitted changes exist, ask the user if they want to commit them first
3. After writing the plan, stage it: `git add agents/test-plans/plan-N.md`
4. Ask the user if they'd like to commit
5. Commit with message: `"testplan: add plan-N"`
6. Do not push unless the user asks

## Test plan index

Maintain an index at `agents/test-plans/index.md`. When creating or updating a plan, add or update its entry. If the index does not exist, create it.

Format:

```markdown
# Test Plan Index

| Scope | Plan | Date |
|-------|------|------|
| full | [plan-1.md](plan-1.md) | 2026-03-19 |
```

## Testing conventions

Reference these conventions when assessing gaps and writing recommendations.

### Test file layout

- Test files live in `src/tests/` and mirror the source layout:
  - `src/<project>/<name>.py` -> `src/tests/test_<name>.py`
  - `src/<project>/<pkg>/<file>.py` -> `src/tests/<pkg>/test_<file>.py`
- Test functions are prefixed with `test_`
- Make and use re-usable pytest fixtures
- Place fixture files in `src/tests/fixtures/` with names that mirror the source module names
- Load fixtures in the `src/tests/conftest.py` file
- Use hypothesis for functions with well-defined input domains
- Use `pytest.raises` for expected exceptions

### Performance guardrails

- Mark tests that load large models or process real datasets with `@pytest.mark.slow`
- Skip slow tests during development with `pytest -m "not slow"`
- The `slow` marker is registered in `pyproject.toml`
- Hypothesis tests must always use `@settings(max_examples=20, deadline=10000)` to keep run times predictable
- Do not increase `max_examples` without good reason — the default of 20 balances coverage and speed
- If a single test takes more than 10 seconds, it should be marked `@pytest.mark.slow`

## Plan template

```markdown
# Test Plan N

**Date:** YYYY-MM-DD
**Scope:** <what was analysed -- "full" or specific modules>

## Summary

<2-3 sentence overview of testing gaps found>

## Gaps

### Gap 1: <module or function name>

- **Module:** `path/to/module.py`
- **Function(s):** `function_name`
- **Test file:** `path/to/test_file.py` (existing) or "missing"
- **What's missing:** <description of what isn't tested>
- **Suggested approach:** pytest / hypothesis / both
- **Priority:** high / medium / low

### Gap 2: <module or function name>

...

## Well-covered modules

List modules that were checked and have adequate test coverage. Only include this section if there are modules with no gaps.
```
