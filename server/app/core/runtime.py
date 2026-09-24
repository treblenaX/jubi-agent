"""
Runtime-adjustable settings (settings menu).

Unlike config.Settings (env vars, read once at import), these values can
change while the server runs and are persisted to runtime_settings.json so
they survive restarts. Changing them triggers an agent rebuild in
app.graph.graph (middleware stack / model / num_ctx are baked in at build time).

Defaults seed from env config on first run.
"""

import json
import os
import threading

from app.core.config import settings

# Lives next to harness.db (server working directory).
_FILE = "runtime_settings.json"
_lock = threading.Lock()

# Defaults seed from env config; compaction per SPEC-02 + the state-document
# lifecycle protocol (~85% pressure trigger, keep last 20 messages).
_DEFAULTS = {
    "model": settings.OLLAMA_MODEL,
    "num_ctx": settings.OLLAMA_NUM_CTX,
    "compaction_enabled": True,
    "compaction_mode": "state_doc",
    "compaction_trigger_fraction": 0.85,
    "compaction_keep_messages": 20,
}

# Validation bounds
_NUM_CTX_MIN, _NUM_CTX_MAX = 1024, 131072
_FRACTION_MIN, _FRACTION_MAX = 0.1, 0.95
_KEEP_MIN, _KEEP_MAX = 1, 200


def _path() -> str:
    """Settings file lives next to harness.db (server working dir)."""
    return _FILE


def _validate(patch: dict) -> dict:
    """Return the validated subset of patch. Raises ValueError on bad input."""
    out = {}
    if "model" in patch:
        model = patch["model"]
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")
        out["model"] = model.strip()
    if "num_ctx" in patch:
        try:
            num_ctx = int(patch["num_ctx"])
        except (TypeError, ValueError):
            raise ValueError("num_ctx must be an integer")
        if not (_NUM_CTX_MIN <= num_ctx <= _NUM_CTX_MAX):
            raise ValueError(f"num_ctx must be {_NUM_CTX_MIN}-{_NUM_CTX_MAX}")
        out["num_ctx"] = num_ctx
    if "compaction_enabled" in patch:
        if not isinstance(patch["compaction_enabled"], bool):
            raise ValueError("compaction_enabled must be a boolean")
        out["compaction_enabled"] = patch["compaction_enabled"]
    if "compaction_mode" in patch:
        mode = patch["compaction_mode"]
        if mode not in ("state_doc", "summary"):
            raise ValueError("compaction_mode must be 'state_doc' or 'summary'")
        out["compaction_mode"] = mode
    if "compaction_trigger_fraction" in patch:
        try:
            frac = float(patch["compaction_trigger_fraction"])
        except (TypeError, ValueError):
            raise ValueError("compaction_trigger_fraction must be a number")
        if not (_FRACTION_MIN <= frac <= _FRACTION_MAX):
            raise ValueError(
                f"compaction_trigger_fraction must be {_FRACTION_MIN}-{_FRACTION_MAX}"
            )
        out["compaction_trigger_fraction"] = frac
    if "compaction_keep_messages" in patch:
        try:
            keep = int(patch["compaction_keep_messages"])
        except (TypeError, ValueError):
            raise ValueError("compaction_keep_messages must be an integer")
        if not (_KEEP_MIN <= keep <= _KEEP_MAX):
            raise ValueError(f"compaction_keep_messages must be {_KEEP_MIN}-{_KEEP_MAX}")
        out["compaction_keep_messages"] = keep
    return out


def get() -> dict:
    """Current runtime settings (defaults overlaid with persisted file)."""
    with _lock:
        current = dict(_DEFAULTS)
        try:
            with open(_path()) as f:
                current.update(json.load(f))
        except (OSError, ValueError):
            pass  # no file yet / corrupt -> defaults
        return current


def update(patch: dict) -> dict:
    """Validate, merge, and persist a settings patch. Returns new settings."""
    valid = _validate(patch or {})
    with _lock:
        current = dict(_DEFAULTS)
        try:
            with open(_path()) as f:
                current.update(json.load(f))
        except (OSError, ValueError):
            pass
        current.update(valid)
        with open(_path(), "w") as f:
            json.dump(current, f, indent=2)
        return current
