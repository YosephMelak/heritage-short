"""Moving-shot stage: SHA-256 caching, Kaggle Wan 2.2 TI2V-5B batch script, and FFmpeg Ken Burns fallback."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from pipeline.utils import (
    OUTPUTS_DIR,
    STORYBOARD_PATH,
    compute_cache_key,
    compute_file_sha256,
    is_cache_hit,
    load_json,
    log_run,
    resolve_binary,
    retry_call,
    save_json,
    write_cache_key,
)

KEYFRAMES_DIR = OUTPUTS_DIR / "keyframes"
SHOTS_DIR = OUTPUTS_DIR / "shots"

# Vary slow Ken Burns directions across consecutive fallback shots to avoid repetitive motion.
KEN_BURNS_MODES = [
    "zoom_in_center",
    "pan_right",
    "zoom_out_center",
    "pan_left",
]


def compute_shot_cache_key(shot: dict[str, Any], keyframe_path: Path) -> str:
    """Compute deterministic SHA-256 hash from all shot-generation inputs."""
    return compute_cache_key(
        {
            "shot_id": shot["id"],
            "keyframe_sha256": compute_file_sha256(keyframe_path),
            "visual_prompt": shot["visual_prompt"],
            "camera_motion": shot["camera_motion"],
            "duration_sec": shot["duration_sec"],
            "video_model": shot["video_model"],
            "draft_resolution": shot["draft_resolution"],
            "seed": shot["seed"],
        }
    )


def _render_ken_burns_fallback(
    *,
    keyframe_path: Path,
    out_path: Path,
    duration_sec: float,
    mode_index: int,
    fps: int = 24,
) -> float:
    """Animate a still keyframe cleanly at 480p+ square-safe resolution using FFmpeg zoompan."""
    ffmpeg_bin = resolve_binary("ffmpeg")
    frames = max(24, int(round(duration_sec * fps)))
    mode = KEN_BURNS_MODES[mode_index % len(KEN_BURNS_MODES)]

    if mode == "zoom_in_center":
        zp = f"zoompan=z='min(zoom+0.0012,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1024x1024:fps={fps}"
    elif mode == "zoom_out_center":
        zp = f"zoompan=z='if(lte(on,1),1.12,max(1.0,zoom-0.0012))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1024x1024:fps={fps}"
    elif mode == "pan_right":
        zp = f"zoompan=z='1.10':x='min(iw-iw/zoom,(iw-iw/zoom)*on/{frames})':y='ih/2-(ih/zoom/2)':d={frames}:s=1024x1024:fps={fps}"
    else:
        zp = f"zoompan=z='1.10':x='max(0,(iw-iw/zoom)*(1-on/{frames}))':y='ih/2-(ih/zoom/2)':d={frames}:s=1024x1024:fps={fps}"

    t0 = time.perf_counter()
    proc = subprocess.run(
        [
            ffmpeg_bin,
            "-y",
            "-loop",
            "1",
            "-i",
            str(keyframe_path),
            "-vf",
            zp,
            "-t",
            f"{duration_sec:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            str(out_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    latency_s = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg Ken Burns failed ({proc.returncode}): {proc.stderr[-500:]}")
    return latency_s


def emit_wan_kaggle_script(storyboard: dict[str, Any]) -> Path:
    """Write a Kaggle/Colab batch runner for Wan 2.2 TI2V-5B 480p image-to-video."""
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    script_path = SHOTS_DIR / "wan22_kaggle_batch.py"
    jobs = [
        {
            "id": s["id"],
            "keyframe": f"keyframes/{s['id']}.png",
            "motion_prompt": f"{s['camera_motion']} Subtle natural atmospheric motion.",
            "duration_sec": s["duration_sec"],
            "seed": s["seed"],
        }
        for s in storyboard.get("shots", [])
        if s.get("video_model") != "ken-burns"
    ]
    script_content = f'''"""Run on Kaggle (2x T4) or Colab with Wan 2.2 TI2V-5B at 480p.
Saves each clip immediately after completion so session timeouts never lose progress.
"""
import json
import subprocess
import time
from pathlib import Path

JOBS = {json.dumps(jobs, indent=2)}
WAN_REPO = Path("Wan2.2")  # git clone https://github.com/Wan-Video/Wan2.2.git
CKPT_DIR = Path("Wan2.2-TI2V-5B")  # huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir Wan2.2-TI2V-5B
OUT_DIR = Path("wan_clips")
OUT_DIR.mkdir(parents=True, exist_ok=True)

logs = []
for job in JOBS:
    sid = job["id"]
    out_mp4 = OUT_DIR / f"{{sid}}.mp4"
    if out_mp4.exists():
        print(f"Skipping existing {{out_mp4}}")
        continue
    t0 = time.perf_counter()
    cmd = [
        "python",
        str(WAN_REPO / "generate.py"),
        "--task", "ti2v-5B",
        "--size", "832*480",
        "--ckpt_dir", str(CKPT_DIR),
        "--image", job["keyframe"],
        "--prompt", job["motion_prompt"],
        "--base_seed", str(job["seed"]),
        "--save_file", str(out_mp4),
    ]
    subprocess.run(cmd, check=True)
    dt = time.perf_counter() - t0
    logs.append({{"shot_id": sid, "model": "wan-2.2", "seed": job["seed"], "latency_s": round(dt, 3)}})
    (OUT_DIR / "wan_runs.json").write_text(json.dumps(logs, indent=2), encoding="utf-8")
    print(f"Saved {{out_mp4}} in {{dt:.2f}}s")
'''
    script_path.write_text(script_content, encoding="utf-8")
    return script_path


def process_shots(
    *,
    storyboard_path: Path = STORYBOARD_PATH,
    shot_id: str | None = None,
    ingest_dir: Path | None = None,
    fallback_ken_burns: bool = False,
    emit_kaggle: bool = False,
) -> None:
    """Check SHA-256 caches, ingest Kaggle clips, or render Ken Burns fallbacks."""
    storyboard = load_json(storyboard_path)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    if emit_kaggle:
        script_path = emit_wan_kaggle_script(storyboard)
        print(f"[shots] Wrote Kaggle Wan 2.2 batch script: {script_path}")

    changed_cache_keys = False
    for idx, shot in enumerate(storyboard.get("shots", [])):
        sid = shot["id"]
        if shot_id and sid != shot_id:
            continue

        keyframe_path = KEYFRAMES_DIR / f"{sid}.png"
        out_mp4 = SHOTS_DIR / f"{sid}.mp4"
        hash_path = SHOTS_DIR / f"{sid}.sha256"

        if not keyframe_path.exists():
            raise FileNotFoundError(
                f"Missing keyframe {keyframe_path}. Run `python -m pipeline.keyframes` first."
            )

        expected_key = compute_shot_cache_key(shot, keyframe_path)
        if shot.get("cache_key") != expected_key:
            shot["cache_key"] = expected_key
            changed_cache_keys = True

        if is_cache_hit(out_mp4, hash_path, expected_key):
            print(f"[shots] {sid}: cache hit (skipping)")
            continue

        # 1. If Kaggle-generated clip is available in `ingest_dir`, import and cache it.
        if ingest_dir is not None:
            candidate = ingest_dir / f"{sid}.mp4"
            if candidate.exists():
                shutil.copy2(candidate, out_mp4)
                write_cache_key(hash_path, expected_key)
                log_run(
                    stage="shots",
                    shot_id=sid,
                    model=shot["video_model"],
                    params={"source": "kaggle_ingest", "resolution": shot["draft_resolution"]},
                    seed=int(shot["seed"]),
                    latency_s=0.0,
                    status="ok",
                    note=f"ingested {candidate.name}",
                )
                print(f"[shots] {sid}: ingested {candidate.name} (cached)")
                continue

        # 2. If Ken Burns fallback is requested or configured, render deterministically via FFmpeg.
        if fallback_ken_burns or shot["video_model"] == "ken-burns":
            latency_s = retry_call(
                lambda kp=keyframe_path, op=out_mp4, d=float(shot["duration_sec"]), m=idx: _render_ken_burns_fallback(
                    keyframe_path=kp,
                    out_path=op,
                    duration_sec=d,
                    mode_index=m,
                ),
                max_attempts=3,
                backoff_s=1.0,
            )
            write_cache_key(hash_path, expected_key)
            log_run(
                stage="shots",
                shot_id=sid,
                model="ffmpeg-ken-burns",
                params={"mode": KEN_BURNS_MODES[idx % len(KEN_BURNS_MODES)], "duration_sec": shot["duration_sec"]},
                seed=int(shot["seed"]),
                latency_s=latency_s,
                status="ok",
                note=f"fallback rendered {out_mp4.name}",
            )
            print(f"[shots] {sid}: rendered Ken Burns fallback ({latency_s:.2f}s)")
            continue

        raise FileNotFoundError(
            f"No cached video clip for {sid} at {out_mp4}. "
            "Run `--emit-kaggle` to generate Wan 2.2 clips on Kaggle and `--ingest-dir <dir>` to import them, "
            "or pass `--fallback-ken-burns` for FFmpeg Ken Burns fallback."
        )

    if changed_cache_keys:
        save_json(storyboard_path, storyboard)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or cache moving shots with SHA-256 input hashing.")
    parser.add_argument("--storyboard", type=Path, default=STORYBOARD_PATH)
    parser.add_argument("--shot", help="Optional single shot ID (e.g. shot_01) to process.")
    parser.add_argument("--ingest-dir", type=Path, help="Folder containing Kaggle-generated `shot_XX.mp4` clips.")
    parser.add_argument("--fallback-ken-burns", action="store_true", help="Render FFmpeg Ken Burns fallback for missing clips.")
    parser.add_argument("--emit-kaggle", action="store_true", help="Write `outputs/shots/wan22_kaggle_batch.py`.")
    args = parser.parse_args(argv)

    try:
        process_shots(
            storyboard_path=args.storyboard,
            shot_id=args.shot,
            ingest_dir=args.ingest_dir,
            fallback_ken_burns=args.fallback_ken_burns,
            emit_kaggle=args.emit_kaggle,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Shots stage failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
