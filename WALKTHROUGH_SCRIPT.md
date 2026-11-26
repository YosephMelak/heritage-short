# 5-Minute Walkthrough Recording Script (Target: `4:30 – 4:50`, Strictly `<= 5:00`)

> **Setup Before Pressing Record:**
> - Open VS Code / terminal at `D:\TRP\AI-Content Generation\heritage-short\` with font large enough to read easily.
> - Have open tabs ready: `storyboard.json`, `pipeline/run.py`, `pipeline/shots.py`, `runs.jsonl`, and `outputs/final/film_9x16.mp4` (`outputs/final/film_16x9.mp4`).
> - Activate `.venv` or run with `.\.venv\Scripts\python.exe`.

---

## `[0:00 – 1:30]` Architecture & Single `storyboard.json` Contract (`~1.5 min`)
1. Show `README.md` / folder tree (`storyboard.json`, `schema/storyboard.schema.json`, `pipeline/`, `runs.jsonl`, `outputs/`).
2. Scroll through `storyboard.json` lines `1–65` pointing out:
   - `title`, `language: "Amharic"`, `target_duration_sec: 72.26`, `style_block`, `character_ref`.
   - Each shot's **`shot_reason`**, **`visual_prompt`**, **`camera_motion`**, **`narration_text`**, **`subtitle_en`**, **`music_cue`**, **`seed`**, and **`consent_verified: true`**.
3. Show `pipeline/run.py` explaining the sequential contract:
   - `validate` (JSON Schema + `60–90s` duration check + consent gate) -> `narration` (Gemini TTS + auto duration sync) -> `keyframes` (Cloudflare FLUX.2 klein 4B) -> `music` (score selection) -> `shots` (Wan 2.2 / `4x` supersampled FFmpeg motion) -> `assemble` (sidechain ducking, `-14 LUFS`, subtitles, dual `9:16` & `16:9` MP4 exports).

---

## `[1:30 – 2:30]` One Hard Decision & Failure Fix (`~1.0 min`)
Open `FAILURES.md` (`FAIL-05`, `FAIL-06`, `FAIL-07`) + `EXPERIMENTS.md` (`EXP-12`, `EXP-14`):
- Explain briefly (pick your sharpest story):
  - How Kaggle/Colab/HF free GPUs stalled on submission day (`>67 min` queue) and Cloudflare `flux-2-klein-4b` locked composition when `input_image_0` was attached to all shots, **plus** how Amharic `ጠባቂውም` softened at `0:19` (`EXP-12` User Test #1 feedback).
  - Show how SHA-256 caching + decoupled fallbacks (`facebook/musicgen-small`, `4x` supersampled shot-matched FFmpeg motion, and `9:16` blurred-atmosphere cinema framing so characters aren't cropped) solved it cleanly while keeping `outputs/` 100% reproducible.

---

## `[2:30 – 4:40]` Live Single-Shot Regeneration & Cache-Skip Proof (`~2.0 min`)
1. Run baseline cached check in terminal to show all shots are currently cached:
   ```powershell
   .\.venv\Scripts\python.exe -m pipeline.shots
   ```
   Point out on screen: `[shots] shot_01..shot_08: cache hit (skipping)`.
2. Edit **one single field** in `storyboard.json` live (e.g., change `shot_06` `camera_motion` slightly from `"Locked-off camera, subtle nod and flickering lantern light."` to `"Locked-off camera, gentle nod and warm flickering lantern glow."` — **or** tweak `shot_06` `seed` `6446 -> 6447`).
   *(Tip: Changing `shot_06`'s `camera_motion` only invalidates `shot_06` in `pipeline.shots` so you don't even burn an API key on camera, OR changing `shot_06`'s `visual_prompt` regenerates ONLY `shot_06` keyframe + `shot_06` clip in ~12 seconds!)*
3. Run:
   ```powershell
   .\.venv\Scripts\python.exe -m pipeline.keyframes
   .\.venv\Scripts\python.exe -m pipeline.shots --fallback-ken-burns
   ```
4. Highlight the terminal output:
   - `shot_01`–`05`, `07`–`08`: **`cache hit`** (skipped in milliseconds!)
   - **ONLY `shot_06`** regenerated!
5. Print the last 2 lines of `runs.jsonl` (`Get-Content runs.jsonl -Tail 3`) showing the single fresh logged call (`stage`, `shot_id: "shot_06"`, `latency_s`)!
6. *(Optional)* Revert the temporary test edit or keep cleanly if intentional, and briefly play 5 seconds of `outputs/final/film_9x16.mp4` to close cleanly under `5:00`!
