# -*- coding: utf-8 -*-
"""
Runtime diagnostics helpers for long-running service processes.
"""

import atexit
import logging
import signal
import sys
import threading
from typing import Callable, Optional

from logger import log_with_context


def install_runtime_diagnostics(logger: logging.Logger, service_name: str) -> Callable[..., None]:
    """
    Install lightweight process diagnostics for long-running workers.

    Returns a marker function that can be used to record an expected shutdown
    reason before exiting the process.
    """
    state = {
        "service": service_name,
        "exit_reason": "process_exit",
        "expected": False,
        "signal": None,
        "installed": True,
    }

    def mark_shutdown(reason: str, expected: bool = True, signal_name: Optional[str] = None) -> None:
        state["exit_reason"] = reason
        state["expected"] = expected
        if signal_name:
            state["signal"] = signal_name

    previous_excepthook = sys.excepthook

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            mark_shutdown("keyboard_interrupt", expected=True)
            logger.info("收到 KeyboardInterrupt，准备退出")
        else:
            mark_shutdown("unhandled_exception", expected=False)
            logger.critical(
                "未捕获异常导致进程退出",
                exc_info=(exc_type, exc_value, exc_traceback),
            )
        if previous_excepthook:
            previous_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception

    def _make_signal_handler(sig, previous_handler):
        signal_name = signal.Signals(sig).name

        def _handler(signum, frame):
            mark_shutdown("signal", expected=True, signal_name=signal_name)
            log_with_context(
                logger,
                logging.WARNING,
                "收到进程停止信号",
                service=service_name,
                signal=signal_name,
            )
            if callable(previous_handler):
                previous_handler(signum, frame)
            elif previous_handler == signal.SIG_DFL:
                raise SystemExit(0)

        return _handler

    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                previous = signal.getsignal(sig)
                signal.signal(sig, _make_signal_handler(sig, previous))
            except (ValueError, OSError, RuntimeError):
                continue

    def _log_exit():
        log_with_context(
            logger,
            logging.INFO if state["expected"] else logging.WARNING,
            "进程退出",
            service=service_name,
            exit_reason=state["exit_reason"],
            signal=state["signal"],
            expected=state["expected"],
        )

    atexit.register(_log_exit)
    return mark_shutdown
