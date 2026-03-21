---
name: taskdev
description: Guide the user in the production of a task list from a specification file
when_to_use: |
    Use this skill whenever the user mentions:
        - write a task list
        - task lists
        - plan the implementation
        - break a spec into tasks
        - implement a spec
        - build tasks from a spec

allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill]
---

# Task development

Invoke as:
    /taskdev <SPEC-NAME>
    /taskdev <SPEC-PATH>

Where:

- <SPEC-NAME> is the title of the spec
- <SPEC-PATH> is the path to a spec or a review, it can be distinguished because it will have slashes "/" in it

If no argument is provided, list existing specs from agents/specs/index.md and ask the user to pick one.

## Spec location

If you are given a <SPEC-NAME> you can find the spec with the following rules.

The spec file is at `agents/specs/<SLUG>/spec.md`, where `<SLUG>` is the slugified version of <SPEC-NAME> (lowercase, spaces to hyphens, non-alphanumeric characters removed). See the [specdev skill](../specdev/SKILL.md) for full slugification rules.

If you are given a <SPEC-PATH> read the spec at that path. The <SLUG> in this case will be the name of the directory containing the spec. For example, for a spec at path `agents/audit-reviews/review-1.md` the <SLUG> is `audit-reviews`.

## Non-spec input

A document is a spec if its path is under agents/specs/ and the filename is spec.md. All other paths are treated as non-spec input.

When the input document is not a spec (e.g., an audit review file):

- Step 3: skip the specdev invocation — mark ambiguous items with **Caveat:** instead
- Step 6: skip API signature comparison — check only whether implementation code exists for the described changes
- Step 9: verify every actionable finding/recommendation has a corresponding task (instead of verifying spec section coverage)
- File header: use **Source:** `<input path>` instead of **Spec:**
- Task template: use **Source Reference:** `<finding number>` instead of **Spec Reference:**

## Gather context

1. Read `AGENTS.md` and `README.md`
2. Read `agents/tasks/index.md` (if it exists)
3. Read existing task files in `agents/tasks/<SLUG>/tasks-*.md` (if they exists)

## Follow existing rules and standards

All tasks should following the standards in AGENTS.md established for source code, testing and file system layout.

## Workflow

1. Read the spec at the resolved path
2. Read related `.md` documents in the same directory
3. If the spec is ambiguous or incomplete, ask the user whether to invoke the specdev skill (via the Skill tool) to improve it before proceeding. If the user declines, continue but add a warning to the task file header noting which spec sections were ambiguous, and mark affected tasks with `**Caveat:** spec unclear` in their Notes
4. Read any existing `tasks-*.md` files in `agents/tasks/<SLUG>/` to understand prior work
5. Analyse the spec and produce an implementation plan
6. Check if implementation code already exists:
   1. Search `src/` for modules matching task descriptions using Glob and Grep
   2. Compare public API signatures against the spec (function names, parameters, return types)
   3. Check for tests that cover the implemented functionality
   4. Mark tasks as done only if the API matches the spec and tests verify correctness
   5. For partial implementations, mark the task as in-progress and note what remains in the subtasks
7. Write the task list file
8. Update `agents/tasks/index.md` with the new task file entry (create the index if it doesn't exist)
9. Verify coverage: confirm every spec section is addressed by at least one task
10. Present the task list summary to the user for review

## Task sizing

The plan should consist of small, self-contained tasks. A self-contained task:

- Is a logical unit that can be implemented, tested, and integrated without breaking the system
- Typically corresponds to a single Python module or a focused change across a few files
- Should be completable in a single working session

Aim for less than 15 tasks per spec. If more are needed, suggest splitting the spec.

## Task format

Use user stories for user-facing tasks. For infrastructure or technical tasks where "As a user" doesn't fit naturally, use the technical goal format instead.

Each task should include:

- **Status**: todo / in-progress / done
- **Priority**: high / medium / low
- **Complexity**: small / medium / large
- **Spec Reference**: which section(s) of the spec this task fulfils
- **Subtasks**: atomic actions that are not further decomposable
- **Acceptance Criteria**: testable conditions
- **Notes**: dependencies, relevant file paths, implementation hints

## Task ordering

Tasks should be in implementation order. Take into account:

- Dependencies between tasks (explicit: "Task 3 depends on Task 1")
- Priority (high-priority tasks first when dependencies allow)
- Complexity (consider front-loading simpler tasks to build momentum)

## Cross referencing

If the spec references other specs, check whether tasks from those specs have already been created and note dependencies.

## File output

Write the implementation plan to `agents/tasks/<SLUG>/tasks-N.md`, where N is an index starting from 1.

If the file already exists DO NOT overwrite it. Instead increment N to create a unique filename (e.g., tasks-2.md, tasks-3.md).

Tasks numbering always starts at 1 per file, and dependencies reference file + task number ("tasks-1.md Task 3")

### File header

Every task list file must start with a metadata header:

```markdown
# Tasks: <SPEC-NAME>

**Spec:** `agents/specs/<SLUG>/spec.md`
**Created:** <YYYY-MM-DD>
**Version:** N
```

## Task index

Maintain an index file at `agents/tasks/index.md` listing all task files across all specs. When creating a new task file, add an entry to this index. If the index does not exist, create it.

Format:

```markdown
# Task Index

| Spec | Task File | Version | Created |
|------|-----------|---------|---------|
| [Searcher](../specs/searcher/spec.md) | [tasks-1.md](searcher/tasks-1.md) | 1 | 2026-03-08 |
```

## Reconciling with spec changes

If prior task files exist and the spec has changed since they were written:

1. Check previous task files and flag tasks that no longer align with the spec (removed requirements, changed API, etc.)
2. Check the implementation against the current spec and make a new task file to implement changes to bring the implementation in line with the spec.
3. If there are tasks left over from previous sessions, check against the spec, flag if no longer relevant, if any are still relevant add to the task file created in step 2.

## Task template

Use User Story for user-facing tasks or Technical Goal for infrastructure tasks. Include only one.

```markdown
---

## Task <N>: <description>

**Status:** todo
**Priority:** high/medium/low
**Complexity:** small/medium/large
**Spec Reference:** <section name or "Section X.Y">

**User Story:** As a [user], I want [feature], so that [benefit].
**Technical Goal:** <what needs to happen and why>

**Subtasks:**

- [ ] <atomic action>
...

**Acceptance Criteria:**

- [ ] <testable condition>
...

**Notes:**

- Depends on Task <M>
- Depends on tasks-1.md Task <M> *(use this format for cross-file references)*
- Key files: `path/to/relevant/module.py`
- <any implementation hints or context>

---
```

## Completion checklist

Before finalising the task list, verify:

- [ ] Every section of the spec is covered by at least one task
- [ ] No task is so large it should be split further
- [ ] Dependencies between tasks are explicitly stated
- [ ] Existing completed work is marked as done
- [ ] Task order respects dependency chains
- [ ] Prior task files were reviewed to avoid duplicating already-planned work

## Version control

Before making any changes to a task file:

1. Check if the task file has uncommitted changes with `git status`
2. If uncommitted changes exist, ask the user if they want to commit them first
3. After editing, stage the task file and index: `git add agents/tasks/<SLUG>/tasks-N.md agents/tasks/index.md`
4. Ask the user if they'd like to commit the changes
5. Commit with a message describing what changed, e.g.: `"taskdev: add error handling tasks"`
6. Do not push unless the user asks
