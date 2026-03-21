import pytest

import ralphlib.printer
import ralphlib.types


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
        assert ralphlib.printer.type_to_style(message_type) == expected_style

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
        assert ralphlib.printer.type_to_style(message_type) == 'grey30'
