import enum
import types


class MessageType(enum.IntEnum):
    NONE = 0
    ERROR = 1
    SYSTEM = 2
    CONTENT_START = 3
    CONTENT_STOP = 4
    CONTENT_DELTA = 5
    TOOL_USE = 6
    COMPLETE = 7
    REGULAR = 8
    ALERT = 9
    PROGRESS = 10


MESSAGE_TYPE_TO_STR = types.MappingProxyType(
    {
        MessageType.NONE: 'none',
        MessageType.ERROR: 'error',
        MessageType.SYSTEM: 'system',
        MessageType.CONTENT_START: 'content_start',
        MessageType.CONTENT_STOP: 'content_stop',
        MessageType.CONTENT_DELTA: 'content_delta',
        MessageType.TOOL_USE: 'tool_use',
        MessageType.COMPLETE: 'complete',
        MessageType.REGULAR: 'regular',
        MessageType.ALERT: 'alert',
        MessageType.PROGRESS: 'progress',
    }
)


class RalpherEventType(enum.IntEnum):
    NONE = 0
    START = 1
    ITERATION_START = 2
    ITERATION_END = 3
    END = 4
    ERROR = 5
    LLM_TASK_PROGRESS = 6
    AGENT_PROCESS_START = 7
    AGENT_PROCESS_END = 8


RALPHER_EVENT_TYPE_TO_STR = types.MappingProxyType(
    {
        RalpherEventType.NONE: 'none',
        RalpherEventType.START: 'start',
        RalpherEventType.ITERATION_START: 'iteration_start',
        RalpherEventType.ITERATION_END: 'iteration_end',
        RalpherEventType.END: 'end',
        RalpherEventType.ERROR: 'error',
        RalpherEventType.LLM_TASK_PROGRESS: 'llm_task_progress',
        RalpherEventType.AGENT_PROCESS_START: 'agent_process_start',
        RalpherEventType.AGENT_PROCESS_END: 'agent_process_end',
    }
)
