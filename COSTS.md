# Measured Costs, Latency & Quotas

> Measurements below are taken strictly from `runs.jsonl`. Phase 2 image/music/video rows will be populated once Phase 2 runs complete.

## 1. Per-Stage Measurements (Observed to Date)

| Stage | Model / Tool | Measured Calls | Avg Latency (s) | Total Units / Duration | Actual Free-Tier Limit Observed | List-Price Equivalent (USD) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Script / Storyboard | Gemini 3.5 Flash / 3.8 Flash | Probe only | `1.44s` (list); `3.8-flash` hit `503` | — | Free tier (`3.8-flash` had transient `503`) | \$0.00 (free tier) |
| Narration (Current Harar Cut) | Gemini 3.8 Flash TTS (`shot_01`–`05`) + 3.8 Flash-Lite TTS (`shot_07`–`08`) | `7` (`shot_06` silent = `0` calls) | `5.45s` (`3.8-flash`: `5.42s, 4.72s, 6.59s, 5.28s, 5.12s`; `3.8-lite`: `6.14s, 4.89s`) | `53.14s` spoken audio across `7` clips | `10 req/day` (`FreeTier`) per TTS model | \$0.00 (free tier) |
| Assembly (Radio Cut) | FFmpeg 9.1 (local) | `1` (Harar Radio Cut) | `10.90s` | `72.67s` MP4 (`1.94 MB`) | Unlimited (local CPU) | \$0.00 |
| Keyframes | FLUX.2 klein 4B / FLUX.1 schnell | *Pending Phase 2* | — | — | ~50–170 free images/day (Cloudflare) | — |
| Moving Shots | Wan 2.2 TI2V-5B (480p) / Ken Burns | *Pending Phase 2* | — | — | ~30 GPU hrs/week (Kaggle 2x T4, phone-verified) | — |
| Music | ACE-Step 1.5 | *Pending Phase 2* | — | — | Kaggle / Colab GPU quota | — |

## 2. Frontier Comparison *(if cohort access is provided)*

*Not yet executed (awaiting cohort frontier key availability, if opened).*
