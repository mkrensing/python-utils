import signal
import sys

def register_on_exit(function_callback):
    def __calback(signal: str) -> int:
        function_callback()
        sys.exit(0)

    signal.signal(signal.SIGTERM, lambda *x: __calback("SIGTERM"))
    signal.signal(signal.SIGINT, lambda *x: __calback("SIGINT"))