# ralpher

A ralph loop.

## Goals

Run an agent prompt a specified maximum number of times

Show the agent progress in the terminal - parsing streamed json output

Stop when the agent indicates via a completion message

Record logs

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
- Environment variables: `direnv` <https://direnv.net/> read from the `.env` file

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

## Security

Always follow good security practices. Think about the security implications of every decision. All secret information such as API keys should be encrypted if stored or read from environment variable at run time.

## Coding standards

Follow the ruff rules defined in `pyproject.toml`.

Check for source code meets our standard with the `ruff check` command line tool.

Always develop using type declarations.

**IMPORTANT**: make sure the source code is cleanly formatted with `ruff format`

### String Formatting

- **Always use f-strings** instead of `%` formatting or `.format()`
- Convert existing `%` patterns to f-strings when editing
- Example: `f'Exception: {e}'` instead of `'Exception: %s' % e`
- Use single quotes 'strings' whenever possible instead of "strings"

### Alphabetical ordering of lists

All lists should be in **alphabetical** order. For example like this:

```python
list = [
    'aardvark',
    'bird',
    'cat',
]
```

### Comments

Do not add obvious comments.

Function docstrings are not required for all functions.

Only add comments if they add a lot of value that is not obvious rom reading the code.
