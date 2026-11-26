# Walkthrough Presentation Script — Yoseph (`~4:40` Total, Strictly Under `5:00`)

> **How to Use This File:** Read the quoted **`> "..."`** lines word-for-word at a natural pace (`~130 words/min`). Follow the **`[SCREEN CUE]`** tags on what to show or run.  
> **Before Clicking Record:** Open `storyboard.json`, `pipeline/run.py`, `FAILURES.md`, `runs.jsonl`, `outputs/final/film_9x16.mp4`, and a PowerShell terminal inside `D:\TRP\AI-Content Generation\heritage-short\`.

---

## Part 1: Intro & `storyboard.json` Architecture (`0:00 – 1:35`)

`[SCREEN CUE: Show README.md & folder structure, then open storyboard.json]`

> "Hi, I'm **Yoseph**, and this is my pipeline and short film, **'Keeper of the Hyenas: A Night in Harar — የጅቦቹ ጠባቂ፡ አንድ ምሽት በሐረር'** — a 75-second Amharic-narrated story about coexistence outside Harar Jugol's ancient walls, built completely from code at **$0.00 API cost**."

`[SCREEN CUE: Scroll storyboard.json lines 1–42 showing title, style_block, character_ref, and shot_01]`

> "Everything starts with a single contract: **`storyboard.json`**, validated against a strict JSON Schema before anything runs. Every shot locks a `shot_reason`, `visual_prompt`, `camera_motion`, Amharic `narration_text`, `subtitle_en`, `music_cue`, fixed `seed`, and `consent_verified: true`. To respect privacy, my characters **Umar** and **Dawit** are strictly fictional, voiced by Gemini's synthetic `Kore` voice—no real likenesses or cloned voices."

`[SCREEN CUE: Switch tab to pipeline/run.py (29 lines)]`

> "One command—**`python -m pipeline.run`** or **`make film`**—executes six decoupled stages in sequence:
> 1. **`validate.py`** enforces the schema, 60-to-90-second total duration (`72.26s`), and consent gate.
> 2. **`narration.py`** calls **Gemini 3.8 Flash TTS** with a 4-model quota cascade and auto-syncs shot durations from the measured WAV lengths.
> 3. **`keyframes.py`** combines curated `16:9` Harar stills with **Cloudflare Workers AI `FLUX.2 klein 4B`** (`input_image_0` editing) for consistent `1024x576` frames.
> 4. **`music.py`** selects our auditioned `72 BPM`, `D minor` instrumental score—generated via **`facebook/musicgen-small`** locally after remote GPUs queued out.
> 5. **`shots.py`** animates all 8 shots using `4x`-supersampled **FFmpeg Ken Burns** motion (`1280x720`, 24 fps) alongside a ready **Wan 2.2 TI2V-5B** Kaggle batch script.
> 6. **`assemble.py`** ducks the score under the voice with `sidechaincompress`, normalizes loudness to **`-14.06 LUFS`**, burns English subtitles, adds a bilingual English-and-Amharic opening title, and exports both **`9:16`** and **`16:9`** MP4s."

---

## Part 2: One Hard Decision & Real Fixes (`1:35 – 2:45`)

`[SCREEN CUE: Open FAILURES.md briefly (FAIL-05, FAIL-06), then EXPERIMENTS.md (EXP-12, EXP-14)]`

> "My hardest challenge was handling **free-tier limits and multi-model failures without losing consistency or missing the deadline**."
>
> "First, on visuals and GPUs: attaching the golden reference image to every prompt locked `FLUX.2 klein` into one camera angle (`FAIL-05`), so I gated image conditioning only to matching compositions and kept shots consistent with ungraded documentary prompts. Then, on submission day, Kaggle GPU queues stalled past 90 minutes, Colab had no free T4 backend, and Hugging Face's `ACE-Step v1.5` button was disabled (`FAIL-06`). Because the pipeline is decoupled around `storyboard.json`, I swapped in **local `MusicGen-Small`** for three `76s` score candidates—auditioned quietly under narration (`EXP-11`)—and upgraded `shots.py` with **`4x`-supersampled shot-matched FFmpeg camera motion** (`EXP-13`)."
>
> "Second, feedback drove real edits: during **User Test #1** on the audio-only Radio Cut, Slack listeners flagged Amharic pronunciation at `0:19`—the ejective **`ጠ` in `ጠባቂውም`** sounded too soft (`EXP-12`). Adding a short lead-in comma (`'እርሱም፣ ጠባቂውም፣'`) made the consonant crisp and accurate. Later, in **User Test #2**, switching `9:16` to a **full-frame blurred-atmosphere cinema layout** (`EXP-14`) prevented cropping characters on phones, and adding the bilingual **English + Amharic opening title** (`EXP-15`) respected viewer feedback cleanly."

---

## Part 3: Live Single-Shot Regeneration & Cache Proof (`2:45 – 4:40`)

`[SCREEN CUE: Focus PowerShell terminal at D:\TRP\AI-Content Generation\heritage-short\]`

> "Now let's prove our deterministic **SHA-256 caching** live. Right now every stage hashes its inputs into sidecar `.sha256` files. Watch what happens when I run `pipeline.shots` with nothing changed:"

`[RUN IN TERMINAL:]`
```powershell
.\.venv\Scripts\python.exe -m pipeline.shots
```

> "Every single shot—`shot_01` through `shot_08`—hits cache and skips in milliseconds."

`[SCREEN CUE: Open storyboard.json at shot_06 (around line 112), change camera_motion text slightly, and SAVE (Ctrl+S):]`
- Change `"Locked-off camera, subtle nod and flickering lantern light."` -> `"Locked-off camera, gentle nod and warm flickering lantern glow."`

> "Now I'll edit just **one field** on **`shot_06`**—`camera_motion` in `storyboard.json`—save the file, and re-run `pipeline.shots --fallback-ken-burns`."

`[RUN IN TERMINAL:]`
```powershell
.\.venv\Scripts\python.exe -m pipeline.shots --fallback-ken-burns
```
*(Wait ~5 seconds while ONLY `shot_06` renders!)*

> "Look at the output: `shot_01` through `shot_05`, `shot_07`, and `shot_08` all **skipped cleanly on cache**, and **only `shot_06` regenerated**—because only its input hash changed."

`[RUN IN TERMINAL: Show the single new log line in runs.jsonl]`
```powershell
Get-Content runs.jsonl -Tail 2
```

> "And here in **`runs.jsonl`**, we see the exact single logged run for `shot_06` with model, parameters, seed, and latency."

`[SCREEN CUE: Switch briefly to play 5 seconds of outputs/final/film_9x16.mp4]`

> "Here is the finished `9:16` vertical export with bilingual opening title, Amharic narration, ducked nocturnal score, full-frame visuals, and safe-zone English subtitles. Thanks for watching!"

---

## Quick Post-Recording Tip (`DO NOT READ ALOUD`)
After finishing your recording, restore `shot_06` `camera_motion` back to `"Locked-off camera, subtle nod and flickering lantern light."` (or run `git checkout storyboard.json` / `pipeline.shots` cache verify) if you want zero extra uncommitted diff — or keep it clean!
