"""Provider smoke test: verify credentials for Gemini, Cloudflare Workers AI, and Kaggle."""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import requests

from pipeline.utils import load_env, log_run


def _check_gemini(api_key: str) -> tuple[bool, str]:
    """Probe Gemini Text (`gemini-3.8-flash`) and TTS (`gemini-3.8-flash-tts`) via Google AI Studio."""
    headers = {"x-goog-api-key": api_key}
    details: list[str] = []

    text_ok = False
    for attempt in range(1, 3):
        t0 = time.perf_counter()
        try:
            resp = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                headers=headers,
                json={"contents": [{"parts": [{"text": "Reply with one word: OK"}]}]},
                timeout=30,
            )
            dt = time.perf_counter() - t0
            text_ok = resp.status_code == 200
            log_run(
                stage="smoke_test",
                shot_id=None,
                model="gemini-3.8-flash",
                params={"attempt": attempt, "status_code": resp.status_code},
                seed=None,
                latency_s=dt,
                status="ok" if text_ok else "error",
                note=f"HTTP {resp.status_code}" if text_ok else resp.text[:220].replace("\n", " "),
            )
            details.append(f"gemini-3.8-flash (attempt {attempt}): HTTP {resp.status_code} ({dt:.2f}s)")
            if text_ok or resp.status_code != 503:
                break
            time.sleep(2)
        except Exception as exc:  # noqa: BLE001
            details.append(f"gemini-3.8-flash: ERROR {exc}")
            break

    tts_ok, tts_msg = _check_gemini_tts(api_key, use_vertex=False)
    details.append(tts_msg)
    return (text_ok and tts_ok), " | ".join(details)


def _check_gemini_tts(api_key: str, *, use_vertex: bool) -> tuple[bool, str]:
    """Probe Gemini 3.8 Flash TTS with a tiny Amharic phrase."""
    if use_vertex:
        url = "https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-3.8-flash-tts:generateContent"
        contents: Any = [{"role": "user", "parts": [{"text": "ሰላም።"}]}]
    else:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent"
        contents = [{"parts": [{"text": "ሰላም።"}]}]

    payload = {
        "contents": contents,
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}
            },
        },
    }
    t0 = time.perf_counter()
    resp = requests.post(url, headers={"x-goog-api-key": api_key}, json=payload, timeout=30)
    dt = time.perf_counter() - t0
    ok = resp.status_code == 200
    log_run(
        stage="smoke_test",
        shot_id=None,
        model="gemini-3.8-flash-tts",
        params={"vertex": use_vertex, "status_code": resp.status_code},
        seed=None,
        latency_s=dt,
        status="ok" if ok else "error",
        note="audio generated" if ok else resp.text[:220].replace("\n", " "),
    )
    return ok, f"gemini-3.8-flash-tts: HTTP {resp.status_code} ({dt:.2f}s)"


def _check_cloudflare(account_id: str, api_token: str) -> tuple[bool, str]:
    """Verify Cloudflare Workers AI token and check FLUX model availability."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search"
    headers = {"Authorization": f"Bearer {api_token}"}
    t0 = time.perf_counter()
    try:
        resp = requests.get(url, headers=headers, params={"search": "flux"}, timeout=20)
        dt = time.perf_counter() - t0
        ok = resp.status_code == 200
        models: list[str] = []
        if ok:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("result", []) if "flux" in m.get("name", "").lower()]
        log_run(
            stage="smoke_test",
            shot_id=None,
            model="cloudflare-workers-ai",
            params={"status_code": resp.status_code, "flux_models_found": len(models)},
            seed=None,
            latency_s=dt,
            status="ok" if ok else "error",
            note=", ".join(models[:5]) if ok else resp.text[:220].replace("\n", " "),
        )
        if ok:
            return True, f"HTTP {resp.status_code} ({dt:.2f}s); FLUX models: {', '.join(models[:5])}"
        return False, f"HTTP {resp.status_code} ({dt:.2f}s): {resp.text[:200]}"
    except Exception as exc:  # noqa: BLE001
        return False, f"ERROR {exc}"


def _check_kaggle(username: str, key: str) -> tuple[bool, str]:
    """Verify Kaggle API credentials (`KGAT_` Bearer token or legacy Basic auth)."""
    url = "https://www.kaggle.com/api/v1/datasets/list"
    t0 = time.perf_counter()
    try:
        if key.startswith("KGAT_"):
            resp = requests.get(url, headers={"Authorization": f"Bearer {key}"}, params={"page": 1}, timeout=20)
        else:
            resp = requests.get(url, auth=(username, key), params={"page": 1}, timeout=20)
        dt = time.perf_counter() - t0
        ok = resp.status_code == 200
        log_run(
            stage="smoke_test",
            shot_id=None,
            model="kaggle-api",
            params={"status_code": resp.status_code, "auth_type": "bearer" if key.startswith("KGAT_") else "basic"},
            seed=None,
            latency_s=dt,
            status="ok" if ok else "error",
            note="authenticated" if ok else resp.text[:220].replace("\n", " "),
        )
        return ok, f"HTTP {resp.status_code} ({dt:.2f}s)"
    except Exception as exc:  # noqa: BLE001
        return False, f"ERROR {exc}"


def main() -> int:
    load_env()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    kaggle_user = os.getenv("KAGGLE_USERNAME", "").strip()
    kaggle_key = os.getenv("KAGGLE_KEY", "").strip()

    all_ok = True
    if gemini_key:
        ok, msg = _check_gemini(gemini_key)
        print(f"[Gemini]     {'PASS' if ok else 'FAIL'} -> {msg}")
        all_ok = all_ok and ok
    else:
        print("[Gemini]     MISSING GEMINI_API_KEY", file=sys.stderr)
        all_ok = False

    if cf_account and cf_token:
        ok, msg = _check_cloudflare(cf_account, cf_token)
        print(f"[Cloudflare] {'PASS' if ok else 'FAIL'} -> {msg}")
        all_ok = all_ok and ok
    else:
        print("[Cloudflare] MISSING CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN", file=sys.stderr)
        all_ok = False

    if kaggle_user and kaggle_key:
        ok, msg = _check_kaggle(kaggle_user, kaggle_key)
        print(f"[Kaggle]     {'PASS' if ok else 'FAIL'} -> {msg}")
        all_ok = all_ok and ok
    else:
        print("[Kaggle]     MISSING KAGGLE_USERNAME or KAGGLE_KEY", file=sys.stderr)
        all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
