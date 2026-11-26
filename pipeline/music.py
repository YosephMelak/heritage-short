"""Original score candidate management & Kaggle/Colab ACE-Step 1.5 script generator."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from pipeline.utils import OUTPUTS_DIR, STORYBOARD_PATH, load_json, log_run

MUSIC_DIR = OUTPUTS_DIR / "music"


def emit_kaggle_script(storyboard: dict, *, candidates: int = 3) -> Path:
    """Write a self-contained Kaggle/Colab Python script for ACE-Step 1.5 candidate generation."""
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    music_cfg = storyboard["music"]
    duration_sec = int(round(float(storyboard["target_duration_sec"])))
    script_path = MUSIC_DIR / "acestep_kaggle_job.py"

    # Tempo (BPM), musical keyscale, and instrumental mode go in GenerationParams metadata fields.
    content = f'''"""Run on Kaggle (T4 x2 / P100) or Google Colab to generate {candidates} ACE-Step 1.5 score candidates."""
import json
import shutil
import time
from pathlib import Path

# Run once in Notebook Cell 1 (requires GPU + Internet ON):
# !git clone https://github.com/ACE-Step/ACE-Step-1.5.git
# !pip install -q -e ACE-Step-1.5

CAPTION = {music_cfg["caption"]!r}
BPM = {int(music_cfg["bpm"])}
KEY = {music_cfg["key"]!r}
INSTRUMENTAL = {bool(music_cfg["instrumental"])}
BASE_SEED = {int(music_cfg["seed"])}
DURATION_SEC = {min(90, max(30, duration_sec + 3))}
NUM_CANDIDATES = {candidates}

REPO_DIR = Path("ACE-Step-1.5").resolve()
CKPT_DIR = (REPO_DIR / "checkpoints").resolve()
OUT_DIR = Path("acestep_candidates").resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music
    from acestep.llm_inference import LLMHandler
except ImportError as exc:
    raise SystemExit(
        "Install ACE-Step 1.5 first:\\n"
        "  git clone https://github.com/ACE-Step/ACE-Step-1.5.git\\n"
        "  pip install -e ACE-Step-1.5"
    ) from exc

project_root = str(REPO_DIR if REPO_DIR.exists() else Path.cwd())
dit_handler = AceStepHandler()
dit_handler.initialize_service(
    project_root=project_root,
    config_path="acestep-v15-turbo",
    device="cuda",
)

llm_handler = LLMHandler()
llm_handler.initialize(
    checkpoint_dir=str(CKPT_DIR),
    lm_model_path="acestep-5Hz-lm-0.6B",
    backend="pt",
    device="cuda",
)

logs = []
for i in range(NUM_CANDIDATES):
    seed = BASE_SEED + i
    out_wav = OUT_DIR / f"candidate_{{i + 1:02d}}.wav"
    if out_wav.exists():
        print(f"Skipping existing {{out_wav.name}}")
        continue

    params = GenerationParams(
        caption=CAPTION,
        instrumental=INSTRUMENTAL,
        bpm=BPM,
        keyscale=KEY,
        duration=float(DURATION_SEC),
        seed=seed,
    )
    config = GenerationConfig(
        batch_size=1,
        audio_format="wav",
        use_random_seed=False,
        seeds=[seed],
    )
    t0 = time.perf_counter()
    result = generate_music(
        dit_handler,
        llm_handler,
        params,
        config,
        save_dir=str(OUT_DIR / f"_tmp_{{i + 1:02d}}"),
    )
    dt = time.perf_counter() - t0
    if not getattr(result, "success", False) or not getattr(result, "audios", None):
        raise RuntimeError(f"ACE-Step 1.5 failed on candidate {{i + 1}}: {{getattr(result, 'error', 'unknown error')}}")

    src_audio = Path(result.audios[0]["path"])
    shutil.copy2(src_audio, out_wav)
    logs.append({{"candidate": out_wav.name, "seed": seed, "latency_s": round(dt, 3)}})
    print(f"Generated {{out_wav.name}} in {{dt:.2f}}s (seed={{seed}})")

(OUT_DIR / "music_runs.json").write_text(json.dumps(logs, indent=2), encoding="utf-8")
print("Done! Download files from:", OUT_DIR)
'''
    script_path.write_text(content, encoding="utf-8")
    return script_path


def select_candidate(*, storyboard_path: Path, candidate_name: str) -> Path:
    """Copy a chosen ACE-Step candidate WAV into `storyboard['music']['chosen_track']`."""
    storyboard = load_json(storyboard_path)
    chosen_rel = Path(storyboard["music"]["chosen_track"])
    chosen_path = chosen_rel if chosen_rel.is_absolute() else (storyboard_path.parent / chosen_rel).resolve()

    src = Path(candidate_name)
    if not src.exists():
        src = MUSIC_DIR / candidate_name
    if not src.exists():
        raise FileNotFoundError(f"Music candidate not found: {candidate_name}")

    chosen_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, chosen_path)
    log_run(
        stage="music_select",
        shot_id=None,
        model=storyboard["music"]["model"],
        params={"selected": src.name, "bpm": storyboard["music"]["bpm"], "key": storyboard["music"]["key"]},
        seed=int(storyboard["music"]["seed"]),
        latency_s=0.0,
        status="ok",
        note=f"selected {src.name} -> {chosen_path.name}",
    )
    print(f"[music] Selected {src.name} -> {chosen_path}")
    return chosen_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare ACE-Step 1.5 job or select chosen score.")
    parser.add_argument("--storyboard", type=Path, default=STORYBOARD_PATH)
    parser.add_argument("--candidates", type=int, default=3)
    parser.add_argument("--emit-job", action="store_true", help="Write Kaggle/Colab ACE-Step job script.")
    parser.add_argument("--select", help="Copy a generated candidate WAV into `chosen_track`.")
    args = parser.parse_args(argv)

    try:
        storyboard = load_json(args.storyboard)
        if args.select:
            select_candidate(storyboard_path=args.storyboard, candidate_name=args.select)
            return 0

        chosen_rel = Path(storyboard["music"]["chosen_track"])
        chosen_path = chosen_rel if chosen_rel.is_absolute() else (args.storyboard.parent / chosen_rel).resolve()
        if chosen_path.exists() and not args.emit_job:
            print(f"[music] Chosen score present: {chosen_path}")
            return 0

        script_path = emit_kaggle_script(storyboard, candidates=args.candidates)
        print(f"[music] Wrote ACE-Step Kaggle/Colab job script: {script_path}")
        if not chosen_path.exists():
            print("[music] Upload/run that script on Kaggle or Colab, download the 3 candidates to `outputs/music/`, then run `--select candidate_01.wav`.")
    except Exception as exc:  # noqa: BLE001
        print(f"Music stage failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
