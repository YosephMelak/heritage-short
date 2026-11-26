# Measured Costs, Latency & Quotas

> Record actual measured latency and GPU minutes per stage from `runs.jsonl`, free-tier limits encountered, and commercial list-price equivalents.

## 1. Per-Stage Measurements

| Stage | Model / Tool | Calls | Avg Latency (s) | Total GPU Min / Units | Actual Free-Tier Limit Observed | List-Price Equivalent (USD) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Script / Translation | Gemini 3.8 Flash / Flash-Lite | — | — | — | — | — |
| Narration | Gemini 3.8 / 3.8-Lite / 3.1 / 2.5 Flash TTS | — | — | — | `3.8-flash-tts`: 10 RPD; `3.8-flash-lite-tts`: ~10 RPD; `3.1-flash-tts-preview`: ~10 RPD; fallback `2.5-flash-preview-tts` | — |
| Keyframes | FLUX.2 klein / FLUX.1 schnell | — | — | — | ~50–170 images/day (verify) | — |
| Moving Shots | Wan 2.2 TI2V-5B (480p) | — | — | — | ~30 GPU hrs/week Kaggle (verify) | — |
| Music | ACE-Step 1.5 | — | — | — | Kaggle/Colab quota | — |
| Assembly | FFmpeg | — | — | 0 (local) | Free | \$0.00 |

## 2. Frontier Comparison *(if cohort access was provided)*

*Compare open models vs. frontier models (Omni Flash / Nano Banana / Lyria 3.5) on latency, cost, and quality if available.*
