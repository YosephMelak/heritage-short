"""Run on Kaggle (T4 x2 / P100) or Google Colab to generate 3 ACE-Step 1.5 score candidates."""
import json
import shutil
import time
from pathlib import Path

# Run once in Notebook Cell 1 (requires GPU + Internet ON):
# !git clone https://github.com/ACE-Step/ACE-Step-1.5.git
# !pip install -q -e ACE-Step-1.5

CAPTION = 'Atmospheric nocturnal Ethiopian acoustic score, deep resonant krar bass plucks, subtle traditional Harari percussive pulse, and haunting washint flute notes, building from quiet night tension to grounded reverence and peace, spacious under Amharic narration, no vocals'
BPM = 72
KEY = 'D minor'
INSTRUMENTAL = True
BASE_SEED = 5401
DURATION_SEC = 76
NUM_CANDIDATES = 3

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
        "Install ACE-Step 1.5 first:\n"
        "  git clone https://github.com/ACE-Step/ACE-Step-1.5.git\n"
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
    out_wav = OUT_DIR / f"candidate_{i + 1:02d}.wav"
    if out_wav.exists():
        print(f"Skipping existing {out_wav.name}")
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
        save_dir=str(OUT_DIR / f"_tmp_{i + 1:02d}"),
    )
    dt = time.perf_counter() - t0
    if not getattr(result, "success", False) or not getattr(result, "audios", None):
        raise RuntimeError(f"ACE-Step 1.5 failed on candidate {i + 1}: {getattr(result, 'error', 'unknown error')}")

    src_audio = Path(result.audios[0]["path"])
    shutil.copy2(src_audio, out_wav)
    logs.append({"candidate": out_wav.name, "seed": seed, "latency_s": round(dt, 3)})
    print(f"Generated {out_wav.name} in {dt:.2f}s (seed={seed})")

(OUT_DIR / "music_runs.json").write_text(json.dumps(logs, indent=2), encoding="utf-8")
print("Done! Download files from:", OUT_DIR)
