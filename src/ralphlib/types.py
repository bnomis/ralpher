import enum


class MessageType(enum.IntEnum):
    NONE = 0
    ERROR = 1
    SYSTEM = 2
    CONTENT_START = 3
    CONTENT_STOP = 4
    CONTENT_DELTA = 5
    TOOL_USE = 6
