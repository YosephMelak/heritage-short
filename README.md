# Keeper of the Hyenas: A Night in Harar — የጅቦቹ ጠባቂ፡ አንድ ምሽት በሐረር

A reproducible, schema-driven AI short-film studio in code. Turning one validated contract ([storyboard.json](./storyboard.json)) into a **`74.71s`** Amharic-narrated cultural short film exported in both **`9:16` vertical** ([film_9x16.mp4](./outputs/final/film_9x16.mp4)) and **`16:9` horizontal** ([film_16x9.mp4](./outputs/final/film_16x9.mp4)), with burned-in English subtitles and a sidechain-ducked original nocturnal acoustic score (`-14.06 LUFS` / `-0.95 dBTP`).

> **Ethics & Cost:** 100% fictional characters (`Umar`, `Dawit` — distinct from real Harar feeding families) voiced with synthetic Gemini TTS (`Kore`); **$0.00 API/GPU cash spend** across 123 logged pipeline operations (commercial list-price equivalent **~$2.27**). See [ETHICS.md](./ETHICS.md) and [COSTS.md](./COSTS.md).

---

## Quickstart (One-Command Run from Clean Clone)

1. Clone the repository and create a Python virtual environment:
   ```bash
   git clone https://github.com/YosephMelak/heritage-short.git
   cd heritage-short
   python -m venv .venv
   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
   # Linux/macOS:        source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Ensure `ffmpeg` and `ffprobe` are installed and on `PATH`.
3. *(Optional for regenerating uncached shots via API)* Copy `.env.example` to `.env` and add `GEMINI_API_KEY` and `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN`. **Not required to rebuild the film from the committed cached assets.**
4. Run the full end-to-end pipeline in one command:
   ```bash
   python -m pipeline.run
   # Or with GNU Make:
   make film
   ```
   Cached narration, keyframes, score, and moving shots skip cleanly via `.sha256` sidecars, and `pipeline/assemble.py` produces fresh `outputs/final/film_9x16.mp4` and `outputs/final/film_16x9.mp4`.

### Live Single-Shot Regeneration (Demo / Iteration)
Edit any shot's `narration_text` or `visual_prompt` in `storyboard.json` and rerun:
```bash
python -m pipeline.narration   # regenerates ONLY the modified shot; 7/8 skip on SHA-256 cache
python -m pipeline.run         # cascades downstream cache keys & rebuilds both MP4 exports
```

---

## Pipeline Stages (`storyboard.json` Contract)

1. [pipeline/validate.py](./pipeline/validate.py) — Validates `storyboard.json` against [schema/storyboard.schema.json](./schema/storyboard.schema.json), checks `60–90s` summed duration (`72.26s` active timeline), and enforces `consent_verified == true`.
2. [pipeline/narration.py](./pipeline/narration.py) — Generates Amharic speech via a 4-model **Gemini TTS** cascade (`gemini-3.8-flash-tts` primary) with `speechMetadata.style`, silent-beat handling (`shot_06`), and SHA-256 caching.
3. [pipeline/keyframes.py](./pipeline/keyframes.py) — Manages `1024x576` (`16:9`) curated reference stills + image-conditioned **Cloudflare Workers AI `@cf/black-forest-labs/flux-2-klein-4b`** keyframes (`outputs/refs/`, `outputs/keyframes/`).
4. [pipeline/music.py](./pipeline/music.py) — Emits **ACE-Step 1.5** GPU scripts and locks the auditioned winner (`outputs/music/candidate_03.wav` from **Meta `facebook/musicgen-small`**, `72 BPM`, `D minor`, local CPU fallback after Kaggle GPU queue stall) into `outputs/music/chosen_score.wav`.
5. [pipeline/shots.py](./pipeline/shots.py) — Emits **Wan 2.2 TI2V-5B** (`1280*704`) Kaggle scripts (`--emit-kaggle`), ingests remote clips (`--ingest-dir`), and renders `4x` supersampled shot-matched FFmpeg `zoompan` clips (`1280x720`, `24 fps`, `-crf 16`, `.sha256` cached) via `--fallback-ken-burns`.
6. [pipeline/assemble.py](./pipeline/assemble.py) — Renders the Phase 1 Radio Cut (`--mode radio-cut`) and Phase 3 dual exports (`--mode final`): sidechain-ducked score, two-pass `-14 LUFS` `loudnorm`, burned-in English subtitles, `2.5s` closing card, and blurred-atmosphere full-frame `9:16` cinema layout.

---

## Documentation & Evidence Trail

| Document | Purpose |
| :--- | :--- |
| [storyboard.json](./storyboard.json) & [schema/storyboard.schema.json](./schema/storyboard.schema.json) | Single-source-of-truth contract & schema |
| [runs.jsonl](./runs.jsonl) | Append-only telemetry (`123` entries: timestamp, stage, shot, model, params, seed, latency) |
| [DESIGN.md](./DESIGN.md) | Audience, Harar Jugol research, 8-shot plan, User Test #1 & #2 notes, storyboard diffs |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Stage boundaries, SHA-256 caching, retry & fallback logic, dual-aspect composition |
| [EXPERIMENTS.md](./EXPERIMENTS.md) | 15 structured `Hypothesis -> Change -> Result` engineering entries (`EXP-01`–`EXP-15`) |
| [FAILURES.md](./FAILURES.md) | 7 real failure cases (`FAIL-01`–`FAIL-07`): quotas, TTS onset/pronunciation, GPU queues, Windows Fontconfig |
| [COSTS.md](./COSTS.md) | Measured latency summary (`59.55 min` compute across 123 runs, **\$0.00** spent, **~\$2.27** commercial eq.) |
| [ETHICS.md](./ETHICS.md) | Non-real-person consent verification, model licences, AI disclosure & provenance plan |
