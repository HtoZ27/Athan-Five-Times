"""
User-defined reminders (adhkar/prayer/dhikr reminders).

Storage: JSON file under XDG_CONFIG_HOME/athan-five-times/reminders.json
Model: {id, text, time (HH:MM), days (list of weekday ints 0=Mon..6=Sun or []=daily),
        enabled, created_at}
Scheduling is driven by the controller's 60s tick (no background thread).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()


def _storage_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(base) / "athan-five-times" / "reminders.json"


def _load() -> List[Dict]:
    try:
        p = _storage_path()
        if p.is_file():
            with p.open(encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("Failed to load reminders: %s", exc)
    return []


def _save(items: List[Dict]) -> None:
    try:
        p = _storage_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("Failed to save reminders: %s", exc)


def _parse_time(time_str: str) -> str:
    """Validate "HH:MM" and return it zero-padded, else raise ValueError."""
    try:
        hh, mm = time_str.split(":")
        hh, mm = int(hh), int(mm)
    except (ValueError, AttributeError) as exc:
        raise ValueError("invalid time (expected HH:MM)") from exc
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError("invalid time (expected HH:MM)")
    return "%02d:%02d" % (hh, mm)


def list_reminders() -> List[Dict]:
    with _LOCK:
        return [dict(r) for r in _load()]


def add_reminder(text: str, time_str: str, days: Optional[List[int]] = None) -> Dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("text required")
    tstr = _parse_time(time_str)
    days = [int(d) for d in (days or []) if 0 <= int(d) <= 6]
    rec = {
        "id": uuid.uuid4().hex[:12],
        "text": text,
        "time": tstr,
        "days": days,
        "enabled": True,
        "created_at": int(time.time()),
    }
    with _LOCK:
        items = _load()
        items.append(rec)
        _save(items)
    return rec


def remove_reminder(rid: str) -> bool:
    with _LOCK:
        items = _load()
        new = [r for r in items if r.get("id") != rid]
        if len(new) == len(items):
            return False
        _save(new)
        return True


def toggle_reminder(rid: str, enabled: bool) -> bool:
    with _LOCK:
        items = _load()
        found = False
        for r in items:
            if r.get("id") == rid:
                r["enabled"] = bool(enabled)
                found = True
        if found:
            _save(items)
        return found


def update_reminder(rid: str, text: str = None, time_str: str = None, days=None) -> bool:
    with _LOCK:
        items = _load()
        found = False
        for r in items:
            if r.get("id") == rid:
                if text is not None:
                    r["text"] = text.strip()
                if time_str is not None:
                    r["time"] = _parse_time(time_str)
                if days is not None:
                    r["days"] = [int(d) for d in days if 0 <= int(d) <= 6]
                found = True
        if found:
            _save(items)
        return found


def due_reminders(now: Optional[datetime] = None) -> List[Dict]:
    """Return reminders that should fire at `now` (minute precision)."""
    now = now or datetime.now()
    hm = now.strftime("%H:%M")
    wd = now.weekday()
    out = []
    for r in list_reminders():
        if not r.get("enabled"):
            continue
        if r.get("time") != hm:
            continue
        days = r.get("days") or []
        if days and wd not in days:
            continue
        out.append(r)
    return out
