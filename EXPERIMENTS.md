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
