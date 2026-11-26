# Heritage Short — Multi-Model AI Film Pipeline

> **Status:** Scaffolded — awaiting Pre-Start Decisions (story, language, consent gate, compute setup).

A schema-driven pipeline that turns `storyboard.json` into a 60–90 second heritage short film exported in both **9:16** (vertical) and **16:9** (horizontal) with narration, English subtitles, a ducked original score, and a visible AI end card.

## Quickstart (One-Command Run)

1. Clone the repository and create a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your API keys (never commit `.env`).
3. Ensure `ffmpeg` is installed and on `PATH`.
4. Run the full pipeline from a clean clone:
   ```bash
   make film
   # Or directly without make:
   python -m pipeline.run
   ```

## Pipeline Stages (`storyboard.json` Contract)

1. `pipeline/validate.py` — Validates `storyboard.json` against `schema/storyboard.schema.json`, checks total duration (60–90s), and enforces the `consent_verified` gate.
2. `pipeline/narration.py` — Generates line-by-line narration via **Gemini 3.8 Flash TTS** and updates shot durations from measured audio.
3. `pipeline/keyframes.py` — Builds a golden character/style reference sheet and per-shot keyframes via **FLUX.2 klein / FLUX.1 schnell** (Cloudflare Workers AI).
4. `pipeline/music.py` — Auditions score candidates via **ACE-Step 1.5**.
5. `pipeline/shots.py` — Generates 480p moving clips via **Wan 2.2 TI2V-5B** (with SHA-256 input-hash caching, 3-attempt cap, and FFmpeg Ken Burns fallback).
6. `pipeline/assemble.py` — Normalizes stems, ducks music (`sidechaincompress`), normalizes loudness (`-14 LUFS` / `-1.0 dB` true peak), burns in subtitles, appends the AI end card, and exports `9:16` and `16:9` MP4s.

## Repository Files

- `storyboard.json` & `schema/storyboard.schema.json` — Single-source-of-truth contract.
- `runs.jsonl` — Append-only log of every model call (model, parameters, seed, latency, estimated cost).
- `DESIGN.md` — Audience, intent, Radio Cut test (#1), Near-Final Cut test (#2), storyboard diffs.
- `ARCHITECTURE.md` — Stage contracts, SHA-256 caching, retry & fallback design.
- `EXPERIMENTS.md` — Hypothesis -> Change -> Result entries.
- `FAILURES.md` — Real blockers, attempts, and resolutions.
- `COSTS.md` — Measured latency, GPU minutes, free-tier usage, and commercial cost equivalent.
- `ETHICS.md` — Consent log, model/output licences, AI labelling & provenance plan.

## Measured Cost Summary

*To be populated in [COSTS.md](./COSTS.md) after full pipeline runs.*
