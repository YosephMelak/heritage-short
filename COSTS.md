# Measured Costs, Latency & Quotas

> All execution metrics below are measured directly from `runs.jsonl` (`123` logged stage entries as of final assembly). All APIs ran strictly on zero-cost free tiers and local compute; commercial list-price equivalents reflect typical per-call/per-minute public cloud API rates for transparency.

## 1. Per-Stage Measurements (From `runs.jsonl`)

| Stage | Model / Tool Executed | Total Calls | Total Latency | Avg Latency / Call | Observed Free-Tier Limit / Bottleneck | Cash Spent | Commercial Equivalent (Est.) |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: | :---: |
| **Smoke Test & Text** | `gemini-3.8-flash` / AI Studio probes (`smoke_test`) | `10` | `38.62s` | `3.86s` | `gemini-3.8-flash` hit transient `503 UNAVAILABLE`; Gemini `lyria-3.5` returned `429` (`limit: 0` free tier) | \$0.00 | ~\$0.02 |
| **Amharic Narration** | `gemini-3.8-flash-tts` (`20`), `gemini-3.8-flash-lite-tts` (`14`), `gemini-3.1-flash-tts-preview` (`10`), `gemini-2.5-flash-preview-tts` (`8`) | `52` *(across all story & prosody iterations)* | `293.98s` (`4.90 min`) | `5.65s` | Strict **`10 req/day/model`** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`); mitigated with 4-model fallback + SHA-256 cache (`shot_06` silent = `0` calls) | \$0.00 | ~\$0.45 |
| **Reference & Keyframes** | `@cf/black-forest-labs/flux-2-klein-4b` (`28` API calls: `6` refs + `22` keyframes) & `user_curated` (`6`) | `34` | `330.22s` (`5.50 min`) | `11.79s` *(API only)* | ~`50–170` free images/day on Cloudflare Workers AI; `flux-2-klein-4b` uses fixed 4 steps + `multipart/form-data` (`input_image_0`) | \$0.00 | ~\$0.85 |
| **Original Score** | `facebook/musicgen-small` (local CPU fallback after Kaggle `ACE-Step 1.5` job stalled `>67m` in `QUEUED`) | `3` candidates (`76.0s` each) + `2` selects | `2,119.42s` (`35.32 min`) | `706.47s` (`11.77 min`) | Kaggle GPU queue (`#452 -> #416`, `Draft Session Starting...` hang); Colab `No backend with GPU`; HF `Ace-Step-v1.5` button disabled (`interactive=False`) | \$0.00 | ~\$0.15 *(GPU equivalent)* |
| **Moving Shots** | `ffmpeg-ken-burns` (`4x` supersampled `3840x2160` -> `1280x720`, `24 fps`) | `8` *(all shots; `wan22_kaggle_batch.py` also emitted)* | `60.88s` (`1.01 min`) | `7.61s` | Kaggle GPU queue `>90m`; laptop GPU (`MX450` `2 GB` VRAM) below `Wan 2.2` `12–24 GB` requirement | \$0.00 | ~\$0.80 *(if run on cloud T4/4090)* |
| **Assembly (Radio + Final)** | `FFmpeg 9.1` (`radio_cut.mp4`, `film_9x16.mp4`, `film_16x9.mp4`) | `14` (`4` radio cuts, `10` dual final runs) | `729.66s` (`12.16 min`) | `10.28s` (radio) / `68.86s` (final) | Local Windows `Fontconfig` needed temporary `fonts.conf` isolation (`FAIL-07`); blurred `9:16` optimization (`270x480` -> `1080x1920`) | \$0.00 | \$0.00 (local) |
| **Total Pipeline** | **All Stages Combined** | **`123`** | **`3,572.79s` (`59.55 min`)** | — | Zero paid billing attached; 100% free tier + local compute | **\$0.00** | **~\$2.27** |

---

## 2. Final Film Runtime Compute Cost (Single Clean Pass from Cached Assets vs Fresh Generation)

- **Clean-clone cached rebuild (`python -m pipeline.run`):** `~140–180s` (`~2.5 min`) locally (`FFmpeg` assembly only; `0` API/GPU calls needed).
- **Fresh single-shot regeneration live demo (1 narration line or 1 keyframe):** `~4–12s` API call + cached re-assembly (`7/8` shots skipped via `.sha256` sidecars).
- **GPU Hours Used on Kaggle / Colab:** `0.00` active billable GPU hours completed (account quota remained at `00:00 / 30 hrs` while remote queues blocked; all compute succeeded via Cloudflare serverless API, Gemini API, and local CPU).

---

## 3. Multi-Model / Ceiling Notes (Amharic TTS & Open-Weight Fallbacks)

We did not receive paid frontier keys (Omni Flash / Nano Banana / paid Lyria 3.5); however, our measured runs across **4 Gemini TTS variants (`52` calls)** produced an empirically grounded language benchmark for Amharic storytelling (`EXP-02`, `EXP-03`, `EXP-12`):
1. **Inline English style prefixes fail (`FAIL-02`):** Putting style directions inside `text` caused `3.8-flash-tts` to inject dramatic silences (`16.12s` vs `7.42s`), solved by `speechMetadata.style`.
2. **Labialized glyph fragility (`FAIL-03`):** Glyphs such as `ሿ` (`ትንሿ`) were misread by Amharic TTS; rewriting to clear unclipped wording fixed comprehension.
3. **Ejective onset clipping (`EXP-12`):** Word-initial ejective `ጠ` at `0ms` (`"ጠባቂውም..."` at `0:19`) sounded overly soft (`"smooth"`); adding a brief spoken lead-in + comma (`"እርሱም፣ ጠባቂውም፣"`) restored crisp ejective articulation without changing semantic meaning (`10.98s` verified by native-speaker review).
