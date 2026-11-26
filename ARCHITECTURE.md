# Pipeline Architecture

## 1. Overview & `storyboard.json` Contract

`storyboard.json` is the single contract shared across every stage, validated against `schema/storyboard.schema.json` before any stage runs in `pipeline/validate.py`.

```text
storyboard.json
  ├──> pipeline/validate.py   (JSON Schema + 60–90s duration sum + consent_verified gate)
  ├──> pipeline/narration.py  (Gemini TTS 4-model fallback cascade -> outputs/narration/ + duration sync)
  ├──> pipeline/keyframes.py  (Cloudflare Workers AI FLUX.2 klein / FLUX.1 schnell -> refs/ + keyframes/)
  ├──> pipeline/music.py      (ACE-Step 1.5 Kaggle/Colab job & track selection -> outputs/music/)
  ├──> pipeline/shots.py      (Wan 2.2 TI2V-5B 480p ingest / FFmpeg Ken Burns fallback -> outputs/shots/)
  └──> pipeline/assemble.py   (Radio Cut OR Final 9:16 + 16:9 with ducking, -14 LUFS, subtitles, AI end card)
```

Executed end-to-end from a clean clone via `make film` or `python -m pipeline.run`.

---

## 2. Stage Boundaries & Single-Shot Regeneration

- Each stage reads `storyboard.json` and writes deterministic per-shot files (`shot_01.*`–`shot_08.*`) plus sidecar `.sha256` cache keys.
- Changing one shot's `narration_text` invalidates only that shot's key in `pipeline/narration.py`, `pipeline/shots.py`, and final assembly.
- Changing one shot's `visual_prompt`, `camera_motion`, or `seed` invalidates only that shot in `pipeline/keyframes.py` and `pipeline/shots.py` while all other cached shots are skipped.

---

## 3. Deterministic SHA-256 Caching

In `pipeline/utils.py`, `compute_cache_key()` serializes canonical JSON (`sort_keys=True`) and computes a SHA-256 hex digest:
- **Narration (`pipeline/narration.py`):** `(shot_id, language, narration_text, voice_name, style_cue, model)`. Intentional silent shots (`narration_text == ""`, e.g., `shot_06`) skip API calls cleanly.
- **Keyframes (`pipeline/keyframes.py`):** `(shot_id, prompt, seed, golden_ref_sha256, width, height, models)`.
- **Moving Shots (`pipeline/shots.py`):** `(shot_id, keyframe_sha256, visual_prompt, camera_motion, duration_sec, video_model, draft_resolution, seed)`.

On re-run, if both the output file and matching `.sha256` sidecar exist, generation is skipped and no API/GPU call is made.

---

## 4. Retry Logic, Quota Fallbacks & Failure Handling

- **Bounded Retries:** `retry_call()` in `pipeline/utils.py` retries transient errors up to 3 attempts with linear backoff.
- **TTS Daily-Quota Cascade:** `pipeline/narration.py` parses `429` retry delays and automatically cascades across `gemini-3.8-flash-tts` -> `gemini-3.8-flash-lite-tts` -> `gemini-3.1-flash-tts-preview` -> `gemini-2.5-flash-preview-tts` on `DAILY_QUOTA_429`.
- **Image Model Fallback:** `pipeline/keyframes.py` prefers Apache 2.0 `@cf/black-forest-labs/flux-2-klein-4b` and falls back to `@cf/black-forest-labs/flux-1-schnell` on errors.
- **Video Fallback:** `pipeline/shots.py` accepts Kaggle `Wan 2.2 TI2V-5B` 480p clips via `--ingest-dir` and provides varied-direction FFmpeg `zoompan` (Ken Burns) rendering (`--fallback-ken-burns`) when GPU quota or clips are unavailable.
- **Audit Trail:** Every model/FFmpeg execution appends a JSON record to `runs.jsonl`.
