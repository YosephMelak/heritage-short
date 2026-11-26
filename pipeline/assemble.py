"""FFmpeg assembly stage: radio cut (Phase 1) and dual-aspect final film (Phase 3)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from pipeline.utils import OUTPUTS_DIR, STORYBOARD_PATH, load_json, log_run, resolve_binary

FINAL_DIR = OUTPUTS_DIR / "final"
NARRATION_DIR = OUTPUTS_DIR / "narration"
SHOTS_DIR = OUTPUTS_DIR / "shots"
TEMP_DIR = OUTPUTS_DIR / "temp"


def _fmt_srt_time(seconds: float) -> str:
    """Format seconds as `HH:MM:SS,mmm` for SRT subtitles."""
    ms_total = max(0, int(round(seconds * 1000)))
    hrs, rem = divmod(ms_total, 3_600_000)
    mins, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def _write_srt(storyboard: dict[str, Any], srt_path: Path) -> None:
    """Write sequential English subtitles matching shot timelines."""
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    cursor = 0.0
    lines: list[str] = []
    cue_idx = 1
    for shot in storyboard.get("shots", []):
        dur = float(shot["duration_sec"])
        subtitle = shot.get("subtitle_en", "").strip()
        if subtitle:
            start = cursor + 0.25
            end = max(start + 0.5, cursor + dur - 0.25)
            lines.append(f"{cue_idx}\n{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n{subtitle}\n")
            cue_idx += 1
        cursor += dur
    srt_path.write_text("\n".join(lines), encoding="utf-8")


def _run_ffmpeg(ffmpeg_bin: str, args: list[str]) -> subprocess.CompletedProcess[str]:
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
    return proc


def _build_narration_track(ffmpeg_bin: str, shots: list[dict[str, Any]], tag: str) -> tuple[Path, float]:
    """Pad each shot's narration WAV (or silent span) to `duration_sec` and concatenate."""
    padded_clips: list[Path] = []
    for shot in shots:
        sid = shot["id"]
        dur = float(shot["duration_sec"])
        padded_wav = TEMP_DIR / f"{tag}_{sid}_padded.wav"
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

    concat_list = TEMP_DIR / f"{tag}_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{clip.resolve().as_posix()}'" for clip in padded_clips),
        encoding="utf-8",
    )

    narration_track = TEMP_DIR / f"{tag}_narration.wav"
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
    return narration_track, total_sec


def _build_placeholder_bed(ffmpeg_bin: str, total_sec: float, out_wav: Path, temp_music_path: Path | None) -> None:
    """Prepare a quiet D-minor ambient bed (or looped temp track) for Radio Cut."""
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
                str(out_wav),
            ],
        )
        return

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
            str(out_wav),
        ],
    )


def _two_pass_loudnorm_mix(
    *,
    ffmpeg_bin: str,
    narration_wav: Path,
    music_wav: Path,
    total_sec: float,
    out_wav: Path,
) -> None:
    """Duck music under narration via sidechaincompress and apply two-pass -14 LUFS loudnorm."""
    ducked_raw = TEMP_DIR / "ducked_mix_raw.wav"
    _run_ffmpeg(
        ffmpeg_bin,
        [
            "-i",
            str(narration_wav),
            "-i",
            str(music_wav),
            "-filter_complex",
            (
                "[0:a]asplit=2[voice][sc];"
                "[1:a][sc]sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500[ducked];"
                f"[voice][ducked]amix=inputs=2:duration=first:normalize=0,atrim=0:{total_sec:.3f}[aout]"
            ),
            "-map",
            "[aout]",
            "-ac",
            "2",
            "-ar",
            "48000",
            str(ducked_raw),
        ],
    )

    # Pass 1: measure loudness stats
    pass1 = _run_ffmpeg(
        ffmpeg_bin,
        [
            "-i",
            str(ducked_raw),
            "-af",
            "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
    )
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", pass1.stderr, flags=re.DOTALL)
    if not match:
        _run_ffmpeg(
            ffmpeg_bin,
            ["-i", str(ducked_raw), "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", str(out_wav)],
        )
        return

    stats = json.loads(match.group(0))
    # Pass 2: linear loudness normalization using measured values
    af_pass2 = (
        f"loudnorm=I=-14:TP=-1.0:LRA=11:"
        f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
        f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}:linear=true"
    )
    _run_ffmpeg(ffmpeg_bin, ["-i", str(ducked_raw), "-af", af_pass2, str(out_wav)])


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

    narration_track, total_sec = _build_narration_track(ffmpeg_bin, shots, tag="radio")
    music_bed = TEMP_DIR / "placeholder_bed.wav"
    _build_placeholder_bed(ffmpeg_bin, total_sec, music_bed, temp_music_path)

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


def _escape_ffmpeg_sub_path(path: Path) -> str:
    """Escape Windows path for FFmpeg `subtitles=` filtergraph syntax."""
    posix = path.resolve().as_posix()
    return posix.replace(":", "\\:")


def _render_aspect_export(
    *,
    ffmpeg_bin: str,
    storyboard: dict[str, Any],
    shots: list[dict[str, Any]],
    audio_mix: Path,
    srt_path: Path,
    width: int,
    height: int,
    margin_v: int,
    out_mp4: Path,
    end_card_sec: float = 2.5,
) -> float:
    """Render either 9:16 or 16:9 final film with subtitles and 2.5s AI end card."""
    tag = f"{width}x{height}"
    fitted_clips: list[Path] = []

    for shot in shots:
        sid = shot["id"]
        dur = float(shot["duration_sec"])
        clip_path = SHOTS_DIR / f"{sid}.mp4"
        if not clip_path.exists():
            raise FileNotFoundError(f"Missing video clip {clip_path}. Run `python -m pipeline.shots` first.")
        fitted = TEMP_DIR / f"{tag}_{sid}.mp4"
        _run_ffmpeg(
            ffmpeg_bin,
            [
                "-stream_loop",
                "-1",
                "-i",
                str(clip_path),
                "-t",
                f"{dur:.3f}",
                "-vf",
                f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=24",
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(fitted),
            ],
        )
        fitted_clips.append(fitted)

    # Append visible 2.5s AI disclosure end card
    end_card = TEMP_DIR / f"{tag}_endcard.mp4"
    escaped_title = storyboard["title"].split("—")[0].strip().replace(":", "\\:").replace("'", "\\'")
    _run_ffmpeg(
        ffmpeg_bin,
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c=#0e1116:s={width}x{height}:r=24:d={end_card_sec:.2f}",
            "-vf",
            (
                f"drawtext=text='Made with AI':fontcolor=white:fontsize={44 if width < height else 48}:"
                "x=(w-text_w)/2:y=(h-text_h)/2-36,"
                f"drawtext=text='{escaped_title}':fontcolor=#cccccc:fontsize={26 if width < height else 30}:"
                "x=(w-text_w)/2:y=(h-text_h)/2+28"
            ),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(end_card),
        ],
    )
    fitted_clips.append(end_card)

    concat_file = TEMP_DIR / f"{tag}_video_concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{c.resolve().as_posix()}'" for c in fitted_clips),
        encoding="utf-8",
    )

    srt_escaped = _escape_ffmpeg_sub_path(srt_path)
    t0 = time.perf_counter()
    _run_ffmpeg(
        ffmpeg_bin,
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-i",
            str(audio_mix),
            "-vf",
            (
                f"subtitles='{srt_escaped}':force_style='FontName=Arial,"
                f"FontSize={16 if width < height else 20},PrimaryColour=&H00FFFFFF,"
                f"OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
                f"Alignment=2,MarginV={margin_v}'"
            ),
            "-af",
            f"apad=pad_dur={end_card_sec:.2f}",
            "-map",
            "0:v",
            "-map",
            "1:a",
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
            str(out_mp4),
        ],
    )
    return time.perf_counter() - t0


def build_final_film(*, storyboard_path: Path = STORYBOARD_PATH) -> tuple[Path, Path]:
    """Assemble final 9:16 and 16:9 MP4s with ducked score, -14 LUFS loudness, subtitles, and AI end card."""
    ffmpeg_bin = resolve_binary("ffmpeg")
    storyboard = load_json(storyboard_path)
    shots = storyboard.get("shots", [])
    if not shots:
        raise RuntimeError("No shots found in storyboard.json.")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    narration_track, total_sec = _build_narration_track(ffmpeg_bin, shots, tag="final")
    chosen_rel = Path(storyboard["music"]["chosen_track"])
    chosen_music = chosen_rel if chosen_rel.is_absolute() else (storyboard_path.parent / chosen_rel).resolve()
    if not chosen_music.exists():
        raise FileNotFoundError(
            f"Missing chosen score at {chosen_music}. Run `python -m pipeline.music` and select a track first."
        )

    music_norm = TEMP_DIR / "final_music_norm.wav"
    _run_ffmpeg(
        ffmpeg_bin,
        [
            "-stream_loop",
            "-1",
            "-i",
            str(chosen_music),
            "-t",
            f"{total_sec:.3f}",
            "-af",
            f"aresample=48000,loudnorm=I=-20:TP=-2.0:LRA=11,afade=t=in:st=0:d=1.0,afade=t=out:st={max(0.0, total_sec - 2.0):.3f}:d=2.0",
            "-ac",
            "2",
            str(music_norm),
        ],
    )

    final_audio = TEMP_DIR / "final_audio_master.wav"
    _two_pass_loudnorm_mix(
        ffmpeg_bin=ffmpeg_bin,
        narration_wav=narration_track,
        music_wav=music_norm,
        total_sec=total_sec,
        out_wav=final_audio,
    )

    srt_path = FINAL_DIR / "final.srt"
    _write_srt(storyboard, srt_path)

    out_9x16 = FINAL_DIR / "film_9x16.mp4"
    lat_9x16 = _render_aspect_export(
        ffmpeg_bin=ffmpeg_bin,
        storyboard=storyboard,
        shots=shots,
        audio_mix=final_audio,
        srt_path=srt_path,
        width=1080,
        height=1920,
        margin_v=180,
        out_mp4=out_9x16,
    )
    log_run(
        stage="assemble_final",
        shot_id=None,
        model="ffmpeg",
        params={"aspect": "9:16", "resolution": "1080x1920", "lufs_target": -14},
        seed=None,
        latency_s=lat_9x16,
        status="ok",
        note=f"wrote {out_9x16.name}",
    )

    out_16x9 = FINAL_DIR / "film_16x9.mp4"
    lat_16x9 = _render_aspect_export(
        ffmpeg_bin=ffmpeg_bin,
        storyboard=storyboard,
        shots=shots,
        audio_mix=final_audio,
        srt_path=srt_path,
        width=1920,
        height=1080,
        margin_v=60,
        out_mp4=out_16x9,
    )
    log_run(
        stage="assemble_final",
        shot_id=None,
        model="ffmpeg",
        params={"aspect": "16:9", "resolution": "1920x1080", "lufs_target": -14},
        seed=None,
        latency_s=lat_16x9,
        status="ok",
        note=f"wrote {out_16x9.name}",
    )

    print(f"[assemble] Final exports ready: {out_9x16} & {out_16x9}")
    return out_9x16, out_16x9


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

    try:
        if args.mode == "radio-cut":
            build_radio_cut(storyboard_path=args.storyboard, temp_music_path=args.temp_music)
        else:
            build_final_film(storyboard_path=args.storyboard)
    except Exception as exc:  # noqa: BLE001
        print(f"Assembly stage failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
