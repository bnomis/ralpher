---
name: auditme
description: Perform a structured code and spec audit with findings and recommendations
when_to_use: |
    Use this skill whenever the user mentions:
        - audit the code
        - code audit
        - full code review
        - review the codebase

allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill]
---

# Code audit

Invoke as:
    /auditme [scope]

Where `[scope]` is an optional argument specifying what to audit. If no argument is provided, perform a full audit of the entire project.

Scope examples:

- `/auditme` -- full audit (all specs, all source, all docs)
- `/auditme src/<project>/<file>.py` -- audit a single module
- `/auditme <spec>` -- audit a spec and its implementation

## Workflow

### 1. Establish scope

- **Full audit** (no argument): audit `agents/specs/`, `src/`, `AGENTS.md`, and `README.md`
- **Module audit** (file path given): audit that module, its tests, and any spec that references it
- **Spec audit** (spec name given): resolve to `agents/specs/<SLUG>/spec.md`, audit the spec and its implementation

See the `specdev` skill for `slugification` rules

### 2. Gather context

1. Read `AGENTS.md` and `README.md`
2. Read `agents/specs/index.md` (if it exists) to discover all specs
3. Read the source modules in scope
4. Read existing tests for modules in scope
5. Read any prior review files in `agents/audit-reviews/` to avoid repeating findings

### 3. Run automated checks

1. Run `uv run ruff check` on source files in scope -- record any violations
2. Run `uv run ruff format --check` on source files in scope -- record any formatting issues

If ruff reports violations, add a single finding summarising the count and list up to 5 examples. Do not list every violation individually.

### 4. Manual audit

Audit **file-by-file**, not category-by-category. This ensures every file is explicitly reviewed and nothing is skipped due to LLM attention drift.

1. Use `Glob` to build a complete list of source files in scope (e.g. `src/**/*.py`)
2. Iterate through each file in the list:
   a. Read the file
   b. Evaluate it against **every applicable category** in the [Audit checklist](#audit-checklist) below
   c. Record any findings with category, severity, location, and a concrete recommendation
3. Track which files you have reviewed — this list is written to the review file (see [Review template](#review-template))

Do not move on from a file until you have checked all applicable checklist categories against it. This prevents the common failure mode of scanning by category and missing files.

### 5. Spec review

For each spec in scope, check it against the validation criteria and spec template in agents/skills/specdev/SKILL.md. Do not invoke the specdev skill — perform the checks directly and record gaps as findings.

If there are no specs in scope, skip this step.

### 6. Write the review file

Cap the review at 20 findings. If more issues exist, note the total count in the Summary and recommend a focused follow-up audit.

Write findings to `agents/audit-reviews/review-N.md` using the [Review template](#review-template) below.

To determine N: check existing files in `agents/audit-reviews/` and use the next available number starting from 1. If the directory does not exist, create it.

**Do not overwrite existing review files.** Always increment N.

Update `agents/audit-reviews/index.md` with the new review file entry (create the index if it doesn't exist)

### 7. Act on findings

- **If there are recommendations for improvements:** use the `taskdev` skill to create a task list.

```
/taskdev agents/audit-reviews/review-N.md
```

- **If there are no recommendations:** tell the user where the review file was written.

### 8. Version control

1. Check for uncommitted changes with `git status`
2. If uncommitted changes exist, ask the user if they want to commit them first
3. After writing the review, stage it: `git add agents/audit-reviews/review-N.md`
4. Ask the user if they'd like to commit
5. Commit with message: `"auditme: add review-N"`
6. Do not push unless the user asks

## Review index

Maintain an index at `agents/audit-reviews/index.md`. When creating or updating a review, add or update its entry. If the index does not exist, create it.

Format:

```markdown
# Review Index

| Scope | Review | Date |
|-------|--------|------|
| full | [review-1.md](review-1.md) | 2026-03-19 |
```

## Audit checklist

Evaluate each category. Skip categories that are out of scope for a focused audit.

### Documentation coherence

- [ ] `AGENTS.md` project structure matches actual directory layout
- [ ] `AGENTS.md` development tools and libraries list is current
- [ ] `README.md` (if it exists) is consistent with `AGENTS.md`
- [ ] Specs in `agents/specs/` match their implementations (drift detection)

### Coding standards

Ruff violations are captured in step 3. Verify the following in addition to ruff output:

- [ ] All function signatures have parameter and return type annotations
- [ ] Naming follows project conventions (snake_case, PascalCase, UPPER_SNAKE_CASE)
- [ ] f-strings used instead of `%` or `.format()`
- [ ] Imports follow isort ordering (stdlib, third-party, local)
- [ ] No wildcard imports

### Security

- [ ] No secrets, API keys, or credentials hardcoded in source
- [ ] Input validation at system boundaries (user input, external APIs)
- [ ] No command injection vectors (unsanitised input in shell calls)
- [ ] No path traversal vulnerabilities
- [ ] Environment variables used for sensitive configuration

### Testing

Assess by reading test files — do not run the test suite.

- [ ] Test files exist for modules with complex logic
- [ ] Functions with branching logic, error handling, or state transitions have corresponding test cases
- [ ] Property-based tests (hypothesis) used where input domains are well-defined

### Performance

- [ ] No obvious O(n^2) or worse patterns on potentially large inputs
- [ ] No unnecessary blocking I/O in hot paths
- [ ] No redundant file reads or repeated expensive computations

### Dependencies

- [ ] All dependencies declared in `pyproject.toml`
- [ ] No unused dependencies
- [ ] `uv.lock` is committed and up to date

### Architecture

- [ ] Modules have clear, single responsibilities
- [ ] No circular imports
- [ ] Public APIs are minimal and well-defined
- [ ] Error handling follows project convention (let unexpected exceptions propagate)

## Review template

```markdown
# Audit Review N

**Date:** YYYY-MM-DD
**Scope:** <what was audited -- "full" or specific modules/specs>

## Summary

<2-3 sentence overview of findings>

## Findings

### Finding 1: <title>

- **Category:** standards / security / performance / testing / documentation / architecture
- **Severity:** high / medium / low
- **Location:** `path/to/file.py:line` (or "project-wide")
- **Description:** <what the issue is>
- **Recommendation:** <concrete action to fix it>

### Finding 2: <title>

...

## Files reviewed

List every file that was explicitly read and audited during this review. This ensures coverage is visible and reproducible.

- `src/example/module.py` -- checked: standards, security, testing, performance, architecture
- `src/example/other.py` -- checked: standards, security, testing
- ...

## Recommendations

Prioritised summary of recommended actions, ordered by severity

## Clean categories

List categories that were checked and passed cleanly. Only include this section if there are categories with zero findings.
```

## Severity guide

- **High:** security vulnerabilities, crashes, data loss, spec contradicts implementation on critical behaviour
- **Medium:** standards violations, missing tests for complex logic, documentation out of date, performance concerns
- **Low:** style nitpicks not caught by ruff, minor documentation gaps, suggestions for clarity
