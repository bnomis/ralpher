import datetime
import signal
import sys
import threading
import types

import ralphlib.printer
import ralphlib.types

should_exit = False
should_exit_lock = threading.Lock()


def set_should_exit(value: bool) -> None:
    global should_exit
    with should_exit_lock:
        should_exit = value


def get_should_exit() -> bool:
    with should_exit_lock:
        return should_exit


class GracefulTerminator:
    CTRL_C_PRESS_INTERVAL = 3  # seconds
    FIRST_MESSAGE = f'Ctrl+C pressed → Press **once more** within {CTRL_C_PRESS_INTERVAL} seconds to exit'
    SECOND_MESSAGE = '→ Exiting now!'
    EXIT_CODE = 130

    def __init__(self) -> None:
        self.first_press = None
        self.is_shutting_down = False
        signal.signal(signal.SIGINT, self.handler)
        signal.signal(signal.SIGTERM, self.handler)

    def handler(self, signum: int, frame: types.FrameType | None) -> None:
        if self.is_shutting_down:
            ralphlib.printer.console_print(
                '\nAlready shutting down — forceful exit!\n',
                ralphlib.types.MessageType.ALERT,
            )
            sys.exit(1)

        sig_name = signal.Signals(signum).name
        if signum == signal.SIGTERM:
            ralphlib.printer.console_print(
                f'\nReceived {sig_name} → shutting down gracefully...\n',
                ralphlib.types.MessageType.ALERT,
            )
            self.perform_shutdown()
            return

        now = datetime.datetime.now()
        if self.first_press:
            time_since_first_press = (now - self.first_press).total_seconds()
            if time_since_first_press < self.CTRL_C_PRESS_INTERVAL:
                ralphlib.printer.console_print(
                    f'\n{self.SECOND_MESSAGE}\n',
                    ralphlib.types.MessageType.ALERT,
                )
                self.perform_shutdown()
                return

        ralphlib.printer.console_print(
            f'\n{self.FIRST_MESSAGE}\n',
            ralphlib.types.MessageType.ALERT,
        )
        self.first_press = now

    def perform_shutdown(self) -> None:
        self.is_shutting_down = True
        set_should_exit(True)
