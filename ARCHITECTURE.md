# Pipeline Architecture

## 1. Overview & `storyboard.json` Contract

`storyboard.json` is the single contract shared across every stage, validated against `schema/storyboard.schema.json` before execution via `pipeline/validate.py`.

```text
storyboard.json
  ├──> pipeline/validate.py   (Schema + 60–90s duration sum + consent gate)
  ├──> pipeline/narration.py  (Gemini 3.8 Flash TTS -> outputs/narration/ + duration sync)
  ├──> pipeline/keyframes.py  (Golden ref -> outputs/refs/ -> per-shot outputs/keyframes/)
  ├──> pipeline/music.py      (ACE-Step 1.5 candidates -> outputs/music/)
  ├──> pipeline/shots.py      (Wan 2.2 480p I2V / Ken Burns fallback -> outputs/shots/)
  └──> pipeline/assemble.py   (FFmpeg mix, ducking, -14 LUFS, subtitles, end card -> 9:16 & 16:9)
```

## 2. Stage Contracts & Single-Shot Regeneration

Each stage reads `storybo"Keeper of the Hyenas: A Night in Harar" (የጅቦቹ ጠባቂ፡ አንድ ምሽት በሐረር) is the strongest choice for a captivating story because it offers immediate sensory tension, a rare living tradition, and an unforgettable nocturnal setting inside the historic walled city of Harar Jugol. Here are the Amharic translations and story angles for your three choices:ard.json` and writes per-shot artifacts keyed by `shot_id`. Updating one shot's `visual_prompt`, `camera_motion`, `narration_text`, `seed`, or `duration_sec` only invalidates that shot.

## 3. Deterministic SHA-256 Caching

In `pipeline/shots.py` (and asset stages), a SHA-256 digest is computed from the canonical input parameters:
`(keyframe_hash, visual_prompt, camera_motion, duration_sec, video_model, draft_resolution, seed)`.
The digest is stored in a sidecar hash file. On re-run, if the output file exists and the stored hash matches, generation is skipped.

## 4. Retry Logic & Fallbacks

- API/GPU calls use bounded retries (`max_attempts = 3`) in `pipeline/utils.py`.
- Moving-shot generation caps retries at 3 attempts per shot and falls back to FFmpeg `zoompan` (Ken Burns) motion over the approved keyframe if a clip fails or GPU quota runs low.
- Every model call appends an audit record to `runs.jsonl`.
