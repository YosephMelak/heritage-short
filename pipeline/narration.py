"""Line-by-line Gemini 3.8 Flash TTS narration generator and duration sync."""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
import time
import wave
from pathlib import Path
from typing import Any

import requests

from pipeline.utils import (
    OUTPUTS_DIR,
    STORYBOARD_PATH,
    compute_cache_key,
    is_cache_hit,
    load_env,
    load_json,
    log_run,
    retry_call,
    save_json,
    write_cache_key,
)

TTS_MODELS = [
    "gemini-3.8-flash-tts",
    "gemini-3.8-flash-lite-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash-preview-tts",
]
DEFAULT_VOICE = "Kore"
DEFAULT_STYLE_CUE = "calm, warm, unhurried storyteller"
NARRATION_DIR = OUTPUTS_DIR / "narration"


def _wav_duration_sec(wav_path: Path) -> float:
    """Measure exact duration in seconds of a WAV file."""
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def _to_wav_bytes(raw_bytes: bytes, mime_type: str) -> bytes:
    """Ensure audio bytes have a valid RIFF WAV header."""
    if raw_bytes[:4] == b"RIFF" or "wav" in mime_type.lower():
        return raw_bytes
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(raw_bytes)
    return buf.getvalue()


def _call_gemini_tts(
    *,
    api_key: str,
    model: str,
    text: str,
    voice_name: str,
    style_cue: str,
) -> tuple[bytes, float]:
    """Call Gemini TTS REST endpoint and return (wav_bytes, latency_s)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    if "3.8" in model:
        part: dict[str, Any] = {"text": text}
        if style_cue:
            part["speechMetadata"] = {"style": style_cue}
    elif model.startswith("gemini-2.5-"):
        part = {"text": f"Read aloud only the following text calmly and warmly:\n{text}"}
    else:
        part = {"text": text}
    payload = {
        "contents": [{"role": "user", "parts": [part]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}
            },
        },
    }
    t0 = time.perf_counter()
    resp = requests.post(
        url,
        headers={"x-goog-api-key": api_key},
        json=payload,
        timeout=60,
    )
    latency_s = time.perf_counter() - t0
    if resp.status_code == 429:
        is_daily = "PerDay" in resp.text or "retryDelay" in resp.text and "h" in resp.text
        retry_hint = 30.0
        match = re.search(r"retry in (\d+(?:\.\d+)?)s", resp.text, flags=re.IGNORECASE)
        if match:
            retry_hint = max(5.0, float(match.group(1)) + 1.0)
        kind = "DAILY_QUOTA_429" if is_daily else f"RATE_LIMIT_429:{retry_hint:.1f}"
        raise RuntimeError(f"{kind}:{resp.text[:350]}")
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini TTS HTTP {resp.status_code}: {resp.text[:350]}")

    data = resp.json()
    part = data["candidates"][0]["content"]["parts"][0]["inlineData"]
    raw_bytes = base64.b64decode(part["data"])
    mime_type = part.get("mimeType", "audio/wav")
    return _to_wav_bytes(raw_bytes, mime_type), latency_s


def generate_narration(
    *,
    storyboard_path: Path = STORYBOARD_PATH,
    shot_id: str | None = None,
    voice_name: str = DEFAULT_VOICE,
    style_cue: str = DEFAULT_STYLE_CUE,
    pad_sec: float = 2.0,
) -> dict[str, Any]:
    """Generate cached line-by-line narration WAVs and sync shot durations."""
    load_env()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    storyboard = load_json(storyboard_path)
    language = storyboard.get("language", "Amharic")
    shots = storyboard.get("shots", [])

    NARRATION_DIR.mkdir(parents=True, exist_ok=True)
    measured_audio: dict[str, float] = {}
    exhausted_models: set[str] = set()

    for shot in shots:
        sid = shot["id"]
        wav_path = NARRATION_DIR / f"{sid}.wav"
        hash_path = NARRATION_DIR / f"{sid}.sha256"
        text = shot.get("narration_text", "").strip()

        if not text:
            # Intentional silent / natural-sound shot (no TTS API call needed).
            if shot_id and sid != shot_id:
                measured_audio[sid] = 0.0
            else:
                measured_audio[sid] = 0.0
                print(f"[narration] {sid}: silent/music beat (0.00s speech)")
            continue

        candidate_keys = {
            m: compute_cache_key(
                {
                    "shot_id": sid,
                    "language": language,
                    "narration_text": text,
                    "voice_name": voice_name,
                    "style_cue": style_cue,
                    "model": m,
                }
            )
            for m in TTS_MODELS
        }

        if shot_id and sid != shot_id:
            if wav_path.exists():
                measured_audio[sid] = _wav_duration_sec(wav_path)
            continue

        cached_hit = any(is_cache_hit(wav_path, hash_path, ck) for ck in candidate_keys.values())
        if cached_hit:
            dur = _wav_duration_sec(wav_path)
            measured_audio[sid] = dur
            print(f"[narration] {sid}: cache hit ({dur:.2f}s)")
            continue

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing in `.env`.")

        used_model = ""
        wav_bytes = b""
        latency_s = 0.0
        last_err: Exception | None = None

        for model in TTS_MODELS:
            if model in exhausted_models:
                continue
            for attempt in range(1, 4):
                try:
                    wav_bytes, latency_s = _call_gemini_tts(
                        api_key=api_key,
                        model=model,
                        text=text,
                        voice_name=voice_name,
                        style_cue=style_cue,
                    )
                    used_model = model
                    break
                except RuntimeError as exc:
                    last_err = exc
                    msg = str(exc)
                    if msg.startswith("DAILY_QUOTA_429:"):
                        print(f"[narration] {sid}: {model} daily free-tier quota exhausted; switching to fallback model...")
                        exhausted_models.add(model)
                        break
                    if msg.startswith("RATE_LIMIT_429:") and attempt < 3:
                        parts = msg.split(":", 2)
                        wait_s = float(parts[1])
                        print(f"[narration] {sid}: {model} rate-limited (429), sleeping {wait_s:.1f}s before retry {attempt + 1}/3...")
                        time.sleep(wait_s)
                        continue
                    if attempt < 3:
                        time.sleep(2.0 * attempt)
                        continue
                    break
            if used_model:
                break

        if not used_model:
            assert last_err is not None
            raise last_err

        wav_path.write_bytes(wav_bytes)
        write_cache_key(hash_path, candidate_keys[used_model])
        dur = _wav_duration_sec(wav_path)
        measured_audio[sid] = dur
        time.sleep(2.0)

        log_run(
            stage="narration",
            shot_id=sid,
            model=used_model,
            params={"voice": voice_name, "language": language, "audio_sec": round(dur, 3)},
            seed=None,
            latency_s=latency_s,
            status="ok",
            note=f"wrote {wav_path.name}",
        )
        print(f"[narration] {sid}: generated via {used_model} ({dur:.2f}s speech, {latency_s:.2f}s API)")

    # Sync shot durations from measured audio + breathing room, keeping silent shots untouched.
    if len(measured_audio) == len(shots):
        spoken_indices = [i for i, s in enumerate(shots) if measured_audio[s["id"]] > 0.0]
        raw_durations = [
            (measured_audio[s["id"]] + pad_sec) if measured_audio[s["id"]] > 0.0 else float(s["duration_sec"])
            for s in shots
        ]
        total = sum(raw_durations)
        if spoken_indices and total < 60.0:
            extra_per_shot = (62.0 - total) / len(spoken_indices)
            for idx in spoken_indices:
                raw_durations[idx] += extra_per_shot
        elif spoken_indices and total > 90.0:
            excess_per_shot = (total - 88.0) / len(spoken_indices)
            for idx in spoken_indices:
                sid = shots[idx]["id"]
                raw_durations[idx] = max(measured_audio[sid] + 0.5, raw_durations[idx] - excess_per_shot)

        for shot, dur in zip(shots, raw_durations):
            shot["duration_sec"] = round(dur, 2)
        storyboard["target_duration_sec"] = round(sum(s["duration_sec"] for s in shots), 2)
        save_json(storyboard_path, storyboard)
        print(
            f"[narration] Synced storyboard.json total duration = "
            f"{storyboard['target_duration_sec']:.2f}s across {len(shots)} shots."
        )

    return storyboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate per-shot narration via Gemini 3.8 Flash TTS.")
    parser.add_argument("--storyboard", type=Path, default=STORYBOARD_PATH)
    parser.add_argument("--shot", help="Optional single shot ID (e.g. shot_01) to regenerate.")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--style-cue", default=DEFAULT_STYLE_CUE)
    parser.add_argument("--pad-sec", type=float, default=2.0)
    args = parser.parse_args(argv)

    try:
        generate_narration(
            storyboard_path=args.storyboard,
            shot_id=args.shot,
            voice_name=args.voice,
            style_cue=args.style_cue,
            pad_sec=args.pad_sec,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Narration stage failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
