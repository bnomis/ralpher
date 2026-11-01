import shlex

import jinja2.sandbox


def test_quote_the_value() -> None:
    var = "Give each project's config.py a module name mypy can distinguish"
    s = f'/opt/homebrew/bin/alerter --title {shlex.quote("probe audit-reviews 57/7")} --message {shlex.quote(var)}'
    print(s)
    args = shlex.split(s)
    print(args)
    assert args[-1] == var


def test_quote_handles_double_quotes_too() -> None:
    var = """He said "it's fine" & ran `rm -rf /` $HOME"""
    args = shlex.split(f'alerter --message {shlex.quote(var)}')
    assert args == ['alerter', '--message', var]


def test_jinja_finalize_quotes_every_substitution() -> None:
    env = jinja2.sandbox.SandboxedEnvironment(finalize=lambda v: shlex.quote(str(v)))
    template = env.from_string('/opt/homebrew/bin/alerter --title {{ title }} --message {{ message }}')
    cmd = template.render(
        title='probe audit-reviews 57/7',
        message="Give each project's config.py a module name mypy can distinguish",
    )
    args = shlex.split(cmd)
    assert args[-1] == "Give each project's config.py a module name mypy can distinguish"
