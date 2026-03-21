# -*- coding: utf-8 -*-
"""
Persist lightweight process heartbeat and last-activity state for debugging.
"""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def _resolve_project_root() -> Path:
    try:
        from config import PROJECT_ROOT
        return Path(PROJECT_ROOT)
    except Exception:
        return Path(__file__).parent.parent


class ProcessHeartbeat:
    def __init__(self, service_name: str, interval_seconds: int = 30):
        self.service_name = service_name
        self.interval_seconds = interval_seconds
        self.project_root = _resolve_project_root()
        self.state_dir = self.project_root / "data" / "runtime_state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / f"{service_name}.json"
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        now = self._now()
        self._state = {
            "service": service_name,
            "pid": os.getpid(),
            "start_time": now,
            "last_seen": now,
            "activity": "starting",
            "activity_details": {},
            "activity_at": now,
        }

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _write(self) -> None:
        with self._lock:
            payload = dict(self._state)
        self.state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def start(self) -> None:
        self._write()
        self._thread = threading.Thread(target=self._run, name=f"{self.service_name}-heartbeat", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            with self._lock:
                self._state["last_seen"] = self._now()
            self._write()

    def update(self, activity: str, **details: Any) -> None:
        with self._lock:
            now = self._now()
            self._state["last_seen"] = now
            self._state["activity"] = activity
            self._state["activity_details"] = details
            self._state["activity_at"] = now
        self._write()

    def stop(self, reason: str) -> None:
        self._stop_event.set()
        with self._lock:
            now = self._now()
            self._state["last_seen"] = now
            self._state["exit_at"] = now
            self._state["exit_reason"] = reason
        self._write()
