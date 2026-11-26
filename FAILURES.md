# Failure & Troubleshooting Journal

> Record real blockers (API quota, GPU timeouts/OOM, model replacements, character/face/hand drift, TTS pronunciation errors), what you tried, and how you resolved or worked around them.

## FAIL-01: Gemini 3.8 Flash Text 503 Spike & TTS Free-Tier 10 RPD Quota Limit
- **Stage / Tool:** Smoke Test & Phase 1 Narration (`pipeline/smoke_test.py`, `pipeline/narration.py` -> `gemini-3.8-flash`, `gemini-3.8-flash-tts`)
- **Symptom / Error:**
  1. `gemini-3.8-flash` returned `HTTP 503 UNAVAILABLE` (*"This model is currently experiencing high demand"*).
  2. `gemini-3.8-flash-tts` returned `HTTP 429 RESOURCE_EXHAUSTED` with `quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: "10"` (free tier allows only **10 requests per day** per project on `gemini-3.8-flash-tts`).
- **What Was Tried:**
  1. Verified `v1beta/models` list and tested `gemini-3.5-flash` and `gemini-3.5-flash-lite` (`HTTP 200`) as fallback text models.
  2. Probed `gemini-3.8-flash-lite-tts` and confirmed it returned `HTTP 200` under a separate quota bucket.
  3. Preserved completed shots (`shot_01`–`shot_03`) via SHA-256 caching and added an automatic fallback chain (`gemini-3.8-flash-tts` -> `gemini-3.8-flash-lite-tts` -> `gemini-2.5-flash-preview-tts`) when daily quota is exhausted.
- **Resolution / Workaround:** `shot_01`–`shot_03` remained cached from `gemini-3.8-flash-tts`, and `pipeline/narration.py` automatically switches to `gemini-3.8-flash-lite-tts` on `DAILY_QUOTA_429` so all 9 narration tracks finish without manual intervention.

## FAIL-02: Gemini TTS Speaking/Stalling on Inline English Style Prompt (`shot_03` 16.12s vs 7.42s)
- **Stage / Tool:** Phase 1 Narration (`pipeline/narration.py` -> `gemini-3.8-flash-tts`)
- **Symptom / Error:** Prepending `"Speak in a calm, warm, unhurried storyteller voice: "` directly inside the `contents[].parts[].text` field produced bloated clips (`shot_03` = `16.12s`, `shot_05` = `11.64s`, `shot_06` = `13.20s`, `shot_07` = `14.91s`) with multiple mid-clip pauses (`silencedetect`), pushing the 9-shot total to `97.14s` (above the `60–90s` schema bound).
- **What Was Tried:** Inspected silence intervals with FFmpeg `silencedetect`, verified `speechMetadata.style` in the Gemini 3.8 Flash TTS schema, and separated `style_cue` into `parts[].speechMetadata.style` while keeping `parts[].text` strictly pure Amharic.
- **Resolution / Workaround:** Re-running `shot_03` with `speechMetadata.style` cut speech duration from `16.12s` to `7.42s` and brought the storyboard duration back inside `60–90s`. Regenerating all shots under `speechMetadata.style`.

## FAIL-03: Amharic TTS Mispronunciation (`ትንሿ ሰላም`) & Cultural-Context Revision
- **Stage / Tool:** Phase 1 Pronunciation Review (`pipeline/narration.py` -> `gemini-3.8-flash-lite-tts` + `storyboard.json`)
- **Symptom / Error:** Native-speaker review of `outputs/final/radio_cut.mp4` caught mispronounced Amharic words—specifically `ትንሿ ሰላም` (the labialized glyph `ሿ` caused the TTS to say an unintended word)—and our initial draft narrowed Ethiopian manuscript heritage to a single monastic framing rather than honoring Ethiopia's plural Ge'ez, Islamic/*Ajami*, oral, and archival preservation traditions.
- **What Was Tried:** Conducted heritage research across *brana* parchment/ink/reed-pen/*wanza*-cover/*medegos* traditions, Harar & Wollo *Ajami* manuscripts, Ethiopian oral storytelling, and verifiable preservation institutions (NALE/*Wemezekir* and IES). Replaced labialized/ambiguous TTS words (`ትንሿ` -> `ተማሪ`, etc.) with clear, unambiguous Amharic phrasing.
- **Resolution / Workaround:** Rewrote `DESIGN.md` and `storyboard.json` around verified plural heritage traditions and clearer Amharic wording, then regenerated narration for re-auditioning.

## FAIL-04: Daily Free-Tier TTS Quota Exhaustion (`10 RPD` / Model) Across Story Pivots
- **Stage / Tool:** Phase 1 Narration (`pipeline/narration.py` -> `gemini-3.8-flash-tts`, `3.8-flash-lite-tts`, `3.1-flash-tts-preview`, `2.5-flash-preview-tts`)
- **Symptom / Error:** After regenerating narration across multiple story revisions and pivoting to *Keeper of the Hyenas: A Night in Harar* (team story de-duplication), `shot_01` (`6.01s`) and `shot_02` (`6.45s`) succeeded via `gemini-2.5-flash-preview-tts`, and `shot_03` hit `DAILY_QUOTA_429` (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`).
- **What Was Tried:** Built a 4-model fallback cascade with `speechMetadata.style` (3.8) and explicit prompt prefix (2.5), added intentional silent-shot support (`shot_06` uses 0 TTS calls), cleared stale audio from earlier drafts, and cached `shot_01`–`shot_02`.
- **Resolution / Workaround:** `shot_01`–`shot_02` remain cached in `outputs/narration/`; re-running `python -m pipeline.narration` after the Google AI Studio daily reset (~11:00 EAT) or with a second project key will complete the remaining 5 spoken shots (`shot_03`–`05`, `07`–`08`) and allow `radio_cut.mp4` assembly.

## FAIL-05: `flux-2-klein-4b` `input_image_0` Composition Lock & Wolf-Like Hyena Artifacts
- **Stage / Tool:** Phase 2 Keyframes (`pipeline/keyframes.py` -> `@cf/black-forest-labs/flux-2-klein-4b`)
- **Symptom / Error:** Passing `golden_ref.png` via `input_image_0` on all 8 shots caused `flux-2-klein-4b` to preserve the reference image's exact medium two-shot composition across `insert`, `close_up`, and `wide` shots (`shot_02`, `03`, `04`, `06`, `07`, `08`), and `"spotted hyena"` rendered wolf/dog-like pointy-eared animals in `shot_04` and `shot_07`.
- **What Was Tried:** Visually inspected all 8 generated keyframes (`outputs/keyframes/shot_01.png`–`shot_08.png`) before spending GPU minutes on video generation. Kept `shot_01` and `shot_05` (where two-shot framing matched `golden_ref.png`), gated `input_image_0` to matching two-shot compositions only, and added explicit *Crocuta crocuta* anatomical descriptors (`rounded bear-like ears, muscular sloping shoulders, golden-tan fur with dark brown spots`) plus locked attire/face descriptions for text-to-image shots.
- **Resolution / Workaround:** Regenerated `shot_02`, `03`, `04`, `06`, `07`, `08` with true camera diversity and accurate spotted hyenas. Later upgraded all 8 stills to `1024x576` Harar Jugol cinema style (`EXP-08`, `EXP-09`).

## FAIL-06: Kaggle `GPU T4 x2` Queue Wait & Upstream API/CLI Mismatches (`ACE-Step 1.5` & `Wan 2.2 TI2V-5B`)
- **Stage / Tool:** Phase 2 Music & Moving Shots (`pipeline/music.py`, `pipeline/shots.py`)
- **Symptom / Error:**
  1. Kaggle free `GPU T4 x2` notebook queued at position `#452` (`11:40 EAT`), progressed slowly (`#416` at `11:57 EAT`), and then hung on `Draft Session Starting...` (`12:02–12:17 EAT`); Google Colab fallback also returned `"No backend with GPU available / Unable to connect to the runtime"` (`12:24 EAT`).
  2. Initial `ACE-Step 1.5` job template imported `acestep.pipeline_ace_step.ACEStepPipeline` (v1 API), whereas upstream `ACE-Step-1.5` exposes `AceStepHandler` + `LLMHandler` + `generate_music` (`keyscale`, `instrumental`, `backend="pt"`).
  3. Initial `Wan 2.2 TI2V-5B` template used `--size 832*480` without offload flags, whereas `ti2v-5B` only supports `1280*704` / `704*1280` and needs `--offload_model True --convert_model_dtype --t5_cpu` to fit in 16 GB T4 VRAM.
- **What Was Tried:** Audited upstream repositories, updated `pipeline/music.py` (`76s`, PyTorch `pt` backend) and `pipeline/shots.py` (`1280*704`, CPU/layer offload flags, `1280x720` Ken Burns fallback), probed Gemini `lyria-3.5` (`HTTP 429 limit: 0` on free tier), and switched ACE-Step 1.5 music generation to the official Hugging Face ZeroGPU Space (`https://huggingface.co/spaces/ACE-Step/Ace-Step-v1.5`).
- **Resolution / Workaround:** Updated both Kaggle/Colab scripts (`outputs/music/acestep_kaggle_job.py`, `outputs/shots/wan22_kaggle_batch.py`), submitted headless batch job `yosephalem/heritage-short-music`, and after >67 minutes stuck in `QUEUED` (`14:03–15:10 EAT`), executed open-weight `facebook/musicgen-small` locally inside `.venv` to generate 3 `76.00s` score candidates (`candidate_01.wav`–`03.wav` in ~11.7 min/track; `candidate_03.wav` selected). For moving shots (`15:48 EAT`), upgraded `_render_ken_burns_fallback` in `pipeline/shots.py` with `4x` (`3840x2160`) supersampling (`1280x720 @ 24 fps`, `-crf 16`, shot-matched camera motion) and generated all 8 cached clips (`shot_01.mp4`–`shot_08.mp4`) locally in `60.86s`.

## FAIL-07: Windows FFmpeg Fontconfig Access Violation (`exit 3221225477`) in `drawtext` / `subtitles`
- **Stage / Tool:** Phase 3 Final Assembly (`pipeline/assemble.py` -> FFmpeg 9.1 on Windows)
- **Symptom / Error:** Running `drawtext` for the 2.5s `Made with AI` end card crashed with `Fontconfig error: Cannot load default config file: File not found` and `exit 3221225477` (`0xC0000005` access violation). In addition, `libass` `.srt` rendering uses virtual `PlayResY=288`, so `MarginV=180` would have placed vertical subtitles across character chests/faces rather than bottom safe margins.
- **What Was Tried:** Verified `C:/Windows/Fonts/arial.ttf`, tested generating a temporary `fonts.conf` (`FONTCONFIG_FILE`) plus explicit `fontfile=` and `fontsdir=` options in an isolated FFmpeg test (`drawtext exit: 0`, `subtitles exit: 0`), and recalibrated `MarginV=40, FontSize=11` (`9:16`) / `MarginV=22, FontSize=15` (`16:9`).
- **Resolution / Workaround:** Updated `pipeline/assemble.py` (`_ffmpeg_env()` and `_render_aspect_export()`) to emit and bind `outputs/temp/fonts.conf` automatically on Windows without breaking Linux/macOS execution.

## FAIL-04: All 4 Gemini TTS Free-Tier Models Exhausted Daily Quota (`10 RPD` Each) Across Story Pivots
- **Stage / Tool:** Phase 1 Narration (`pipeline/narration.py` -> `gemini-3.8-flash-tts`, `3.8-flash-lite-tts`, `3.1-flash-tts-preview`, `2.5-flash-preview-tts`)
- **Symptom / Error:** After regenerating narration across multiple story revisions on the same day, all four Gemini TTS models hit `DAILY_QUOTA_429` (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`) during *Buna: Born in Ethiopia* (`shot_01`–`shot_04` succeeded and are cached; `shot_05`–`shot_08` paused on `429`).
- **What Was Tried:** Implemented a 4-model fallback cascade with `speechMetadata.style` (3.8) and explicit prompt prefix (2.5) plus per-shot SHA-256 caching so completed shots (`shot_01`–`shot_04`) are preserved.
- **Resolution / Workaround:** `shot_01`–`shot_04` remain cached in `outputs/narration/`; re-running `python -m pipeline.narration` after the Google AI Studio daily quota reset (midnight Pacific Time / 11:00 EAT) or with a fresh project key will skip `shot_01`–`shot_04` and finish `shot_05`–`shot_08` automatically.
