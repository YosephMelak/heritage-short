# Ethics, Consent, Licences & Labelling Plan

> **CRITICAL GATE:** If any real person's face, likeness, or voice appears or is voiced without a recorded informed consent entry here **before** generation, the film scores **0**, regardless of quality.

## 1. Real People & Informed Consent Log

- **Are any real people's faces, likenesses, or voices depicted?** **No.** While Harar Jugol has real-life hyena feeders (such as the Yusuf family), this film intentionally depicts **strictly fictional characters**—seasoned fictional Harari elder keeper **`Umar` (`ኡመር`)** (specifically **not** named *Yusuf* to avoid depicting real living individuals) and fictional young visitor/apprentice **`Dawit` (`ዳዊት`)**—with synthetic prebuilt TTS narration (`Kore`). No real person's name, face, likeness, or personal voice is depicted or cloned.
- **Cultural & Heritage Safeguard:** Visuals and narration represent Harar Jugol (UNESCO World Heritage coral-stone walled city) and Harar's nocturnal hyena coexistence tradition respectfully—grounded in documented historical/anthropological coexistence and Harari craft (woven straw basket, wooden feeding stick, traditional embroidered tunic and wrapped cotton headcloth), without inventing traditions or naming living artists.

| Character / Voice | Fictional or Real? | Informed Consent Required? | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `Umar` (elder Harari keeper) | Fictional character | No (non-real person) | Verified fictional | Distinct from real Harar families (`Yusuf`); no real likeness used |
| `Dawit` (young man / narrator) | Fictional character | No (non-real person) | Verified fictional | Fictional youth character; no real likeness used |
| Narrator voice (`Gemini TTS`, prebuilt `Kore`) | Synthetic prebuilt voice | No (not a real person's voice clone) | Verified synthetic | No voice cloning performed |

## 2. Model & Output Licences

| Stage | Model / Tool | Licence / Terms | Commercial / Distribution Notes |
| :--- | :--- | :--- | :--- |
| Script & Storyboard | Gemini 3.5 Flash / 3.8 Flash | Google AI Studio / Gemini API Terms | Free tier used; no private family data sent in prompts |
| Narration | Gemini 3.8 / 3.1 / 2.5 Flash TTS | Google AI Studio / Gemini API Terms | Prebuilt synthetic voice (`Kore`) for Amharic narration |
| Keyframes | FLUX.2 klein 4B (`user_curated` stills + AI edits) | Apache 2.0 (`@cf/black-forest-labs/flux-2-klein-4b`) | Permissive Apache 2.0 inference via Cloudflare Workers AI; `shot_04` & `shot_06` edited from user-curated non-real-person Harar stills |
| Moving Shots | Wan 2.2 TI2V-5B (scripted) / FFmpeg Ken Burns fallback (`executed`) | Apache 2.0 (`Wan 2.2`) / LGPL-GPL (`FFmpeg`) | Deterministic `4x`-supersampled `zoompan` executed locally after Kaggle GPU queue stall (`FAIL-06`) |
| Music / Score | ACE-Step 1.5 (scripted) / Meta `facebook/musicgen-small` (`executed`) | MIT (`ACE-Step 1.5`, `audiocraft/transformers`) / `CC-BY-NC 4.0` (`musicgen-small` weights) | Non-commercial educational/challenge film use under `CC-BY-NC 4.0` after Kaggle/Colab/HF `ACE-Step` GPUs stalled (`FAIL-06`) |
| Assembly | FFmpeg | LGPL / GPL | Deterministic non-AI editing & mixing |

## 3. AI Labelling & Provenance Plan

- **In-film closing card:** Clean 2.5-second closing card displaying *"Thank you for watching — Keeper of the Hyenas: A Night in Harar"* (relying on the platform AI-generated content label and repository disclosures per creator aesthetic direction).
- **Platform disclosure:** Switch **ON** the platform's AI-generated content label when publishing publicly.
- **Provenance metadata:** Preserve watermarks and provenance metadata (**SynthID**, **C2PA**) intact wherever supported by models/tools.

## 4. Privacy & Style Safeguards

- No private personal details or real individuals' likenesses are sent to free endpoints that may train on prompts.
- Prompts describe coral-stone walls, lantern glow, moonlight, and traditional attire rather than referencing living artists or real feeders.
