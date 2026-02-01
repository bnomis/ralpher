import ralphlib.options
import ralphlib.templater


def test_templater() -> None:
    options = ralphlib.options.RalpherOptions(
        vars=[
            'name=World',
            'greeting=Hello',
        ]
    )
    prompt = '{{ greeting }}, {{ name }}!'
    rendered = ralphlib.templater.render(options, prompt)
    assert rendered == 'Hello, World!'
