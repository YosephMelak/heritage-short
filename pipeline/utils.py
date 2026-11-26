"""Shared helpers for configuration, JSONL logging, SHA-256 caching, and retries."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
STORYBOARD_PATH = REPO_ROOT / "storyboard.json"
SCHEMA_PATH = REPO_ROOT / "schema" / "storyboard.schema.json"
RUNS_LOG_PATH = REPO_ROOT / "runs.jsonl"
OUTPUTS_DIR = REPO_ROOT / "outputs"

T = TypeVar("T")


def load_env() -> None:
    """Load environment variables from `.env` at the repository root if present."""
    load_dotenv(REPO_ROOT / ".env")


def load_json(path: Path) -> Any:
    """Read and parse a UTF-8 JSON file."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: Any) -> None:
    """Write formatted UTF-8 JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def compute_sha256_bytes(data: bytes) -> str:
    """Return hex SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_file_sha256(path: Path) -> str:
    """Return hex SHA-256 digest of an existing file, or empty string if missing."""
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_cache_key(payload: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 cache key from canonicalized JSON inputs."""
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return compute_sha256_bytes(serialized)


def is_cache_hit(output_path: Path, hash_file_path: Path, expected_key: str) -> bool:
    """Check whether both output artifact and matching cache key exist."""
    if not output_path.exists() or not hash_file_path.exists():
        return False
    stored = hash_file_path.read_text(encoding="utf-8").strip()
    return stored == expected_key


def write_cache_key(hash_file_path: Path, cache_key: str) -> None:
    """Persist the cache key sidecar file next to a generated artifact."""
    hash_file_path.parent.mkdir(parents=True, exist_ok=True)
    hash_file_path.write_text(cache_key + "\n", encoding="utf-8")


def log_run(
    *,
    stage: str,
    shot_id: str | None,
    model: str,
    params: dict[str, Any],
    seed: int | None,
    latency_s: float,
    cost_est: float = 0.0,
    status: str = "ok",
    note: str = "",
) -> None:
    """Append a single model/tool execution record to `runs.jsonl`."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "shot_id": shot_id,
        "model": model,
        "params": params,
        "seed": seed,
        "latency_s": round(latency_s, 3),
        "cost_est": cost_est,
        "status": status,
        "note": note,
    }
    with RUNS_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def retry_call(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    backoff_s: float = 2.0,
) -> T:
    """Execute `fn` up to `max_attempts` times with linear backoff before raising."""
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - intentional generic retry boundary
            last_error = exc
            if attempt < max_attempts:
                time.sleep(backoff_s * attempt)
    assert last_error is not None
    raise last_error


def resolve_binary(name: str) -> str:
    """Find an executable on PATH or common Windows WinGet links folder."""
    found = shutil.which(name)
    if found:
        return found
    local_app_data = os.getenv("LOCALAPPDATA", "")
    if local_app_data:
        winget_candidate = Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / f"{name}.exe"
        if winget_candidate.exists():
            return str(winget_candidate)
    raise FileNotFoundError(
        f"Required executable `{name}` was not found on PATH or in WinGet Links."
    )
