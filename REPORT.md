# Technical Report — *Keeper of the Hyenas: A Night in Harar* (`የጅቦቹ ጠባቂ፡ አንድ ምሽት በሐረር`)

> **Repository:** https://github.com/YosephMelak/heritage-short  
> **Pipeline Command:** `python -m pipeline.run` *(or `make film`)*  
> **Runtime Status:** `74.71s` (`9:16` `9.09 MB` & `16:9` `13.10 MB`, `-14.06 LUFS` / `-0.95 dBTP`), **$0.00 API/GPU spend** across 123 logged runs.

---

## 1. Intent, Audience & Ethical Boundaries (`DESIGN.md` & `ETHICS.md`)

I set out to build a `60–90` second bilingual heritage short film—narrated in Amharic with English subtitles—about Harar Jugol's centuries-old nocturnal coexistence between the city's hyena keepers and wild spotted hyenas (*Crocuta crocuta*). My primary audience is Ethiopian youth, diaspora families, and curious mobile viewers (`9:16` vertical on phones with sound on, paired with `16:9` horizontal widescreen). The single emotional shift I wanted viewers to leave with is **moving from fear of the unfamiliar to quiet respect**: when humanity approaches nature with steadiness rather than panic, even darkness proclaims peace.

To uphold strict consent and dignity safeguards before generating any asset (`ETHICS.md`), I intentionally wrote **strictly fictional characters**—elder keeper **`Umar` (`ኡመር`)** and visiting youth **`Dawit` (`ዳዊት`)**, explicitly avoiding real Harar hyena-keeping family names (such as *Yusuf*)—and used Gemini's synthetic prebuilt voice (`Kore`). No real person's face, name, or voice clone appears anywhere in the film. Every model choice (`FLUX.2 klein 4B` Apache 2.0, scripted `Wan 2.2` Apache 2.0, Meta `facebook/musicgen-small` CC-BY-NC 4.0, Gemini API, FFmpeg LGPL/GPL) is logged with provenance and licensing terms.

---

## 2. Audience Feedback & Storyboard Evolution (`User Tests #1 & #2`)

### User Test #1 — The Radio Cut (`outputs/final/radio_cut.mp4`)
Before generating images or video, I assembled a black-screen audio-only Radio Cut and shared it on Slack with `3+` cohort/target-audience listeners.
- **What worked:** Listeners reported the pacing and Amharic storytelling landed well overall.
- **What surfaced:** A listener caught a concrete Amharic pronunciation issue on `shot_03` (`0:19`), noting `"0:19 = Tebakiwem / ጠባቂውም"`, where the initial ejective **`ጠ`** sounded soft/smooth rather than crisp and firm. Earlier internal linguistic audits (`FAIL-03`) also caught mispronunciation of labialized glyphs like `ሿ` (`ትንሿ`) and heavy multi-clause phrasing.
- **Storyboard Changes Made:**
  1. Rebuilt `storyboard.json` from real measured Gemini TTS durations (`68.0s -> 72.64s -> 72.26s`), preserving `shot_06` as an intentional `5.50s` wordless breathing beat.
  2. Ran controlled prosody experiments (`EXP-12`): tested adding a brief natural lead-in (`"እርሱም፣ ጠባቂውም፣..."`) with firm Amharic ejective-letter style guidance (`Option A`, `10.98s` via `gemini-3.8-flash-tts`) vs alternate spelling (`Option B`, `9.46s`), verified by listening, and locked `Option A` into `outputs/narration/shot_03.wav`.

### Creator Self-Review & User Test #2 — Near-Final Exports (`3` Slack Reviewers)
Reviewing the initial `1080x1920` vertical export and sharing the near-final cut on Slack produced three concrete outcomes (`EXP-14`, `EXP-15`):
1. **Full-Frame `9:16` Layout (`EXP-14`):** Center/pan cropping `16:9` wide two-shots (`shot_01`, `shot_04`, `shot_07`, `shot_08`) still clipped Elder Umar, Dawit, or the hyenas at wide instants. Switching `9:16` to a **Full-Frame Blurred-Atmosphere Cinema Layout** kept 100% of the wide scene centered (`1080x608` over dimmed Gaussian-blurred nocturnal fill) and placed burned-in subtitles cleanly **below** the image (`MarginV=52`).
2. **Closing Card (`EXP-14`):** Per creator aesthetic direction on the closing card, `"Made with AI"` was removed from the in-frame `2.5s` card (showing `Thank you for watching` + title), relying on the platform's AI-generated content label toggle when publishing.
3. **User Test #2 Slack Feedback (`DESIGN.md` Section 6):**
   - **Tester 1 (Slack reviewer):** Asked why the opening didn't show the film title in both Amharic and English (*"At the start of the video, why aren't we seeing the title of the story in both Amharic and English?"*). I updated `pipeline/assemble.py` (`EXP-15`) to render a `0.25s–4.25s` fade-in/out bilingual opening title (`Keeper of the Hyenas: A Night in Harar` via `arial.ttf` + `የጅቦቹ ጠባቂ፡ አንድ ምሽት በሐረር` via `nyala.ttf`) and re-exported both videos (`9.09 MB` `9:16`, `13.10 MB` `16:9`).
   - **Tester 2 & Tester 3 (Slack reviewers):** Both reviewed the near-final export and raised no additional issues or change requests, confirming audio clarity, subtitles, and visual framing were ready for release.

---

## 3. Hardest Technical & Creative Problem and How I Solved It (`FAILURES.md`)

Two intertwined failure chains tested the pipeline hardest (`FAIL-01` through `FAIL-07`):
1. **Free-Tier Quota Exhaustion & Language Prosody (`FAIL-01`–`FAIL-04`):** Gemini TTS models cap free tier at **10 requests/day/model** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`). During Amharic script refinements, I exhausted individual models' RPD caps (`429`), while inline English style prompts inside `text` caused `3.8-flash-tts` to inject multi-second silences (`16.12s` vs `7.42s`). I solved both by moving instructions into `speechMetadata.style` on 3.8 models, separating a 4-model fallback cascade (`3.8-flash-tts -> 3.8-flash-lite-tts -> 3.1-flash-tts-preview -> 2.5-flash-preview-tts`), and protecting every completed WAV with SHA-256 sidecars.
2. **Simultaneous Cloud GPU Congestion & Image Consistency Drift (`FAIL-05`, `FAIL-06`, `FAIL-07`):** On submission day, Kaggle `GPU T4 x2` interactive sessions stalled (`#452 -> #416`, then hung at `Draft Session Starting...`), a headless Kaggle SDK kernel (`yosephalem/heritage-short-music`) stayed `QUEUED` for `>67` minutes, Google Colab returned `No backend with GPU available`, and Hugging Face's `Ace-Step-v1.5` Space had its `'Generate Music'` button disabled (`interactive=False`). Meanwhile locally, a `2 GB MX450` laptop GPU cannot run `Wan 2.2 TI2V-5B`. Rather than stalling before the deadline, I:
   - Upgraded keyframes (`EXP-08`, `EXP-09`) by anchoring on 6 `1024x576` curated Harar stills and generating `shot_04` & `shot_06` via composition-matched `@cf/black-forest-labs/flux-2-klein-4b` edits with ungraded 35mm documentary prompts (`no cyan/teal LUT`).
   - Generated three `76s` instrumental candidates locally on CPU (`~11.7 min` each) with open-weight **`facebook/musicgen-small`** and auditioned sidechain-ducked mixes (`candidate_03.wav` selected, `EXP-11`).
   - Upgraded `pipeline/shots.py` with **`4x` (`3840x2160`) supersampled shot-matched FFmpeg `zoompan`** (`1280x720`, `24 fps`, `-crf 16`, `EXP-13`) and resolved a Windows FFmpeg `Fontconfig` crash (`exit 3221225477`, `FAIL-07`) via isolated `outputs/temp/fonts.conf`.

---

## 4. Suggested Practices Tested Honestly

- **Practice that beat my instinct — Schema-driven Radio Cut + SHA-256 Input Caching:** Building an audio-only MP4 over a black screen before touching pictures initially felt unnecessary. In practice, sharing `radio_cut.mp4` on Slack caught real Amharic duration and ejective pronunciation flaws (`ጠባቂውም` at `0:19`) when fixing a line cost one `5s` TTS call instead of re-rendering images and video. Paired with `.sha256` caching across every stage (plus lazy API credential checks in `keyframes.py`), changing `shot_03` regenerated *only* `shot_03` while skipping `7/8` shots cleanly.
- **Practice that did NOT behave as expected — Passing `golden_ref.png` via `input_image_0` to every shot + assuming free cloud T4 queues would suffice:** Attaching the same two-shot reference image to every `flux-2-klein-4b` keyframe locked every `insert`, `close_up`, and `wide` shot into the same two-person framing (`FAIL-05`, `EXP-05`). Conditioning had to be gated strictly by shot composition (`SHOT_EDIT_REFS`). Likewise, assuming phone-verified Kaggle (`30 hrs/week`) guaranteed same-day batch execution broke under peak queue stalls (`>90 min`), proving why deterministic local fallbacks (`musicgen-small`, `ffmpeg-ken-burns`) must be first-class pipeline code.

---

## 5. Curiosity Beyond the Floor ("Raising the Ceiling")

Because Amharic TTS quality varies sharply across models and orthography, I turned our narration debugging into a measured **Amharic TTS Prosody & Multi-Provider Resilience Study** across **52 logged Gemini TTS calls** (`EXP-02`, `EXP-03`, `EXP-12`, `COSTS.md`):
- Quantified how separating `speechMetadata.style` halved `shot_03` latency/pause bloat (`16.12s -> 7.42s`).
- Identified two reproducible Amharic failure classes in neural TTS: labialized Ge'ez characters (`ሿ`) and word-initial `0ms` ejective softening (`ጠ` in `ጠባቂውም`), proving that brief natural vocal lead-ins + punctuation commas (`"እርሱም፣ ጠባቂውም፣"`) restore crisp ejective pronunciation without altering voice or meaning.
- Benchmarked real end-to-end free-tier limits (`123` runs, **$0.00** cash spend, **59.55 min** total compute across Gemini, Cloudflare Workers AI, and local FFmpeg/PyTorch fallback).

---

## 6. What I Would Build Next

1. **Native dual-aspect keyframe generation** (separate `9:16` vertical re-compositions paired via multi-reference image editing rather than `16:9` blurred letterbox) and **automated headless Wan 2.2 cloud dispatch** via `kaggle kernels push` once queue windows open.
2. **Reusable Amharic phonetic pre-processor** for `pipeline/narration.py` that automatically detects word-initial ejectives (`ጠ, ቀ, ጨ, ጸ, ጰ`) and risky labialized glyphs before spending daily TTS quota.
