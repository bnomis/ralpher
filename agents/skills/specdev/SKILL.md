---
name: specdev
description: Guide the user in the development of specification markdown files
when_to_use: |
    Use this skill whenever the user mentions:
        - writing specs
        - specifications
        - spec drift
        - review a spec
        - update a spec
        - create a spec

allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill]
---

# Specification development

Invoke as:
    /specdev <SPEC-NAME>

Where `<SPEC-NAME>` is the title of the spec. If no argument is provided, list existing specs from agents/specs/index.md and ask the user to pick one or provide a name.

## Slugification

Specs are saved as a markdown file in `agents/specs/<SLUG>/spec.md` where `<SLUG>` is the slugified version of `<SPEC-NAME>`.

Slugification rules: lowercase ASCII alphanumeric only, spaces become hyphens, all other characters removed, consecutive hyphens collapsed to one, leading/trailing hyphens stripped.

Examples:

- `"Searcher"` -> `searcher`
- `"C++ Parser v2.0"` -> `c-parser-v20`
- `"Date Filtering"` -> `date-filtering`
- `"foo--bar"` -> `foo-bar`

Let `<SPEC-PATH>` be `agents/specs/<SLUG>/spec.md`.

## Purpose

Specs must be detailed enough that the [taskdev](../taskdev/SKILL.md) skill can produce a complete, unambiguous task list from them without further clarification. This is the quality bar for every spec.

## Spec size

If a spec covers multiple independent components, consider splitting into separate specs and linking them.

## Workflow

Follow this decision tree:

1. **Does a spec exist at `<SPEC-PATH>`?**
   - **NO** -> Interview the user -> Write initial draft -> Update `agents/specs/index.md` with a link to the new spec
   - **YES** -> Read the spec, then:
     1. **Does implementation code exist at the module location stated in the spec?**
        - **YES** -> Run drift detection (see [Drift detection](#drift-detection) below)
        - **NO** -> Skip drift
     2. Check spec completeness against the template and validation criteria
     3. Suggest improvements
     4. **Did the user request a specific change?** (e.g., "add a caching section", "update the API")
        - **YES** -> Apply the requested change directly, then re-run validation
        - **NO** -> Present suggestions and ask the user what to change

## Interview

Use the AskUserQuestion tool to gather information not already present in the spec or the codebase. Example questions:

- What does this component do? (introduction)
- Where does it live in the codebase? (module location)
- What functions/classes does it expose? (API)
- What can go wrong? (error handling)
- Are there configurable behaviors? (settings)
- What external services or libraries does it depend on? (external dependencies)

Ask questions iteratively, not all at once. Stop when you can fill every required template section with concrete content (not placeholders) as described in [Purpose](#purpose).

## Spec template

A spec must contain at minimum the following sections. Copy this skeleton when creating a new spec:

~~~markdown
# <Title>

<Introduction: what the component does and why it exists.>

## Module location

`<path-to-component>`

## API

```python
# At least one public function/class with full type annotations and docstring
```

## Error handling

<Name specific exception classes or describe failure modes and what happens on failure.>

## Implementation

<Describe the approach, algorithms, or strategy. Do not just restate the API.>

## Settings

<List setting names, types, defaults, and descriptions. Omit this section only if the component has no configurable behavior.>

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `component.setting_name` | `str` | `"default"` | What it controls |

## External dependencies

<External libraries, services, or APIs the component depends on.>

~~~

Additional domain-specific sections should be added as needed. When deciding whether something warrants its own section vs being part of Implementation, use this rule: if a topic has its own configuration, failure modes, or is complex enough to need subsections, give it its own top-level section.

Also:

- API sections must include concrete function signatures with type annotations and docstrings
- Implementation sections must describe the approach, not just restate the API
- Settings must include defaults and value types

## Cross-referencing

When writing or updating a spec:

1. Read `agents/specs/index.md` to discover all existing specs
2. If the spec mentions a concept covered by another spec, add a relative markdown link: `[Settings](../settings/spec.md)`
3. Check if the new spec's dependencies overlap with existing specs and link to them

## Drift detection

When a spec has a corresponding implementation, compare them to find inconsistencies. Use Glob and Grep to search the codebase.

**What to compare:**

- Function/method signatures (names, parameters, return types)
- Class names and public attributes
- Module paths and file structure
- Settings keys and defaults
- Exception/error class names
- External dependency versions or libraries referenced

**What to do with findings:**

1. Present a report listing each inconsistency with the spec line and the code location
2. Ask the user whether to update the spec to match the code, update the code to match the spec, or skip each item
3. Do not assume a direction -- the user decides

## Validation criteria

After writing or editing a spec, verify:

- [ ] Every section from the template is present (except Settings, which may be omitted if not applicable)
- [ ] No section is empty or contains only placeholder text
- [ ] **API** section contains at least one code block with a type-annotated function or class signature
- [ ] **Module location** references a path under `src/` (existing or proposed)
- [ ] **Error handling** names specific exception classes or describes concrete failure modes
- [ ] **Settings** (if present) includes a table or list with setting name, type, and default for each entry
- [ ] All module paths referenced in the spec correspond to actual (or clearly proposed) paths in the codebase
- [ ] Cross-references to other specs use relative markdown links and resolve correctly

## Version control

Before making any changes to a spec file:

1. Check if the spec file has uncommitted changes with `git status`
2. If uncommitted changes exist, ask the user if they want to commit them first
3. After editing the spec, stage only the spec file: `git add <SPEC-PATH>`
4. Ask the user if they'd like to commit the changes
5. Commit with a message describing what changed, e.g.: `"specdev: add error handling section to <SLUG> spec"`
6. Do not push unless the user asks
