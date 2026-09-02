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

Questions worth asking (in priority order):
1. ~~Sahara v2.5 access~~ ANSWERED 2 Sep: current API access is v2.5.
2. Streaming STT: COMMITTED_TRANSCRIPT bug + 10–35s partial latency — is a
   fix landing before Demo Day? (We have traces to share.)
3. Benchmark audios (bonus): preferred format/metadata schema for the
   optional consented samples?
4. Did the frontier-API credits (Gemini/OpenAI) Tobi mentioned at the
   masterclass materialise?
5. Benchmark report: any required template, or is the
   Intron-Multimodal-Benchmarking repo the reference?

## 1. Model line-up

Sahara requires ≥2 other ASR systems in the comparison (competition brief).
Plan, pending David's sign-off on the third-model decision:

| Model | Role | Status |
|---|---|---|
| **sahara v2.5** | the model under test | CONFIRMED 2 Sep (David): current API access IS v2.5 — no migration, the app and Phase G both run it. Report labels: workshop bench = "Sahara (API, 5 Aug snapshot)", Phase G = "Sahara v2.5" |
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
