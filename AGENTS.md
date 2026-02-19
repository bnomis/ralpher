# ralpher

A ralph loop.

## Goals

Run an agent prompt a specified maximum number of times

Show the agent progress in the terminal - parsing streamed json output

Stop when the agent indicates via a completion message

Record logs

## Project structure

```shell
src/
├── ralphlib/              # Main library package
│   ├── __init__.py
│   ├── iteration.py
│   ├── logger.py
│   ├── looper.py
│   ├── options.py
│   ├── printer.py
│   ├── state.py
│   ├── templater.py
│   └── types.py
└── tests/                 # Tests mirror source structure
    ├── __init__.py
    └── test_templater.py
bin/                       # Entry point scripts
├── activate.sh
├── ralpher.py
└── ralpher.sh
logs/                      # Application log output
```

## Development tools and libraries

ralpher is developed using the following tools and libraries:

- Main programming language: Python version 3.14 <https://docs.python.org/release/3.14.2/>
- Package and virtual environment management: uv <https://docs.astral.sh/uv/>
- Network http[s] requests: `httpx` <https://www.python-httpx.org/>
- Logging: `loguru` <https://loguru.readthedocs.io/en/stable/overview.html>
- Command line argument processing: `cappa` <https://cappa.readthedocs.io/en/latest/index.html>
- Coding standards, quality and lint: ruff <https://docs.astral.sh/ruff/>
- Containerisation: Docker <https://docs.docker.com/>
- Testing: `pytest` <https://docs.pytest.org/en/stable/>
- Property based testing: hypothesis <https://hypothesis.works/>
- Environment variables: `direnv` <https://direnv.net/> read from the `.envrc` file

### Dependency management

- All dependencies are declared in `pyproject.toml` and managed via `uv`
- Do not run `pip install` directly — use `uv add <package>` to add dependencies
- The lockfile `uv.lock` is committed to the repository

## Bash guidelines

### Avoid commands that cause output buffering issues

Do not pipe output through `head`, `tail`, `less` or `more` when monitoring or checking command output

Do not use `| head -n X` or `| tail -x X` to truncate output, these cause buffering problems

Let commands complete fully or use command line flags to limit output if supported, for example `--max-lines` or `--maxlines`

For log monitoring, prefer reading files directly rather than piping through filters

### When checking command output

Run commands directly without pipes when possible

If you need to limit output, use command specific flags. For example, use `git log -n 10` instead of `git log | head -10`

Avoid chained pipes, these can cause output to buffer indefinitely

### Avoid interactive commands

Do not use interactive flags such as `-i` or commands that require user input (e.g., `less`, `vim`, `nano`)

## Security

Always follow good security practices. Think about the security implications of every decision. All secret information such as API keys should be encrypted if stored or read from environment variable at run time.

## Do not modify

The following files should not be modified without explicit instruction:

- `.envrc`
- `uv.lock` (managed by `uv` automatically)
- `.pre-commit-config.yaml`

## Coding standards

Follow the ruff rules defined in `pyproject.toml`.

Check that source code meets our standard with the `ruff check` command line tool.

**IMPORTANT**: make sure the source code is cleanly formatted with `ruff format`

### Imports

- Follow ruff's isort-compatible import ordering (stdlib, third-party, local)
- First-party packages: `ralpher`, `ralphlib`
- No wildcard imports (`from module import *`)

### Type annotations

- All function signatures must have parameter and return type annotations
- Use `None` return type explicitly for functions that return nothing
- Prefer built-in generics (`list[str]`, `dict[str, int]`) over `typing` equivalents
- Use `|` union syntax (Python 3.14) instead of `Union` or `Optional`

### Naming

- `snake_case` for functions, methods, variables, modules
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- DO NOT use different naming for private attributes, e.g. do not prefix with underscore

### String formatting

- **Always use f-strings** instead of `%` formatting or `.format()`
- Convert existing `%` patterns to f-strings when editing
- Example: `f'Exception: {e}'` instead of `'Exception: %s' % e`
- Use single quotes for strings whenever possible (enforced by ruff format config)
- Exception: use double quotes when the string itself contains a single quote

### Alphabetical ordering

Configuration lists, enum-like collections, and import groups should be in **alphabetical** order. For example:

```python
names = [
    'aardvark',
    'bird',
    'cat',
]
```

Do **not** alphabetise lists where order is semantically meaningful (e.g., processing pipelines, priority ordering, function call sequences).

### Data structures

- Prefer `dataclasses` for structured data
- Use `cappa` dataclass conventions for CLI argument definitions

### Error handling

- Use specific exception types, not bare `except:`
- Let unexpected exceptions propagate rather than silently catching them
- Use `httpx` exception hierarchy for network errors

### Comments

Do not add obvious comments.
Only add comments if they add a lot of value that is not obvious from reading the code.

Function docstrings are not required for all functions but you may add them to describe the purpose and input/output of a function if it helps for understanding.

### Logging

- Use `loguru.logger` — do not use stdlib `logging`
- Use appropriate levels: `debug` for internals, `info` for progress, `warning` for recoverable issues, `error` for failures, `exception` to log exceptions in `except` blocks

## Testing

- Test files live in `src/tests/` and mirror the source module names (e.g., `test_templater.py` tests `ralphlib/templater.py`)
- Test functions are prefixed with `test_`
- Use hypothesis for functions with well-defined input domains
- Use `pytest.raises` for expected exceptions
- Run tests with `uv run pytest`
