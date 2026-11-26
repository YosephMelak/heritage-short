"""FFmpeg assembly stage: radio cut (Phase 1) and dual-aspect final film (Phase 3)."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from pipeline.utils import OUTPUTS_DIR, STORYBOARD_PATH, load_json, log_run, resolve_binary

FINAL_DIR = OUTPUTS_DIR / "final"
NARRATION_DIR = OUTPUTS_DIR / "narration"
TEMP_DIR = OUTPUTS_DIR / "temp"


def _fmt_srt_time(seconds: float) -> str:
    """Format seconds as `HH:MM:SS,mmm` for SRT subtitles."""
    ms_total = max(0, int(round(seconds * 1000)))
    hrs, rem = divmod(ms_total, 3_600_000)
    mins, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def _write_srt(storyboard: dict, srt_path: Path) -> None:
    """Write sequential English subtitles matching shot timelines."""
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    cursor = 0.0
    lines: list[str] = []
    for idx, shot in enumerate(storyboard.get("shots", []), start=1):
        dur = float(shot["duration_sec"])
        subtitle = shot.get("subtitle_en", "").strip()
        if subtitle:
            start = cursor + 0.25
            end = max(start + 0.5, cursor + dur - 0.25)
            lines.append(f"{idx}\n{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n{subtitle}\n")
        cursor += dur
    srt_path.write_text("\n".join(lines), encoding="utf-8")


def _run_ffmpeg(ffmpeg_bin: str, args: list[str]) -> None:
    """Execute FFmpeg and raise a concise error on non-zero exit."""
    proc = subprocess.run(
        [ffmpeg_bin, "-y", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}):\n{proc.stderr[-800:]}")


def build_radio_cut(
    *,
    storyboard_path: Path = STORYBOARD_PATH,
    output_path: Path = FINAL_DIR / "radio_cut.mp4",
    temp_music_path: Path | None = None,
) -> Path:
    """Assemble Amharic narration over quiet placeholder music on a black screen."""
    ffmpeg_bin = resolve_binary("ffmpeg")
    storyboard = load_json(storyboard_path)
    shots = storyboard.get("shots", [])
    if not shots:
        raise RuntimeError("No shots found in storyboard.json.")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Pad each narration clip to its exact `duration_sec` with 0.35s leading breath.
    padded_clips: list[Path] = []
    for shot in shots:
        sid = shot["id"]
        dur = float(shot["duration_sec"])
        padded_wav = TEMP_DIR / f"{sid}_padded.wav"
        text = shot.get("narration_text", "").strip()
        src_wav = NARRATION_DIR / f"{sid}.wav"

        if not text:
            _run_ffmpeg(
                ffmpeg_bin,
                [
                    "-f",
                    "lavfi",
                    "-i",
                    f"anullsrc=r=48000:cl=stereo:d={dur:.3f}",
                    str(padded_wav),
                ],
            )
            padded_clips.append(padded_wav)
            continue

        if not src_wav.exists():
            raise FileNotFoundError(f"Missing narration audio: {src_wav}")

        _run_ffmpeg(
            ffmpeg_bin,
            [
                "-i",
                str(src_wav),
                "-af",
                f"adelay=350|350,apad,atrim=0:{dur:.3f},aresample=48000",
                "-ac",
                "2",
                str(padded_wav),
            ],
        )
        padded_clips.append(padded_wav)

    concat_list = TEMP_DIR / "radio_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{clip.resolve().as_posix()}'" for clip in padded_clips),
        encoding="utf-8",
    )

    narration_track = TEMP_DIR / "radio_narration.wav"
    _run_ffmpeg(
        ffmpeg_bin,
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            str(narration_track),
        ],
    )

    total_sec = sum(float(s["duration_sec"]) for s in shots)

    # 2. Generate subtle deterministic D-minor ambient placeholder bed if no temp track provided.
    music_bed = TEMP_DIR / "placeholder_bed.wav"
    if temp_music_path and temp_music_path.exists():
        _run_ffmpeg(
            ffmpeg_bin,
            [
                "-stream_loop",
                "-1",
                "-i",
                str(temp_music_path),
                "-t",
                f"{total_sec:.3f}",
                "-af",
                "aresample=48000,volume=-18dB",
                "-ac",
                "2",
                str(music_bed),
            ],
        )
    else:
        _run_ffmpeg(
            ffmpeg_bin,
            [
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=146.83:sample_rate=48000:duration={total_sec:.3f}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=220.00:sample_rate=48000:duration={total_sec:.3f}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=174.61:sample_rate=48000:duration={total_sec:.3f}",
                "-filter_complex",
                (
                    "[0:a][1:a][2:a]amix=inputs=3:normalize=0,"
                    "lowpass=f=420,volume=0.04,"
                    f"afade=t=in:st=0:d=1.5,afade=t=out:st={max(0.0, total_sec - 2.0):.3f}:d=2.0,"
                    "pan=stereo|c0=c0|c1=c0"
                ),
                str(music_bed),
            ],
        )

    # 3. Mix narration + ducked placeholder music over black 9:16 video at -14 LUFS.
    t0 = time.perf_counter()
    _run_ffmpeg(
        ffmpeg_bin,
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=1080x1920:r=24:d={total_sec:.3f}",
            "-i",
            str(narration_track),
            "-i",
            str(music_bed),
            "-filter_complex",
            (
                "[1:a]asplit=2[voice][sc];"
                "[2:a][sc]sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500[ducked];"
                "[voice][ducked]amix=inputs=2:duration=first:normalize=0,"
                "loudnorm=I=-14:TP=-1.0:LRA=11[aout]"
            ),
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "24",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path),
        ],
    )
    latency_s = time.perf_counter() - t0

    srt_path = output_path.with_suffix(".srt")
    _write_srt(storyboard, srt_path)

    log_run(
        stage="assemble_radio_cut",
        shot_id=None,
        model="ffmpeg",
        params={"total_sec": round(total_sec, 2), "output": str(output_path.name)},
        seed=None,
        latency_s=latency_s,
        status="ok",
        note=f"wrote {output_path.name} and {srt_path.name}",
    )
    print(f"[assemble] Radio cut ready: {output_path} ({total_sec:.2f}s)")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble radio cut or final 9:16 + 16:9 films.")
    parser.add_argument(
        "--mode",
        choices=["radio-cut", "final"],
        default="final",
        help="Assembly mode: `radio-cut` (audio over black) or `final` (dual-ratio exports).",
    )
    parser.add_argument("--storyboard", type=Path, default=STORYBOARD_PATH)
    parser.add_argument("--temp-music", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.mode == "radio-cut":
        try:
            build_radio_cut(storyboard_path=args.storyboard, temp_music_path=args.temp_music)
        except Exception as exc:  # noqa: BLE001
            print(f"Radio cut failed: {exc}", file=sys.stderr)
            return 1
        return 0

    print("pipeline.assemble --mode final is scheduled for Phase 3 (after Phase 2 assets).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
