# Phase G — benchmark & report prep notes (updated 2 Sep, post-registration)

Working checklist for the Sep 8–12 re-benchmark and report. Deadline
context: **submission 15 Sep 11:59pm WAT**, winners 1 Oct.
**ONE submission per access token — no second entry. Assemble everything,
review, submit once.** (Token lives in David's email; never in this repo.)

## 0. Official rubric (from the 2 Sep registration email) — weights drive effort

| Criterion | Weight | Our answer |
|---|---|---|
| **Code-Switching Benchmark Quality** | **30%** | the Phase G report — "a rigorous report matters more than a polished pitch" (their words). Highest weight = highest effort |
| Product Quality & Fit | 25% | live PWA, agentic loop, field-tested by real traders |
| Real-World Impact | 20% | market traders = meaningful population; real field data |
| Technical Execution | 15% | egress architecture, latency work, streaming, P0 gate |
| Ethics, Safety & Inclusion | 10% | consent-gated bundle tool, never-guess invariant, ₦570,007 audit trail |

Submission checklist (all six): solution description · demo video
(unlisted YouTube) · docs · benchmark report (3+ models incl. Sahara) ·
ethics/inclusion note · optional consented benchmark audios (bonus).

Alignment with Intron's own benchmarking practice (their
Intron-Multimodal-Benchmarking repo, checked 2 Sep): they report **WER/CER
both normalized and raw** — ours will too; and their own ASR roster
includes **Meta OmniCTC/OmniLLM and Google Gemini** — our model lineup
mirrors the organisers' methodology, which is worth one sentence in the
report. LyngualLabs/YorubaEnglish-CodeSwitching-TTS (verified 2 Sep): a
**TTS MODEL** (VoxCPM2 fine-tune, weights + synthetic demo wavs,
CC-BY-NC-4.0) — no human audio with ground-truth transcripts, so NOT
ASR-benchmark material. Related-work honourable mention only (evidence
the Yoruba-English code-switching ecosystem is growing); it does not
enter the corpus.

## 0b. Live Q&A — Thu 3 Sep, 12:00–1:00pm WAT (Google Meet, link in email)

Questions — FACT-CHECKED 2 Sep evening, every premise re-verified live:
1. ~~Sahara v2.5 access~~ ANSWERED: current API access is v2.5 (verified
   three ways, see §1).
2. **Streaming STT (re-verified TONIGHT on v2.5, real-time-paced probe):**
   COMMIT is still answered with INPUT_ERROR "Error processing data"
   instead of COMMITTED_TRANSCRIPT, and first partial arrived +10.3s
   after commit. Ask: is a fix scheduled before Demo Day? (Traces in
   hand; the partial also read "I don sell 3 rice 500" — streaming
   quality trails the sync path on the same clip.)
3. **Benchmark audios (bonus):** your Intron-Multimodal-Benchmarking repo
   defines meta_data_transcription.csv as `audio_path, duration, text,
   language, source` — should the optional consented audio submission
   follow that schema? And since it includes `text`: are name-scrubbed
   transcripts acceptable? (Our de-identification withholds transcripts
   by default because market speech contains buyer names.)
4. Frontier-API credits (Gemini/OpenAI) Tobi mentioned at the masterclass
   — did they materialise? (Unverifiable from here; watch WhatsApp too.)
5. Benchmark report: the email says "pros and cons of each" model — is
   the Multimodal-Benchmarking repo's normalisation the expected one for
   WER/CER comparability across teams, or may teams use their own
   documented normaliser? (Ours is public in the repo.)
6. Can the API response expose a model/version field? We measured
   deterministic same-clip output changes between 5 Aug and 2 Sep —
   version labels matter for benchmark reproducibility. (Also product
   feedback for the report.)
7. **NEW — credits:** SESSION_CREATED reports credit_balance 4.24 on our
   key (seen twice tonight). Phase G needs a few hundred Sahara calls
   (frozen corpus + AfriSwitch + field clips + streaming tests). How do
   challenge participants get topped up for benchmarking?

## 1. Model line-up

Sahara requires ≥2 other ASR systems in the comparison (competition brief).
Plan, pending David's sign-off on the third-model decision:

| Model | Role | Status |
|---|---|---|
| **sahara v2.5** | the model under test | VERIFIED 2 Sep, three ways: (1) intron.io states v2.5 is the current release (12 bilingual mixing models, streaming ASR/TTS endpoints — the v2.5-era features our key already uses); (2) David's confirmation; (3) **same-clip probes prove the backend changed since 5 Aug** (deterministic — repeat calls identical). Report labels: workshop bench = "Sahara (API, 5 Aug snapshot)", Phase G = "Sahara v2.5". No version field in API responses — see Q&A Q6 |

**Same-clip evidence, 5 Aug cache vs 3 Sep live — CORRECTED after full
docs read.** The first version of this table (2 Sep evening) was
contaminated: those probes passed `language=pcm`, but the documented
field is `use_language_asr_input` — the wrong name is silently ignored
and the calls defaulted to ENGLISH ASR (hence the anglicised "I don't
sell 3D liquor of rice, 50,005"). The app itself was never affected:
asr.py has used `use_language_asr_input` in both sync and async paths
all along. Corrected table, right param, deterministic (repeat calls
identical):

| clip | truth | Sahara 5 Aug | Sahara 3 Sep (v2.5, pcm) | shift |
|---|---|---|---|---|
| case01 | I don sell three derica of rice five thousand five | "I don sell 3 derica of rice 5,500." | "I don sell 3 of rice 500" | drift: "derica" dropped; amount 5,500→500 |
| case03 | I buy fuel ten thousand naira | "i buy fuel thousand naira" (deleted "ten") | "I buy fuel0 naira" | drift: number mangled into "fuel0" |

Read: real backend drift under correct parameters — smaller than the
contaminated table suggested, but present on both clips, and still
money-corrupting shapes (both would clarify/gate in our grammar, not
log wrong). The Sep 8 frozen-corpus run quantifies it properly. The
English-default outputs are ALSO useful: they show what any integrator
who typos the param name silently gets — worth a product-feedback line
(unknown form fields are accepted silently; suggest rejecting unknown
`use_*` fields or echoing effective config).

**Full docs read (3 Sep, docs.voice.intron.io — all STT + TTS pages):**
- **TTS accent: our call is ALREADY the documented optimum.** Accent
  values are language-named; for Pidgin the pair is voice_language
  "pcm" + voice_accent "pidgin" (male/female) — exactly what
  SaharaTts sends. Igbo/yoruba/hausa accents exist for those languages;
  there is no separate generic "nigerian" accent. NO CODE CHANGE.
- TTS Generate: text limit 4096 chars (we truncate at 1000 — fine),
  `output_audio_format` wav|opus (opus = smaller fetch, optional
  optimisation), 30 req/min, 120s→503 with Get-Text-Status fallback.
- **TTS Streaming (NEW)**: wss://infer.voice.intron.io/tts/v1/stream —
  INPUT_TEXT_CHUNK (10–100 chars) / FETCH_AUDIO_CHUNK / COMMIT, 48 kHz
  mono 16-bit base64. Demo Day option for lower-latency readback.
- STT sync: new documented knobs — **`use_disable_llm_corrections`
  (default FALSE, i.e. LLM post-processing is ON by default)**,
  `use_diarization`, `use_category`, `use_template_id`. Benchmark plan:
  score Sahara as-deployed (default) as the primary row, raw
  (TRUE) as a secondary row — the LLM corrections are plausibly where
  digit-formatting shifts come from.
- STT Question Answering: get_answer=TRUE turns sync upload into
  audio-in→LLM-answer-out. Not for us (our agent is deterministic by
  design — one report sentence contrasting the approaches).
- **Code-switching pairs confirmed (12)**: Pidgin-EN, Yoruba-EN,
  Hausa-EN, Igbo-EN, Swahili-EN, Zulu-EN, Akan-EN, Amharic-EN,
  Luganda-EN, Wolof-EN, Afrikaans-EN + Kinyarwanda-EN-FR trilingual —
  matches all our assumptions for pcm/yo/ha/sw.
- **Shona gap: `sn` is an STT language and a TTS language (shona
  accent, male/female) but is NOT in the 12 code-switch pairs.** Her
  corrected utterances are heavily mixed ("Ndatengesa three cups dze
  rice nefive dollars fifty") — expect degraded Sahara accuracy on the
  sh-ZW tier and SAY SO in advance in the report (a falsifiable
  prediction is good science); AfriSwitch ships Shona at CMI 24.55, so
  the data exists — product feedback: promote Shona to a code-switch
  pair.
| **whisper-large-v3** | strong general open model, offline | cached from workshop bench |
| **whisper-small** | lightweight floor | cached |
| **facebook omnilingual-ASR** | strongest open model on our languages (PazaBench WER 0.29–0.51 on Hausa/Igbo/Yoruba/Swahili/Shona) | **CONFIRMED third model (David, 28 Aug) — and WORKING in WSL.** No Windows fairseq2 wheels and no HF-hosted inference; installed in WSL2 Ubuntu-24.04 venv `~/omni` (kenlm skipped — optional LM decoder needing a C++ toolchain; libsndfile shimmed from the soundfile wheel via `LD_LIBRARY_PATH=~/omni/shimlib`; fairseq2 0.6 + fairseq2n 0.6+cpu + torch 2.8.0 CPU + numpy 1.26). Verified: 1,672 supported languages incl. `pcm_Latn`, `yor_Latn`, `hau_Latn`, `ibo_Latn`, `swh_Latn`, `sna_Latn`. NOTE: it CLAIMS Pidgin — so our gap claim is about public *evaluation* (no leaderboard measures Pidgin), and our report delivers the first Pidgin numbers for this model. CTC-300M variant: 1.3 GiB, ~2 GiB RAM. **Smoke test 28 Aug (CTC-300M, CPU, tier-a case01):** ground truth "I don sell three derica of rice five thousand five" → transcribed "i don sow three the reca of rice" in 21.1s incl. model load — **the money phrase was deleted entirely.** Exactly the deletion-class corruption our task-completion metric exists to expose; a strong early signal for the report. Caveats to carry: this is the smallest variant with greedy decoding (kenlm LM decoder not installed); PazaBench's "omnilingual" column is presumably the larger variant — verify which before quoting. Bench plan: run CTC-300M + LLM-1B (~6 GB RAM, feasible); 7B variants do not fit in 24 GB RAM on CPU |
| **Nemotron 3.5 ASR (0.6B)** | masterclass tie-in; nvidia-nemo family ranks 11/16 on PazaBench | optional bonus row — see feasibility below |
| **Gemini (frontier API)** | closed-model comparator | **CONFIRMED (David, 28 Aug): his Gemini key** — goes in .env as GEMINI_API_KEY, never committed; benchmark-only, never wired into the app. Intron may still provide credits ("stay on the lookout" — Tobi) |

**Nemotron feasibility (investigated 28 Aug, decision for David):**
open weights (OpenMDW-1.1), 600M params ≈ 2.4 GB, runs via HF
`transformers` ≥ 5.13 — BUT its 40 supported language-locales include
**zero African languages**, and this machine has no NVIDIA GPU (AMD
integrated, 24 GB RAM) so it would run on CPU, which the card does not
document. Recommendation: make **omnilingual-ASR the third model** (it is
the scientifically justified strong comparator), and treat Nemotron as an
optional extra row whose predicted failure *is itself the finding* — the
newest state-of-the-art open ASR release supports no African language.
One hour timebox if attempted; drop without ceremony if CPU inference
misbehaves.

## 2. Corpus

- AfriSwitch confirmed at **14 languages** on 28 Aug (Kinyarwanda, Amharic,
  Zulu, Igbo, Yoruba, Hausa, Pidgin, Oromo, Swahili, Shona, French, Tswana,
  Luganda, Afrikaans). Tobi: growing to 16 "by end of week or next week" —
  **re-pull and re-count immediately before the corpus freeze on Sep 8.**
- Shona: 3.86 h / 1,155 utterances / CMI 24.55 — real coverage. If the
  native-speaker session happens (human task), sh-ZW becomes the fifth
  validated tier-a pack, built exactly like pcm-yo-NG.
- Tiers for this benchmark: frozen tier-a (workshop, untouched) + fresh
  AfriSwitch pull + wild-field tier (consented sister/Idowu clips).
- License note: AfriSwitch is CC BY-NC-SA 4.0 — fine for a competition
  report, keep the attribution line.

## 3. CMI framing (correction, verbatim rule)

Per Tobi directly: **low CMI = leans toward one dominant language with
fewer explicit switches; high CMI = more balanced mixing.** The Pidgin
subset (CMI 4.19, lowest on the table) must be described as
"Pidgin-dominant with comparatively fewer explicit switches to English
within this dataset" — never "barely code-switched". (Checked 28 Aug: the
over-claim does not appear anywhere in the workshop REPORT.md or README;
this rule guards the NEW report's text.)

## 4. Report structure — lead with task completion

Order of results:
(a) standard WER/CER table for context, matching general-purpose
leaderboards (PazaBench snapshot: `results/pazabench-wer-2026-08-28.md`);
(b) **transaction-exact / amount-safe / amount-corrupted as the primary
result**, framed as "a task-completion metric of the kind the judging
brief calls for."

Quotes to carry (from the 28 Aug masterclass):
- Tobi Olatunji (Intron founder), on the metric teams should develop, citing
  the finance use case: *"how many transactions were actually correctly
  recorded"* — the downstream task-completion measure, distinct from WER/CER.
- Mercy Muchai (Microsoft Research Africa), Q&A: code-switching evaluation
  needs datasets that are actually code-mixed — single-language datasets
  can't measure it. One sentence noting our approach (native-recorded
  Pidgin/Yoruba corpus + AfriSwitch) is built around exactly this.
- Robustness cross-validation, one sentence: Sahara's own robustness
  benchmarking explicitly includes silence handling (Tobi, masterclass);
  consistent with what our workshop benchmark independently observed
  (empty transcript on a silence-only clip). Cross-validation of the
  vendor's claim — not a new claim of ours.

Related-work positioning (verified 28 Aug against the live leaderboard,
all 61 rows): **Nigerian Pidgin absent from PazaBench's 61 languages;
Sahara absent from its 53 models.** Our benchmark fills a real,
independently checkable gap. Full snapshot + citation pointers in
`results/pazabench-wer-2026-08-28.md`.

## 5. Audio sample bundle (bonus points — confirmed by Tobi)

Tooling ready: `tools/curate_audio_bundle.py` (stage → human review →
finalize). **Hard gate found and enforced:** the in-app consent reads
"Clips stay for this app, nowhere else" — it covers retention for model
testing, NOT redistribution into Intron's community benchmark. The tool
refuses to finalize until each contributing session is listed in
`--consent-confirmed`, i.e. after David gets fresh, explicit permission
from his sister and Idowu (a direct ask; record date + wording via
`--consent-note`). Bundle contents: de-identified wavs (SLA-#### ids,
4-char session refs), metadata.csv (duration, language, domain, device
type — no transcripts, no names), CONSENT.md. The refusal-by-default is
itself submission material for the ethics & safety criterion.

## 6. Scope discipline

This phase is report-and-corpus work. The live app's parsing/safety logic
does not change. No paid API calls before the benchmark run plan is
agreed. (Optional later: update the in-app consent copy for FUTURE users
to mention optional benchmark sharing — a product decision for David, and
it would not retroactively cover clips already collected.)
