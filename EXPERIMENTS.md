# Experiment Log

> Target: **~10+ structured experiments** (`Hypothesis -> Change -> Result`) backed by seeds, parameters, and evidence in `runs.jsonl`. Change one variable at a time.

### EXP-01: Gemini 3.8 TTS Inline Style Prompt vs. `speechMetadata.style` for Amharic Narration
- **Stage:** Narration (`pipeline/narration.py` -> `gemini-3.8-flash-tts`)
- **Hypothesis:** Moving the English style instruction (`"calm, warm, unhurried storyteller"`) from the spoken `parts[].text` field into `parts[].speechMetadata.style` will prevent the TTS model from speaking/improvising on English text or stalling at Amharic punctuation (`፣`), reducing bloated clip durations so all 9 shots fit cleanly inside the `60–90s` film window.
- **Change:** Replaced inline `"Speak in a calm, warm, unhurried storyteller voice: <Amharic>"` in `parts[].text` with pure Amharic in `parts[].text` + `parts[].speechMetadata = {"style": "calm, warm, unhurried storyteller"}`.
- **Result & Evidence:** Measured on `shot_03`: speech duration dropped from `16.12s` (with 3 mid-clip pauses detected by FFmpeg `silencedetect`) to `7.42s` (54% reduction). Across all 9 shots (`shot_01`–`03` on `gemini-3.8-flash-tts`, `shot_04`–`09` on `gemini-3.8-flash-lite-tts`), total synced storyboard duration stabilized at **`74.52s`** (logged in `runs.jsonl`). Decision: keep `speechMetadata.style` for all `3.8` TTS models and omit it only on pre-3.8 fallbacks (`gemini-2.5-flash-preview-tts`).

### EXP-02: Amharic Labialized Glyph Removal & Cultural Revision (`storyboard.json` v2)
- **Stage:** Storyboard & Narration (`storyboard.json`, `pipeline/narration.py` -> `gemini-3.8-flash-lite-tts` & `gemini-3.1-flash-tts-preview`)
- **Hypothesis:** Replacing labialized/compressed Amharic glyphs (such as `ትንሿ`) with clear standard syllables (`ተማሪ ሰላም`) and revising the 9-shot monastic draft into a 10-shot plural Ethiopian heritage script (*brana*/*wanza*/reed pen, Harar/Wollo *Ajami*, oral storytelling, archival custodianship) will eliminate mispronunciations while keeping pacing consistent across all 10 shots.
- **Change:** Updated `DESIGN.md` with heritage research, rewrote `storyboard.json` to 10 shots with clean Amharic phrasing, and added `gemini-3.1-flash-tts-preview` as quota fallback in `pipeline/narration.py`.
- **Result & Evidence:** All 10 clips generated cleanly (`4.24s–6.20s` per shot, zero 15s+ outliers), syncing `storyboard.json` to **`74.93s`** (`runs.jsonl`). Ready for native-speaker pronunciation re-check and User Test #1.

### EXP-03: Story Pivot to *The Wisdom of Buna* (8 Shots) & 4-Model Gemini TTS Quota Cascade
- **Stage:** Storyboard & Narration (`storyboard.json`, `pipeline/narration.py`)
- **Hypothesis:** Focusing on an 8-shot single-setting coffee ceremony arc (*The Wisdom of Buna — የቡና ጥበብ*) with clean phonetic Amharic and a 4-model free-tier TTS cascade (`3.8-flash-tts` -> `3.8-flash-lite-tts` -> `3.1-flash-tts-preview` -> `2.5-flash-preview-tts` with an explicit `"Read aloud only..."` prefix on 2.5) will complete narration in one run despite `~10 RPD` caps per model and land cleanly inside `60–90s`.
- **Change:** Replaced the 10-shot archival script with an 8-shot coffee-ceremony script (`shot_01`–`shot_08`) and added `gemini-3.1-flash-tts-preview` + `gemini-2.5-flash-preview-tts` to `TTS_MODELS` in `pipeline/narration.py`.
- **Result & Evidence:** All 8 clips generated cleanly (`4.96s–7.36s` speech per shot; `3.8-flash-lite-tts` on `shot_01`, `shot_05`; `3.1-flash-tts-preview` on `shot_02`–`04`; `2.5-flash-preview-tts` on `shot_06`–`08`), syncing `storyboard.json` to **`63.71s`** (`runs.jsonl`). Ready for native-speaker audio check and User Test #1.

### EXP-04: Golden Reference Sheet — Authentic Ethiopian Features & Lantern Physics (`flux-2-klein-4b`)
- **Stage:** Keyframes Reference (`pipeline/keyframes.py` -> `@cf/black-forest-labs/flux-2-klein-4b`)
- **Hypothesis:** Adding explicit East African / Ethiopian Harari visual descriptors (`warm dark brown East African skin`, `short curly black hair` for Dawit) to `character_ref.prompt` (seed `4410`) will produce authentic Ethiopian representation, and removing the unsupported `steps` field while wiring `input_image_0` conditioning in `keyframes.py` will keep identity consistent across all 8 shots.
- **Change:** Inspected `ref_01`–`ref_03` (`seed 4401–4403`, latencies `12.71s–15.22s`); `ref_02` showed a floating lantern artifact and `ref_01`/`ref_03` rendered Dawit too light-skinned. Updated `character_ref` (`seed 4410`) and wired `input_image_0` on `flux-2-klein-4b`.
- **Result & Evidence:** Inspected regenerated `ref_01`–`ref_03` (`14.79s`, `11.11s`, `14.41s` via `flux-2-klein-4b`, logged in `runs.jsonl`). `ref_01.png` (seed `4410`) achieved authentic Ethiopian/Harari representation, clean hand anatomy holding both lantern and woven basket, and centered Harar Jugol moonlit coral-stone framing (`ref_02` lacked the basket; `ref_03` had a slightly stiffer portrait pose). Selected `ref_01.png` as `outputs/refs/golden_ref.png`.

### EXP-05: Reference-Conditioned Keyframes (`input_image_0 = golden_ref.png`) Across All 8 Shots
- **Stage:** Keyframes (`pipeline/keyframes.py` -> `@cf/black-forest-labs/flux-2-klein-4b`)
- **Hypothesis:** Conditioning every shot's `flux-2-klein-4b` generation on `outputs/refs/golden_ref.png` via `input_image_0` will preserve Umar's face, wrapped turban, embroidered tunic, Dawit's likeness/jacket, and the amber-vs-indigo nocturnal palette across wide, medium, insert, and close-up shots.
- **Change:** Removed unsupported `steps` field, attached `golden_ref.png` as `input_image_0` multipart file, and ran `python -m pipeline.keyframes`.
- **Result & Evidence:** Visual inspection of `shot_01`–`shot_08` revealed two critical findings (`runs.jsonl`, latencies `7.17s–38.02s`):
  1. `flux-2-klein-4b` treats `input_image_0` as a strict image-editing canvas, locking camera framing and pose across all 8 shots (`shot_02` insert, `shot_03`/`shot_06` close-ups, and `shot_08` wide all cloned `golden_ref.png`'s exact medium two-shot layout; only `shot_01` and `shot_05` worked cleanly).
  2. Prompting `"spotted hyena"` without explicit anatomical cues produced wolf/dog-like pointy-eared canines in `shot_04` and `shot_07`.
  Decision: Keep `shot_01` and `shot_05`, disable `input_image_0` on framing-diverse shots (`shot_02`–`04`, `06`–`08`) while anchoring identity via locked attire/feature descriptors, and specify rounded-ear spotted hyena anatomy.

### EXP-06: Shot-Specific Camera Framing (Text-Anchored Identity) & Spotted Hyena Anatomy
- **Stage:** Keyframes (`pipeline/keyframes.py`, `storyboard.json`)
- **Hypothesis:** Disabling `input_image_0` on `insert`, single-character `close_up`, `medium` feeding, and `wide` pull-back shots while embedding locked character descriptors + explicit `"African spotted hyena (Crocuta crocuta) with rounded ears, sloping back, tan coat with dark spots"` will restore true shot-size variety and accurate hyena anatomy.
- **Change:** Updated `storyboard.json` (`shot_02`, `03`, `04`, `06`, `07`, `08`) and gated `input_image_0` in `keyframes.py` to matching two-shot framing (`shot_01`, `shot_05`).
- **Result & Evidence:** Visual inspection confirmed clean camera diversity and anatomy across `shot_01`–`shot_07`: `shot_02` tight hands+meat insert, `shot_03` & `shot_06` elder close-ups, `shot_04` & `shot_07` rounded-ear spotted hyenas. Only `shot_08` drifted on Dawit's skin tone/hair and distant animal shapes.

### EXP-07: Anchoring Wide-Shot Identity & Distant Hyenas in `shot_08`
- **Stage:** Keyframes (`storyboard.json` `shot_08`, `seed: 6428`)
- **Hypothesis:** Wide-shot framing caused `shot_08` to omit specific skin-tone/hair details for Dawit and render distant animals too generically. Adding explicit East African descriptors for Umar & Dawit plus *Crocuta crocuta* anatomical traits on `shot_08` (with `seed: 6428`) will fix continuity.
- **Change:** Updated `shot_08` `visual_prompt` and seed (`6418` -> `6428`), validated `storyboard.json`, and regenerated `outputs/keyframes/shot_08.png` in 12.04s via `flux-2-klein-4b`.
- **Result & Evidence:** Inspected `outputs/keyframes/shot_08.png` — Umar and Dawit now match `golden_ref.png` cleanly in warm lantern foreground while two spotted hyenas walk peacefully down the moonlit path outside Harar Jugol's arched wall. Ready for user approval & Kaggle Wan 2.2 TI2V-5B generation.

### EXP-08: Upgrading Full 8-Shot Aesthetic to User-Curated 16:9 Cinema Stills & Matched `input_image_0` Edits
- **Stage:** Keyframes & Moving-Shot Prep (`pipeline/keyframes.py`, `pipeline/shots.py`, `storyboard.json`)
- **Hypothesis:** Adopting the user's 6 `1024x576` high-detail Harar Jugol fortress stills (`shot_01`, `02`, `03`, `05`, `07`, `08`) as `outputs/refs/curated/` + `golden_ref.png` and generating `shot_04` (anchored to `shot_07.png`, Dawit removed) and `shot_06` (anchored to `shot_03.png`, solo Umar smiling) via `flux-2-klein-4b` at `1024x576` will produce 8 seamless 35mm documentary keyframes. Also fixing `shots.py` Ken Burns output (`1024x1024` -> `1280x720`) avoids stretching `16:9` inputs.
- **Change:** Normalized the 6 curated stills via FFmpeg to borderless `1024x576` PNGs; updated `keyframes.py` default resolution (`1024x576`), curated-hash caching, and `SHOT_EDIT_REFS`; stripped character leakage from `style_block` (`shot_06` initially pulled Dawit in before removing Dawit from `style_block` and bumping seed `6426` -> `6436`).
- **Result & Evidence:** Visually inspected both generated keyframes (`shot_04.png` in `7.56s`, `shot_06.png` in `6.44s`) alongside all 6 curated stills — zero drift, consistent fortified stone gate, patterned white turban, embroidered robe, striped Harari shawl, basket, lantern, and spotted hyena across all 8 frames (`8/8` cache-verified). Re-emitted `outputs/shots/wan22_kaggle_batch.py`.

### EXP-09: Removing Artificial Teal-LUT Cast & Over-Sculpted Expression on `shot_04` & `shot_06`
- **Stage:** Keyframes (`storyboard.json` `style_block`, `shot_04` `seed: 6444`, `shot_06` `seed: 6446`)
- **Hypothesis:** User feedback flagged that `shot_04` and `shot_06` looked less photorealistic than the 6 curated stills due to (a) cyan/teal haze and exaggerated lantern glow from `style_block`, (b) a stiff outstretched arm on `shot_04`, and (c) an exaggerated smile/lantern addition on `shot_06`. Switching `style_block` to ungraded dark slate 35mm documentary tones and easing posture/expression prompts will make Umar match the curated stills seamlessly.
- **Change:** Updated `style_block` to remove teal/indigo haze and added explicit unretouched low-light photography cues; regenerated `shot_04` (`7.02s`) and `shot_06` (`6.95s`).
- **Result & Evidence:** Inspected `shot_04.png` (elder Umar standing naturally across basket and lantern facing calm spotted hyena in exact curated tones) and `shot_06.png` (identical skin texture, lighting, turban, and fortress bokeh to `shot_03.png` with a natural warm closed-mouth gaze). Both now match all 6 user-curated stills seamlessly.

### EXP-10: Vertical `9:16` Pan-and-Scan Framing & Wan 2.2 16 GB T4 Flag Alignment
- **Stage:** Dual-Aspect Assembly & Moving-Shot Batch Prep (`pipeline/assemble.py`, `pipeline/shots.py`)
- **Hypothesis:** Static center-cropping `16:9` stills/clips (`1024x576` / `1280x704`) to `1080x1920` cuts wide two-shot subjects (`shot_01`, `04`, `07`, `08`) off the left/right edges; adding per-shot normalized horizontal pan-and-scan windows (`VERTICAL_PAN_X`) preserves full-bleed `9:16` video with every subject visible. Likewise, upstream `Wan2.2/generate.py` `--task ti2v-5B` requires `1280*704` + `--offload_model True --convert_model_dtype --t5_cpu` to run inside 16 GB T4 VRAM.
- **Change:** Implemented `VERTICAL_PAN_X` dynamic FFmpeg crop expressions in `assemble.py` and updated `shots.py` `--emit-kaggle` command flags + `1280x720` Ken Burns aspect ratio.
- **Result & Evidence:** Verified compilation, `pipeline.validate`, updated `outputs/shots/wan22_kaggle_batch.py`, and executed FFmpeg vertical crop test on `shot_01.png` (`1080x1920` `PASSED`). Ready for Kaggle Wan 2.2 execution after score download.

### EXP-11: Score Auditioning & Model Replacement (`facebook/musicgen-small`, `candidate_03.wav`)
- **Stage:** Music Score (`pipeline/music.py`, `outputs/music/`)
- **Hypothesis:** After Kaggle `yosephalem/heritage-short-music` remained `QUEUED` for >67 minutes (`FAIL-06`) and Colab/HF ZeroGPU failed, running Meta's open-weight `facebook/musicgen-small` locally for 3 distinct `76s` (`72 BPM`, `D minor`, instrumental) candidates and auditioning each via `-14 LUFS` sidechain-ducked mixes under the Amharic narration will reveal which arrangement supports the voice best.
- **Change:** Generated `candidate_01.wav` (`seed=5401`), `candidate_02.wav` (`seed=5402`), and `candidate_03.wav` (`seed=5403`) locally, mixed sidechain-ducked previews (`outputs/temp/audition_01..03.wav`), selected `candidate_03.wav` (`--select candidate_03.wav`), and updated `storyboard.json` + schema (`musicgen-small`, `seed: 5403`).
- **Result & Evidence:** User auditioned `audition_01`–`03` and selected `candidate_03.wav` (`76.00s`, `4.86 MB`, `mean=-20.3 dB`) because its sparse nocturnal lyre arpeggios and warm drone give the Amharic narration the cleanest headroom. Locked at `outputs/music/chosen_score.wav`.

### EXP-12: Amharic Ejective Onset & Prosody Fix for `0:19` (`እርሱም፣ ጠባቂውም፣`)
- **Stage:** Narration (`storyboard.json` `shot_03`, `pipeline/narration.py`)
- **Hypothesis:** User & Slack feedback flagged that initial-position `ጠባቂውም` sounded too soft/smooth on the ejective `ጠ` (`ṭ`) onset (`0:19`). Testing two variants — Option A (`"እርሱም፣ ጠባቂውም፣ በስማቸው እየጠራ..."` on `gemini-3.8-flash-tts` with firm Amharic ejective-letter style cue so `ጠ` doesn't soften at `0ms` onset) vs Option B (`ጠባቂዉም፣` on `3.8-flash-lite-tts`) — will restore hard, crisp pronunciation.
- **Change:** Backed up original `shot_03.wav` (`outputs/temp/shot_03_v1_backup.wav`), compared `shot03_optA.wav` (`10.98s`) vs `shot03_optB.wav` (`9.46s`), adopted user-approved Option A into `outputs/narration/shot_03.wav`, updated `storyboard.json` (`72.26s` synced total), and re-synced `.sha256` cache.
- **Result & Evidence:** User confirmed Option A nailed the hard/clear Amharic pronunciation of `ጠባቂውም`; `pipeline.narration` cache verification (`8/8` cache hits), `pipeline.shots --emit-kaggle`, and `pipeline.validate` all passed cleanly.

### EXP-13: `4x` Supersampled Shot-Matched Camera Motion (`ffmpeg-ken-burns`) & Cache Verification
- **Stage:** Moving Shots & Caching (`pipeline/shots.py`, `outputs/shots/`)
- **Hypothesis:** With Kaggle GPU queues stalled (`>90m`), Colab unavailable, and Hugging Face ZeroGPU video spaces rate-limited (`FAIL-06`), upgrading `_render_ken_burns_fallback` to upscale `1024x576` stills to `3840x2160` (`lanczos`) before `zoompan` (`s=1280x720`, `-crf 16`, linear per-shot motion matching `camera_motion` across push-ins, subtle drift, and `shot_08` pull-back) eliminates `zoompan` pixel stepping while preserving crisp character/hyena fidelity.
- **Change:** Updated `KEN_BURNS_MODES` & `_render_ken_burns_fallback` in `pipeline/shots.py` and executed `python -m pipeline.shots --fallback-ken-burns` across all 8 shots, followed by cache-hit verification (`--shot shot_01` and full re-run).
- **Result & Evidence:** Rendered all 8 `1280x720 @ 24 fps` clips in `60.86s` total (`shot_01` `10.21s`/`1923 KB` .. `shot_08` `10.50s`/`2176 KB`), verified `8/8` `.sha256` sidecars and cache skip on both `--shot shot_01` and full `pipeline.shots` re-run, reached `112` logged entries in `runs.jsonl`, and passed `pipeline.validate` (**Checkpoint 2 Complete**).

### EXP-14: Full-Frame `9:16` Blurred-Atmosphere Cinema Layout & End Card Polish
- **Stage:** Phase 3 Final Assembly (`pipeline/assemble.py`)
- **Hypothesis:** Self-review of the first `film_9x16.mp4` (`EXP-10` horizontal pan-and-scan crop) showed that cropping `16:9` wide scenes (`31.6%` width) still omitted characters/hyenas at wide instants, and the creator wanted `"Thank you for watching"` on the closing card alongside the rubric-required `"Made with AI"` disclosure. Compositing full `1080x608` (`16:9`) foreground frames centered over a Gaussian-blurred dimmed atmospheric fill inside `1080x1920` (with subtitles placed in the clean lower margin `MarginV=52`) will preserve 100% of every wide composition.
- **Change:** Updated `_render_aspect_export` in `pipeline/assemble.py` with `split=2` + `270x480` downscaled `boxblur=7:2` + `eq=brightness=-0.22:saturation=0.85` background fill for `9:16` (`FontSize=10, MarginV=52`) and updated the `2.5s` closing card per creator direction to `Thank you for watching` + `Keeper of the Hyenas: A Night in Harar` (relying on platform AI disclosure toggle upon publishing).
- **Result & Evidence:** Re-assembled both exports (`film_9x16.mp4` = `1080x1920`, `74.71s`, `8.98 MB`; `film_16x9.mp4` = `1920x1080`, `74.71s`, `12.95 MB`; both measured `-14.06 LUFS`, `-0.95 dBTP`). Visually inspected `inspect_9x16_endcard.png` and `inspect_16x9_endcard.png` confirming crisp centered closing typography.

### EXP-15: Bilingual English + Amharic Opening Title Overlay (User Test #2 — Tester 1)
- **Stage:** Phase 3 Final Assembly (`pipeline/assemble.py` -> `shot_01`)
- **Hypothesis:** User Test #2 Tester 1 noted the opening shot lacked the story's bilingual title on screen. Adding a `0.25s–4.25s` fade-in/out dual title overlay (`Keeper of the Hyenas: A Night in Harar` via `arial.ttf` + `የጅቦቹ ጠባቂ፡ አንድ ምሽት በሐረር` via `nyala.ttf` UTF-8 `textfile=`) above the `9:16` foreground (`y=418/480`) and in `16:9` upper sky (`y=76/138`) establishes bilingual heritage identity immediately without obscuring characters or bottom subtitles.
- **Change:** Updated `_render_aspect_export` in `pipeline/assemble.py` to write UTF-8 `title_en.txt` / `title_am.txt` and overlay timed `drawtext` layers on `shot_01`, logged Tester 1 in `DESIGN.md`, and re-exported both films.
- **Result & Evidence:** Re-assembled both exports (`film_9x16.mp4` = `1080x1920`, `74.71s`, `9.09 MB`; `film_16x9.mp4` = `1920x1080`, `74.71s`, `13.10 MB`; both `-14.06 LUFS`, `-0.95 dBTP`). Visually inspected `inspect_9x16_title.png` and `inspect_16x9_title.png`: Ethiopic Ge'ez glyphs (`የጅቦቹ ጠባቂ፡ አንድ ምሽት በሐረር`) rendered crisply via `nyala.ttf` with zero overlap on Umar, Dawit, or subtitles.
