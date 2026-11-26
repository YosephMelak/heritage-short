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

## FAIL-04: All 4 Gemini TTS Free-Tier Models Exhausted Daily Quota (`10 RPD` Each) Across Story Pivots
- **Stage / Tool:** Phase 1 Narration (`pipeline/narration.py` -> `gemini-3.8-flash-tts`, `3.8-flash-lite-tts`, `3.1-flash-tts-preview`, `2.5-flash-preview-tts`)
- **Symptom / Error:** After regenerating narration across multiple story revisions on the same day, all four Gemini TTS models hit `DAILY_QUOTA_429` (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`) during *Buna: Born in Ethiopia* (`shot_01`–`shot_04` succeeded and are cached; `shot_05`–`shot_08` paused on `429`).
- **What Was Tried:** Implemented a 4-model fallback cascade with `speechMetadata.style` (3.8) and explicit prompt prefix (2.5) plus per-shot SHA-256 caching so completed shots (`shot_01`–`shot_04`) are preserved.
- **Resolution / Workaround:** `shot_01`–`shot_04` remain cached in `outputs/narration/`; re-running `python -m pipeline.narration` after the Google AI Studio daily quota reset (midnight Pacific Time / 11:00 EAT) or with a fresh project key will skip `shot_01`–`shot_04` and finish `shot_05`–`shot_08` automatically.
