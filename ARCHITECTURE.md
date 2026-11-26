# Pipeline Architecture

## 1. Overview & `storyboard.json` Contract

`storyboard.json` is the single contract shared across every stage, validated against `schema/storyboard.schema.json` before any stage runs in `pipeline/validate.py`.

```text
storyboard.json
  ├──> pipeline/validate.py   (JSON Schema + 60–90s duration sum + consent_verified gate)
  ├──> pipeline/narration.py  (Gemini TTS 4-model fallback cascade -> outputs/narration/ + duration sync)
  ├──> pipeline/keyframes.py  (Cloudflare Workers AI FLUX.2 klein 4B + curated stills -> refs/ + keyframes/)
  ├──> pipeline/music.py      (ACE-Step 1.5 Kaggle/Colab job emitter + candidate selector -> chosen_score.wav)
  ├──> pipeline/shots.py      (Wan 2.2 TI2V-5B 1280*704 ingest / 4x-supersampled FFmpeg Ken Burns fallback -> shots/)
  └──> pipeline/assemble.py   (Radio Cut OR Final 9:16 cinema-blur & 16:9 widescreen, ducked score, -14 LUFS, SRT subtitles, closing card)
```

Executed end-to-end from a clean clone via `make film` or `python -m pipeline.run`.

---

## 2. Stage Boundaries & Single-Shot Regeneration

- Each stage reads `storyboard.json` and writes deterministic per-shot files (`shot_01.*`–`shot_08.*`) plus sidecar `.sha256` cache keys.
- Changing one shot's `narration_text` invalidates only that shot's key in `pipeline/narration.py`, `pipeline/shots.py`, and final assembly.
- Changing one shot's `visual_prompt`, `camera_motion`, or `seed` invalidates only that shot in `pipeline/keyframes.py` and `pipeline/shots.py` while all other cached shots are skipped.
- Credentials (`GEMINI_API_KEY`, `CLOUDFLARE_API_TOKEN`) are checked **lazily on cache misses**, so a clean clone with repository outputs runs `python -m pipeline.run` end-to-end with zero secrets configured.

---

## 3. Deterministic SHA-256 Caching

In `pipeline/utils.py`, `compute_cache_key()` serializes canonical JSON (`sort_keys=True`) and computes a SHA-256 hex digest:
- **Narration (`pipeline/narration.py`):** `(shot_id, language, narration_text, voice_name, style_cue, model)`. Intentional silent shots (`narration_text == ""`, e.g., `shot_06`) skip API calls cleanly.
- **Keyframes (`pipeline/keyframes.py`):** `(shot_id, prompt, seed, ref_sha, width, height, models)` for generated edits (`1024x576`), or `(shot_id, curated_sha, prompt, width, height)` for curated visual anchors (`outputs/refs/curated/`).
- **Moving Shots (`pipeline/shots.py`):** `(shot_id, keyframe_sha256, visual_prompt, camera_motion, duration_sec, video_model, draft_resolution, seed)`.

On re-run, if both the output file and matching `.sha256` sidecar exist, generation is skipped and no API/GPU call is made.

---

## 4. Retry Logic, Fallbacks & Dual-Aspect Assembly

- **Bounded Retries:** `retry_call()` in `pipeline/utils.py` retries transient errors up to 3 attempts with linear backoff.
- **TTS Daily-Quota Cascade:** `pipeline/narration.py` parses `429` retry delays and cascades across `gemini-3.8-flash-tts` -> `gemini-3.8-flash-lite-tts` -> `gemini-3.1-flash-tts-preview` -> `gemini-2.5-flash-preview-tts` on `DAILY_QUOTA_429`.
- **Image Conditioning Gate:** `pipeline/keyframes.py` uses `@cf/black-forest-labs/flux-2-klein-4b` (Apache 2.0, `1024x576`) with `flux-1-schnell` fallback, anchoring generated shots to composition-matched `input_image_0` references (`SHOT_EDIT_REFS`) so character wardrobe and lighting never drift.
- **Video & Music Resilience:** `pipeline/shots.py` generates a `Wan 2.2 TI2V-5B` Kaggle batch script (`1280*704`, `--offload_model True --convert_model_dtype --t5_cpu`) and cleanly falls back to `4x` (`3840x2160`) supersampled shot-matched FFmpeg `zoompan` (`1280x720`, `24 fps`, `-crf 16`) when cloud GPU queues stall. `pipeline/music.py` supports `ACE-Step 1.5` remote jobs and Meta `facebook/musicgen-small` candidate selection (`CC-BY-NC 4.0`).
- **Dual-Aspect Assembly (`pipeline/assemble.py`):**
  - **Audio:** Sidechain compression (`threshold=0.02`, `ratio=6`, `attack=300`, `release=1500`) ducks the instrumental score under voice, followed by two-pass FFmpeg `loudnorm` mastering to **`-14.06 LUFS` / `-0.95 dBTP`**.
  - **Video:** `16:9` exports full-bleed `1920x1080 @ 24 fps`; `9:16` exports full-width `1080x608` picture over a downscaled Gaussian-blurred nocturnal fill (`1080x1920`) so wide two-shots retain 100% subject visibility while burned-in English subtitles sit safely beneath the frame (`MarginV=52`). Windows FFmpeg `Fontconfig` isolation emits a scoped `outputs/temp/fonts.conf`.
- **Audit Trail:** Every model/FFmpeg execution appends a JSON record to `runs.jsonl`.
