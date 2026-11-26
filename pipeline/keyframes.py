"""Reference sheet and per-shot keyframe generator via Cloudflare Workers AI (FLUX.2 klein / FLUX.1 schnell)."""

from __future__ import annotations

import argparse
import base64
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

from pipeline.utils import (
    OUTPUTS_DIR,
    STORYBOARD_PATH,
    compute_cache_key,
    compute_file_sha256,
    is_cache_hit,
    load_env,
    load_json,
    log_run,
    retry_call,
    write_cache_key,
)

REFS_DIR = OUTPUTS_DIR / "refs"
KEYFRAMES_DIR = OUTPUTS_DIR / "keyframes"

# Prefer Apache 2.0 licensed models (`flux-2-klein-4b` and `flux-1-schnell`).
DEFAULT_IMAGE_MODELS = [
    "@cf/black-forest-labs/flux-2-klein-4b",
    "@cf/black-forest-labs/flux-1-schnell",
]


def _call_cloudflare_flux(
    *,
    account_id: str,
    api_token: str,
    model: str,
    prompt: str,
    seed: int,
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
) -> tuple[bytes, float]:
    """Call Cloudflare Workers AI FLUX endpoint and return (image_bytes, latency_s)."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {api_token}"}

    t0 = time.perf_counter()
    if "flux-2-klein" in model:
        # FLUX.2 klein models on Cloudflare Workers AI expect multipart/form-data.
        files = {
            "prompt": (None, prompt),
            "width": (None, str(width)),
            "height": (None, str(height)),
            "steps": (None, str(steps)),
            "seed": (None, str(seed)),
        }
        resp = requests.post(url, headers=headers, files=files, timeout=90)
    else:
        payload = {
            "prompt": prompt,
            "steps": steps,
            "seed": seed,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=90)

    latency_s = time.perf_counter() - t0
    if resp.status_code != 200:
        raise RuntimeError(f"Cloudflare {model} HTTP {resp.status_code}: {resp.text[:250]}")

    content_type = resp.headers.get("Content-Type", "").lower()
    if "application/json" in content_type:
        data = resp.json()
        b64_img = data.get("result", {}).get("image")
        if not b64_img:
            raise RuntimeError(f"Unexpected Cloudflare JSON response for {model}: {str(data)[:220]}")
        return base64.b64decode(b64_img), latency_s
    return resp.content, latency_s


def _generate_with_fallback(
    *,
    account_id: str,
    api_token: str,
    models: list[str],
    prompt: str,
    seed: int,
    width: int,
    height: int,
    steps: int,
) -> tuple[bytes, str, float]:
    """Try preferred FLUX models in order with retries."""
    last_err: Exception | None = None
    for model in models:
        try:
            img_bytes, latency_s = retry_call(
                lambda m=model: _call_cloudflare_flux(
                    account_id=account_id,
                    api_token=api_token,
                    model=m,
                    prompt=prompt,
                    seed=seed,
                    width=width,
                    height=height,
                    steps=steps,
                ),
                max_attempts=3,
                backoff_s=2.0,
            )
            return img_bytes, model, latency_s
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"[keyframes] {model} failed ({exc}); trying fallback if available...")
    assert last_err is not None
    raise last_err


def generate_reference_candidates(
    *,
    storyboard: dict[str, Any],
    account_id: str,
    api_token: str,
    models: list[str],
    candidates: int = 3,
    width: int = 1024,
    height: int = 1024,
) -> Path:
    """Generate character/style reference candidates and ensure `golden_ref.png` exists."""
    REFS_DIR.mkdir(parents=True, exist_ok=True)
    char_ref = storyboard["character_ref"]
    style_block = storyboard["style_block"]
    golden_path = Path(char_ref["image_path"])
    if not golden_path.is_absolute():
        golden_path = (STORYBOARD_PATH.parent / golden_path).resolve()

    base_seed = int(char_ref["seed"])
    full_prompt = f"{char_ref['prompt']} {style_block}".strip()

    first_candidate: Path | None = None
    for idx in range(1, candidates + 1):
        seed = base_seed + idx - 1
        cand_path = REFS_DIR / f"ref_{idx:02d}.png"
        hash_path = REFS_DIR / f"ref_{idx:02d}.sha256"
        cache_key = compute_cache_key(
            {"kind": "ref", "prompt": full_prompt, "seed": seed, "width": width, "height": height}
        )
        if is_cache_hit(cand_path, hash_path, cache_key):
            print(f"[keyframes] ref_{idx:02d}: cache hit")
        else:
            img_bytes, used_model, latency_s = _generate_with_fallback(
                account_id=account_id,
                api_token=api_token,
                models=models,
                prompt=full_prompt,
                seed=seed,
                width=width,
                height=height,
                steps=4,
            )
            cand_path.write_bytes(img_bytes)
            write_cache_key(hash_path, cache_key)
            log_run(
                stage="keyframes_ref",
                shot_id=None,
                model=used_model,
                params={"candidate": idx, "width": width, "height": height},
                seed=seed,
                latency_s=latency_s,
                status="ok",
                note=f"wrote {cand_path.name}",
            )
            print(f"[keyframes] ref_{idx:02d}: generated via {used_model} ({latency_s:.2f}s)")
        if first_candidate is None:
            first_candidate = cand_path

    if not golden_path.exists() and first_candidate is not None:
        golden_path.write_bytes(first_candidate.read_bytes())
        print(f"[keyframes] Initialized {golden_path.name} from {first_candidate.name} (replace with chosen best candidate if desired).")
    return golden_path


def generate_keyframes(
    *,
    storyboard_path: Path = STORYBOARD_PATH,
    shot_id: str | None = None,
    ref_only: bool = False,
    candidates: int = 3,
    width: int = 1024,
    height: int = 1024,
    model_override: str | None = None,
) -> None:
    """Generate cached golden reference and per-shot keyframes."""
    load_env()
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or not api_token:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required in `.env`.")

    storyboard = load_json(storyboard_path)
    models = [model_override] if model_override else list(DEFAULT_IMAGE_MODELS)
    golden_path = generate_reference_candidates(
        storyboard=storyboard,
        account_id=account_id,
        api_token=api_token,
        models=models,
        candidates=candidates,
        width=width,
        height=height,
    )
    if ref_only:
        return

    KEYFRAMES_DIR.mkdir(parents=True, exist_ok=True)
    style_block = storyboard["style_block"]
    char_prompt = storyboard["character_ref"]["prompt"]
    golden_sha = compute_file_sha256(golden_path)

    for shot in storyboard.get("shots", []):
        sid = shot["id"]
        if shot_id and sid != shot_id:
            continue

        out_path = KEYFRAMES_DIR / f"{sid}.png"
        hash_path = KEYFRAMES_DIR / f"{sid}.sha256"
        seed = int(shot["seed"])
        prompt = f"{shot['visual_prompt']} Consistent character/look context: {char_prompt} Style: {style_block}".strip()
        cache_key = compute_cache_key(
            {
                "shot_id": sid,
                "prompt": prompt,
                "seed": seed,
                "golden_sha": golden_sha,
                "width": width,
                "height": height,
                "models": models,
            }
        )
        if is_cache_hit(out_path, hash_path, cache_key):
            print(f"[keyframes] {sid}: cache hit")
            continue

        img_bytes, used_model, latency_s = _generate_with_fallback(
            account_id=account_id,
            api_token=api_token,
            models=models,
            prompt=prompt,
            seed=seed,
            width=width,
            height=height,
            steps=4,
        )
        out_path.write_bytes(img_bytes)
        write_cache_key(hash_path, cache_key)
        log_run(
            stage="keyframes",
            shot_id=sid,
            model=used_model,
            params={"width": width, "height": height},
            seed=seed,
            latency_s=latency_s,
            status="ok",
            note=f"wrote {out_path.name}",
        )
        print(f"[keyframes] {sid}: generated via {used_model} ({latency_s:.2f}s)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate reference sheet and per-shot keyframes.")
    parser.add_argument("--storyboard", type=Path, default=STORYBOARD_PATH)
    parser.add_argument("--shot", help="Optional single shot ID (e.g. shot_01) to regenerate.")
    parser.add_argument("--ref-only", action="store_true", help="Only generate reference sheet candidates.")
    parser.add_argument("--candidates", type=int, default=3)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--model", help="Optional explicit Cloudflare Workers AI model ID.")
    args = parser.parse_args(argv)

    try:
        generate_keyframes(
            storyboard_path=args.storyboard,
            shot_id=args.shot,
            ref_only=args.ref_only,
            candidates=args.candidates,
            width=args.width,
            height=args.height,
            model_override=args.model,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Keyframes stage failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
