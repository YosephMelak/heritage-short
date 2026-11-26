"""Run on Kaggle (2x T4) or Colab with Wan 2.2 TI2V-5B at 480p.
Saves each clip immediately after completion so session timeouts never lose progress.
"""
import json
import subprocess
import time
from pathlib import Path

JOBS = [
  {
    "id": "shot_01",
    "keyframe": "keyframes/shot_01.png",
    "motion_prompt": "Gentle slow push-in toward the lantern-lit pair as night mist drifts softly. Subtle natural atmospheric motion.",
    "duration_sec": 10.21,
    "seed": 6401
  },
  {
    "id": "shot_02",
    "keyframe": "keyframes/shot_02.png",
    "motion_prompt": "Slow steady push-in over the keeper's steady hands and woven basket. Subtle natural atmospheric motion.",
    "duration_sec": 7.56,
    "seed": 6412
  },
  {
    "id": "shot_03",
    "keyframe": "keyframes/shot_03.png",
    "motion_prompt": "Very slow gentle push-in on Umar's serene, focused face. Subtle natural atmospheric motion.",
    "duration_sec": 12.98,
    "seed": 6413
  },
  {
    "id": "shot_04",
    "keyframe": "keyframes/shot_04.png",
    "motion_prompt": "Locked-off camera holding cleanly on the calm, respectful exchange. Subtle natural atmospheric motion.",
    "duration_sec": 9.31,
    "seed": 6444
  },
  {
    "id": "shot_05",
    "keyframe": "keyframes/shot_05.png",
    "motion_prompt": "Slow steady push-in as Dawit's expression shifts from hesitation to quiet courage. Subtle natural atmospheric motion.",
    "duration_sec": 8.21,
    "seed": 6405
  },
  {
    "id": "shot_06",
    "keyframe": "keyframes/shot_06.png",
    "motion_prompt": "Locked-off camera, subtle nod and flickering lantern light. Subtle natural atmospheric motion.",
    "duration_sec": 5.5,
    "seed": 6446
  },
  {
    "id": "shot_07",
    "keyframe": "keyframes/shot_07.png",
    "motion_prompt": "Gentle slow side drift keeping Dawit, Umar, and the hyena inside the central safe frame. Subtle natural atmospheric motion.",
    "duration_sec": 7.97,
    "seed": 6417
  },
  {
    "id": "shot_08",
    "keyframe": "keyframes/shot_08.png",
    "motion_prompt": "Slow gentle pull-back revealing the ancient silhouette of Harar Jugol under moonlight. Subtle natural atmospheric motion.",
    "duration_sec": 10.52,
    "seed": 6428
  }
]
WAN_REPO = Path("Wan2.2")  # git clone https://github.com/Wan-Video/Wan2.2.git
CKPT_DIR = Path("Wan2.2-TI2V-5B")  # huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir Wan2.2-TI2V-5B
OUT_DIR = Path("wan_clips")
OUT_DIR.mkdir(parents=True, exist_ok=True)

logs = []
for job in JOBS:
    sid = job["id"]
    out_mp4 = OUT_DIR / f"{sid}.mp4"
    if out_mp4.exists():
        print(f"Skipping existing {out_mp4}")
        continue
    t0 = time.perf_counter()
    cmd = [
        "python",
        str(WAN_REPO / "generate.py"),
        "--task", "ti2v-5B",
        "--size", "1280*704",
        "--ckpt_dir", str(CKPT_DIR),
        "--offload_model", "True",
        "--convert_model_dtype",
        "--t5_cpu",
        "--image", job["keyframe"],
        "--prompt", job["motion_prompt"],
        "--base_seed", str(job["seed"]),
        "--save_file", str(out_mp4),
    ]
    subprocess.run(cmd, check=True)
    dt = time.perf_counter() - t0
    logs.append({"shot_id": sid, "model": "wan-2.2", "seed": job["seed"], "latency_s": round(dt, 3)})
    (OUT_DIR / "wan_runs.json").write_text(json.dumps(logs, indent=2), encoding="utf-8")
    print(f"Saved {out_mp4} in {dt:.2f}s")
