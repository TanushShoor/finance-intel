"""Ephemeral, in-process progress store for in-flight analyses.

The analysis runs in a FastAPI background task that shares this process with the
API, so a simple thread-safe dict is enough for the GET endpoint to read live
progress. Progress is intentionally not persisted — it is only meaningful while a
contract is being processed. (Single-process only; would need shared storage
behind multiple workers.)
"""
import threading

_lock = threading.Lock()
_store: dict[int, dict] = {}


def set_progress(contract_id: int, **fields) -> None:
    with _lock:
        current = _store.get(contract_id, {})
        current.update(fields)
        _store[contract_id] = current


def get_progress(contract_id: int) -> dict | None:
    with _lock:
        value = _store.get(contract_id)
        return dict(value) if value else None


def clear_progress(contract_id: int) -> None:
    with _lock:
        _store.pop(contract_id, None)
