import pathlib

import pytest

import ralphlib.exceptions
import ralphlib.options
import ralphlib.printer
import ralphlib.settings
import ralphlib.types
import tests.helpers


class TestTypeToStyle:
    @pytest.mark.parametrize(
        ('message_type', 'expected_style'),
        [
            (ralphlib.types.MessageType.ALERT, 'bold red'),
            (ralphlib.types.MessageType.CONTENT_DELTA, 'cyan'),
            (ralphlib.types.MessageType.ERROR, 'red'),
            (ralphlib.types.MessageType.REGULAR, 'grey30'),
            (ralphlib.types.MessageType.SYSTEM, 'yellow'),
            (ralphlib.types.MessageType.TOOL_USE, 'magenta'),
        ],
    )
    def test_defined_types_map_to_expected_style(
        self,
        message_type: ralphlib.types.MessageType,
        expected_style: str,
    ) -> None:
        options = tests.helpers.make_options()
        assert ralphlib.printer.type_to_style(options, message_type) == expected_style

    @pytest.mark.parametrize(
        'message_type',
        [
            ralphlib.types.MessageType.COMPLETE,
            ralphlib.types.MessageType.CONTENT_START,
            ralphlib.types.MessageType.CONTENT_STOP,
            ralphlib.types.MessageType.NONE,
        ],
    )
    def test_unmapped_types_fall_back_to_grey30(
        self,
        message_type: ralphlib.types.MessageType,
    ) -> None:
        options = tests.helpers.make_options()
        assert ralphlib.printer.type_to_style(options, message_type) == 'grey30'


def test_prt_translates_progress_log_error(tmp_path: pathlib.Path) -> None:
    blocker = tmp_path / 'file'
    blocker.write_text('x')
    options = tests.helpers.make_options(progress='progress.log', logdir=str(blocker), quiet=True)
    with pytest.raises(ralphlib.exceptions.LogFileError):
        ralphlib.printer.prt(options, 'hello', 1)
