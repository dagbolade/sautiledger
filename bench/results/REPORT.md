# SautiLedger — Code-Switch ASR & TTS Benchmark

**Sahara CodeSwitch Africa Challenge (Phase 2) — benchmark report**

Corpus frozen before the first run; manifest sha256 `50e5e064312fd6bfe05c5aad6662be75f2b31e1525f57917d403849dd4377aeb`.

**70 clips** across three tiers · **7 speech systems compared** (`chirp-3`, `gpt-4o-transcribe`, `mai-transcribe-2`, `omnilingual-ctc-300m`, `parakeet-tdt`, `sahara-v2.5`, `whisper-large-v3`), plus a frozen 5 August Sahara snapshot retained as a drift control and not counted among them.

> **Note:** Scored from cached transcripts: every model pass ran separately (local models are memory-hungry), then one scoring pass assembled the report. No transcript was re-fetched, so the numbers are reproducible without re-spending API credits.

Prior work: this benchmark extends our August workshop report (`REPORT-workshop-2026-08.md`, same repository), which measured three models on the tier-a and tier-b corpora. Everything below is a fresh measurement; where the workshop numbers are cited they are labelled as the 5 August snapshot.

## 1. The primary result: task completion

At Intron's 28 August masterclass the challenge founder was explicit about the metric teams should develop for their own vertical — for a financial application, *"how many transactions were actually correctly recorded"*. That is the metric this section reports, and we lead with it because a voice ledger is judged by the ledger, not by the transcript.

Each model's **raw transcript** is fed through SautiLedger's grammar-first normaliser exactly as the live app runs it (LLM fallback disabled), and the resulting entry is compared to the expected one:

- **Transaction exact** — every field correct: type, item, quantity, unit, amount.
- **Amount safe** — the amount was right, *or* the agent refused to guess and asked a clarifying question. Asking is safe; nothing is written.
- **Amount corrupted** — a WRONG amount would have been written into someone's money records. This is the number that matters.

### tier-a — native-recorded market utterances (Nigerian Pidgin/Yoruba/English), parse ground truth

| Model | Transaction exact | Amount safe | **Amount corrupted** | Numeric accuracy |
|---|---|---|---|---|
| `chirp-3` | 29% | 93% | **7%** | 71% |
| `gpt-4o-transcribe` | 53% | 100% | **0%** | 80% |
| `mai-transcribe-2` | 60% | 100% | **0%** | 80% |
| `omnilingual-ctc-300m` | 13% | 100% | **0%** | 53% |
| `parakeet-tdt` | 33% | 100% | **0%** | 80% |
| sahara *(5 Aug snapshot)* | 47% | 93% | **7%** | 73% |
| `sahara-v2.5` | 47% | 100% | **0%** | 67% |
| `whisper-large-v3` | 27% | 100% | **0%** | 67% |

### tier-sh — native-recorded Shona/English market utterances, parse ground truth (NEW for Phase 2)

| Model | Transaction exact | Amount safe | **Amount corrupted** | Numeric accuracy |
|---|---|---|---|---|
| `chirp-3` | 13% | 100% | **0%** | 53% |
| `gpt-4o-transcribe` | 13% | 93% | **7%** | 67% |
| `mai-transcribe-2` | 13% | 87% | **13%** | 53% |
| `omnilingual-ctc-300m` | 27% | 100% | **0%** | 47% |
| `parakeet-tdt` | 7% | 87% | **13%** | 93% |
| `sahara-v2.5` | 27% | 100% | **0%** | 40% |
| `whisper-large-v3` | 7% | 87% | **13%** | 60% |

### Reading the primary result

**(a) No single model wins, and which one leads flips with the language.** On Pidgin/Yoruba — a *documented Sahara code-switch pair* — Microsoft's MAI-Transcribe-2 records the most transactions exactly (60%) and corrupts none, ahead of GPT-4o-transcribe (53%) and Sahara (47%). On Shona — a supported Sahara *language* but **not** a code-switch pair — that ordering inverts: Sahara leads at 27% with zero corruption, double the best frontier system, while MAI drops to 13% and corrupts 13%.

**The pattern is linguistic distance from English, not African speech in general.** Nigerian Pidgin is lexically English-adjacent, so a strong general-purpose recogniser can largely cope with it; Shona is not, and the frontier systems collapse there while the Africa-trained model holds. An earlier draft of this report — written when the comparison set was only two Whisper models and an open 300M baseline — concluded that "there is currently one viable ASR". Running a genuinely strong field falsified that, and we would rather publish the correction than the flattering version. The practical advice for an integrator is not "use Sahara" or "use a frontier API" but **benchmark on your own language and your own task**, because the ranking does not transfer between them.

**(b) The corruption inversion.** A weaker model can post a *lower* amount-corrupted rate than a stronger one — not because it is safer, but because its output is noise the grammar refuses to parse, which the agent turns into a clarifying question. A plausible-but-wrong transcript is more dangerous than an obviously garbled one, because only the plausible one survives parsing and reaches the ledger. Downstream safety has to be engineered; it cannot be inferred from accuracy.

**(c) An honest caveat on our own metric.** Where the expected outcome is *clarify*, a garbled transcript also produces *clarify*, and scores as an exact match. One Whisper row earns 'exact' on a Shona clip by hallucinating "Thank you for watching. This is Mrs. Jessie." — which our grammar correctly refuses to log. The credit is real (nothing wrong was written) but it is not comprehension, and we flag it rather than bank it.

## 2. Standard transcription metrics (WER / CER)

Reported for comparability with general-purpose leaderboards. Both normalised and raw are given, matching Intron's own `Intron-Multimodal-Benchmarking` practice; CER is included because Microsoft's PazaBench leads with it, and because it is the fairer metric for morphologically rich languages where one wrong affix costs an entire word under WER. Normalisation = lowercase, punctuation stripped, whitespace collapsed, diacritics folded (jiwer-standard conventions; Intron does not publish its own normaliser, so ours is stated rather than claimed identical).

### tier-b — AfriSwitch code-switched broadcast speech, transcript ground truth only

| Model | clips | WER (norm) | WER (raw) | CER (norm) | CER (raw) |
|---|---|---|---|---|---|
| `chirp-3` | **39/40** | 0.376 | 0.500 | 0.241 | 0.272 |
| `gpt-4o-transcribe` | 40/40 | 0.590 | 0.704 | 0.455 | 0.499 |
| `mai-transcribe-2` | 40/40 | 0.476 | 0.613 | 0.195 | 0.256 |
| `omnilingual-ctc-300m` | 40/40 | 0.837 | 0.864 | 0.614 | 0.638 |
| `parakeet-tdt` | 40/40 | 0.642 | 0.761 | 0.385 | 0.431 |
| sahara *(5 Aug snapshot)* | 40/40 | 0.424 | 0.562 | 0.278 | 0.309 |
| `sahara-v2.5` | 40/40 | 0.369 | 0.472 | 0.227 | 0.252 |
| `whisper-large-v3` | 40/40 | 0.765 | 0.851 | 0.506 | 0.528 |

*A bold clip count marks partial coverage: that model was scored on a subset of this tier, so its row is indicative and not strictly like-for-like with the full-coverage rows. We show the denominator rather than quietly averaging over a different sample.*

### tier-a — native-recorded market utterances (Nigerian Pidgin/Yoruba/English), parse ground truth

| Model | clips | WER (norm) | WER (raw) | CER (norm) | CER (raw) |
|---|---|---|---|---|---|
| `chirp-3` | **14/15** | 0.778 | 0.907 | 0.598 | 0.661 |
| `gpt-4o-transcribe` | 15/15 | 0.652 | 0.789 | 0.404 | 0.514 |
| `mai-transcribe-2` | 15/15 | 0.663 | 0.839 | 0.496 | 0.583 |
| `omnilingual-ctc-300m` | 15/15 | 0.861 | 0.918 | 0.542 | 0.588 |
| `parakeet-tdt` | 15/15 | 0.651 | 0.760 | 0.413 | 0.491 |
| sahara *(5 Aug snapshot)* | 15/15 | 0.602 | 0.704 | 0.477 | 0.528 |
| `sahara-v2.5` | 15/15 | 0.574 | 0.680 | 0.490 | 0.512 |
| `whisper-large-v3` | 15/15 | 0.963 | 1.054 | 0.710 | 0.786 |

*A bold clip count marks partial coverage: that model was scored on a subset of this tier, so its row is indicative and not strictly like-for-like with the full-coverage rows. We show the denominator rather than quietly averaging over a different sample.*

### tier-sh — native-recorded Shona/English market utterances, parse ground truth (NEW for Phase 2)

| Model | clips | WER (norm) | WER (raw) | CER (norm) | CER (raw) |
|---|---|---|---|---|---|
| `chirp-3` | 15/15 | 0.900 | 0.963 | 0.467 | 0.493 |
| `gpt-4o-transcribe` | 15/15 | 1.018 | 1.075 | 0.402 | 0.480 |
| `mai-transcribe-2` | 15/15 | 0.869 | 0.927 | 0.399 | 0.437 |
| `omnilingual-ctc-300m` | 15/15 | 0.790 | 0.870 | 0.342 | 0.364 |
| `parakeet-tdt` | 15/15 | 1.131 | 1.241 | 0.478 | 0.555 |
| `sahara-v2.5` | 15/15 | 0.566 | 0.714 | 0.328 | 0.346 |
| `whisper-large-v3` | 15/15 | 1.232 | 1.291 | 0.537 | 0.642 |

### The backend moved under us, and not uniformly

We hold cached Sahara transcripts for the same frozen audio from **5 August** and from **9 September**. The API exposes no model or version field, so this cache is the only evidence available that anything changed — and something did:

| Tier | WER 5 Aug → 9 Sep | CER 5 Aug → 9 Sep | Numeric accuracy 5 Aug → 9 Sep |
|---|---|---|---|
| afriswitch-sample | 0.424 → 0.369 | 0.278 → 0.227 | – |
| sautiledger-clips | 0.602 → 0.574 | 0.477 → 0.490 | 73% → 67% |

Broadcast speech improved clearly. Our native market tier is more mixed: aggregate WER improved slightly while **numeric accuracy went down**, and individual clips regressed — `"I don sell 3 derica of rice 5,500."` in August became `"I don sell 3 of rice 500"` in September, losing both the unit and a factor of ten. We report this without complaint: models are retrained, and improving the average while regressing a subset is normal. The problem is that **an integrator cannot tell**. Without a version identifier in the response, no benchmark against this API is reproducible, and no regression is attributable. That is why §9 asks for one.

**A caveat on WER for financial speech.** Sahara transcribes spoken "five thousand five" as "5,500" — semantically exact, but every such token counts as a word error against a spoken-form reference. WER penalises the model for being *more* useful downstream. This is precisely why the task-completion metric in §1 leads this report.

## 3. Performance disparity across speaker groups

The organisers recommended ASR-FairBench (Rai et al., *Measuring and Benchmarking Equity Across Speech Recognition Systems*, Interspeech 2025), which argues that a single aggregate WER hides systematic disparities between speaker groups, and combines fairness with accuracy into a Fairness-Adjusted ASR Score. We cannot compute FAAS itself — it requires the Fair-Speech corpus with per-speaker demographic labels and a mixed-effects Poisson regression over hundreds of speakers, and our corpus has four speaker groups — but the underlying point applies directly, so we report the disparity rather than hiding behind an average.

Group = corpus tier × language, which here also separates speakers (tier-a is one Nigerian male speaker; tier-sh is one Zimbabwean female speaker; tier-b is many broadcast speakers across languages).

| Model | afriswitch WER | sautiledger WER | sh WER | **Disparity (worst ÷ best)** |
|---|---|---|---|---|
| `chirp-3` | 0.376 | 0.778 | 0.900 | **2.39×** |
| `gpt-4o-transcribe` | 0.590 | 0.652 | 1.018 | **1.73×** |
| `mai-transcribe-2` | 0.476 | 0.663 | 0.869 | **1.83×** |
| `omnilingual-ctc-300m` | 0.837 | 0.861 | 0.790 | **1.09×** |
| `parakeet-tdt` | 0.642 | 0.651 | 1.131 | **1.76×** |
| sahara *(5 Aug snapshot)* | 0.424 | 0.602 | – | **1.42×** |
| `sahara-v2.5` | 0.369 | 0.574 | 0.566 | **1.56×** |
| `whisper-large-v3` | 0.765 | 0.963 | 1.232 | **1.61×** |

A model with a low average but a high disparity ratio is not a model that works for everyone — it is a model that works for whoever resembles its training data. For a product whose users are, by definition, the speakers least represented in mainstream speech corpora, that ratio is a product risk, not a footnote.

## 4. An attempted ablation, reported as a null result

Sahara's documentation states that the sync endpoint applies LLM corrections to transcripts **by default** (`use_disable_llm_corrections`, default FALSE). If true, every integrator benchmarks a recogniser *plus a rewriter* without necessarily knowing it — a confound worth isolating. We therefore ran the entire corpus twice, identical audio, with the flag unset and set to `TRUE`.

**The two runs produced byte-identical transcripts on all 70 clips.** Every metric matches to three decimals, so the ablation yields no signal and we report it as a null result rather than as a second model. We verified this is not a client-side bug by issuing both requests directly against the API: same audio, same output. A third request supplying an invalid value (`use_disable_llm_corrections=BANANA`) was also accepted with HTTP 200 and the same transcript, which suggests the field is not being read on this path — consistent with the silently-ignored-field behaviour reported in §9.

Two readings are consistent with the evidence and we cannot distinguish them from outside: either the flag is not wired on this endpoint, or LLM correction is not applied for this language configuration in the first place, so disabling it changes nothing. Either way the practical conclusion for integrators is the same: **the documented control does not currently change what you get.** The `sahara-v2.5` rows above are therefore the as-deployed configuration, and no separate 'raw' row is presented — including one would inflate our model count with a duplicate.

## 5. A prediction registered in advance: Shona

Before running this benchmark we recorded a falsifiable prediction (`bench/PHASE-G-NOTES.md`, committed 3 September, before any Shona audio existed): Sahara's documentation lists Shona (`sn`) as a supported STT language **and** a supported TTS voice, but Shona is *not* among its 12 documented code-switching pairs. Our Shona validator's utterances are heavily code-mixed by design ("Ndatengesa three cups dze rice nefive dollars fifty"). We therefore predicted degraded performance on tier-sh relative to tier-a, and said so before we could see the result.

| Model | tier-a WER | tier-sh WER | tier-sh transaction exact | **tier-sh amount corrupted** |
|---|---|---|---|---|
| `chirp-3` | 0.778 | 0.900 | 13% | **0%** |
| `gpt-4o-transcribe` | 0.652 | 1.018 | 13% | **7%** |
| `mai-transcribe-2` | 0.663 | 0.869 | 13% | **13%** |
| `omnilingual-ctc-300m` | 0.861 | 0.790 | 27% | **0%** |
| `parakeet-tdt` | 0.651 | 1.131 | 7% | **13%** |
| `sahara-v2.5` | 0.574 | 0.566 | 27% | **0%** |
| `whisper-large-v3` | 0.963 | 1.232 | 7% | **13%** |

**Outcome: half right — and the half we got wrong is the informative half.** We predicted degradation, unqualified. On **WER we were wrong**: Shona WER (0.566) is marginally *better* than our Pidgin tier (0.574), and Shona CER is better still. A transcription-only benchmark would have concluded that Shona is well supported and moved on. On **task completion we were right**: transaction-exact falls from 47% to 27% on the same system. We record the prediction as partly falsified rather than quietly reframing it, because the gap between those two verdicts is the entire argument of this report.

**The mechanism is visible in the transcripts.** Sahara transcribes the Shona *lexicon* well — `ndatengesa`, `matomatisi`, `chikwereti`, `rechibage`, `enzungu`, `dzemazai` all come back intact or near-intact. What collapses is precisely the **code-switched English money phrase**:

| she said | Sahara heard |
|---|---|
| "…ne**five dollars fifty**" | `ne50` |
| "ne **forty five dollars**" | `ne45 vose` |
| "**ethree dollars**" | `etridos` |
| "**yeten dollars**" | `yetendo` |
| "ne **two dollars**" | `netudle` |

The currency word is swallowed into the numeral and the amount is lost. That is exactly the failure a language supported for transcription but *not* for code-switching would produce, and it is why we registered the prediction in advance rather than after seeing the data.

**Two things follow.** First, WER hid the failure and the task-completion metric exposed it — which is why the ordering of this report is not cosmetic. Second, the safety layer converts the gap into a question rather than a wrong number — on these 15 Shona clips Sahara produced **no corrupted amounts and 15/15 amount-safe outcomes**, because when the price phrase collapses the grammar refuses to guess and asks. Fifteen clips from one speaker cannot establish that the design *is* safe for Shona commerce; what they show is that on every failure we observed, the failure mode was a question rather than a wrong number — which is the behaviour the design intends, tested where the ASR is weakest.

**The comparison across the two native tiers is where this benchmark earns its keep.** Sahara ranks *third* on Pidgin/Yoruba (47% exact, behind MAI-Transcribe-2 at 60% and GPT-4o-transcribe at 53%) and *first* on Shona (27%, double the best frontier system, with zero corrupted amounts). The frontier models do not degrade gently on Shona — they collapse, and three of them start corrupting amounts as they do.

**A hypothesis, not a demonstrated cause.** The most economical explanation we can offer is *linguistic distance from English*: Pidgin shares most of its lexicon with English, so a strong general recogniser can approximate it, while Shona does not. If that reading were right, code-switch-specific training would be worth most exactly where general models are worst. **This benchmark cannot establish it.** Our two native tiers differ not only in language but in speaker, gender, microphone, room and recording session — one Nigerian man and one Zimbabwean woman, fifteen clips each. Any of those could produce the same reversal. What is measured here is that **the ranking changed**; why it changed would need matched speakers across languages, or the same speakers across both, which is the obvious next experiment and one we have not run.

The per-clip transcripts add a nuance the aggregate hides: on Shona the two systems split the sentence between them. Sahara recovers the Shona words and loses the English price (`Ndatengesa three cups dze rice nefive dollars fifty` → `ndatengesa 3 ne50`), while the frontier systems do the opposite — chirp-3 returns `Ndatengeza three cups of rice ne $5.50`, with the amount intact but the verb and concord degraded. Sahara still wins the transaction metric because our grammar can refuse a missing amount safely but cannot recover a missing item; a system that loses the *noun* fails more gracefully than one that loses the *number*. That asymmetry is a property of the downstream task, not of the recognisers, and it is invisible to WER.

It also inverts the naive procurement conclusion. A team benchmarking only on Pidgin would pick MAI-Transcribe-2 and then discover it corrupts 13% of Shona amounts. A team benchmarking only on Shona would pick Sahara and leave 13 points of Pidgin accuracy on the table. The ranking does not transfer across languages, so it has to be measured per language and per task.

**What is not finished.** Packs drive parsing, not phrasing: run the Shona pack and the agent parses `Ndatengesa matomatisi ethree dollars` correctly and does the arithmetic in dollars and cents — then answers in Pidgin, because the reply templates are not yet pack-driven. We report this rather than demo around it.

The Shona corpus was built the same way the Pidgin/Yoruba one was: a native speaker rewrote every drafted sentence into what a trader would actually say, chose the currency register (US dollars, spoken as "two fifty" for $2.50), and recorded all 15 utterances herself. Her corrections taught the parser three things no outsider would have guessed: `hwani` marks per-unit pricing, concord prefixes glue onto code-switched numerals (`nefive`, `yeten`), and a trailing copula (`... pack is 4000`) marks a price rather than part of the item name.

## 6. Illustrative transcripts

**case01** — truth: `I don sell three derica of rice five thousand five`

- `chirp-3`: `I don't sell 3 L of rice 5005.`  ⚠ perfective_negation_inversion
- `gpt-4o-transcribe`: `I don sell three derica of rice five thousand five.`
- `mai-transcribe-2`: `I don't sell 3 dolika of rice 5005.`  ⚠ perfective_negation_inversion
- `omnilingual-ctc-300m`: `i don sow three the reca of rice`
- `parakeet-tdt`: `I don't sell three delica of rice five thousand five`  ⚠ perfective_negation_inversion
- `sahara-v2`: `I don sell 3 derica of rice 5,500.`
- `sahara-v2.5`: `I don sell 3 of rice 500`
- `whisper-large-v3`: `I don't sell three delica of rice, 5,005.`  ⚠ perfective_negation_inversion

**case08** — truth: `abeg how much I don make today`

- `chirp-3`: `A big, how much I don't make today?`  ⚠ perfective_negation_inversion
- `gpt-4o-transcribe`: `Abeg, how much I don make today?`
- `mai-transcribe-2`: `Abeg, how much I don't make today?`  ⚠ perfective_negation_inversion
- `omnilingual-ctc-300m`: `abeg amochadon make today`
- `parakeet-tdt`: `A beg, how much I don't make today?`  ⚠ perfective_negation_inversion
- `sahara-v2`: `Abeg, how much I don make today?`
- `sahara-v2.5`: `Abeg how much i don make today`
- `whisper-large-v3`: `I beg, how much I don't make today?`  ⚠ perfective_negation_inversion

**case21** — truth: `I don sell garri finish`

- `chirp-3`: `My guy, I don't say my gari finish, I don't say I'm finish.`
- `gpt-4o-transcribe`: `My guy, I no sell my garri finish o, I no sell am finish.`
- `mai-transcribe-2`: `Mo guy, I don't sell my galley finish, oh. I don't sell them finish.`  ⚠ perfective_negation_inversion
- `omnilingual-ctc-300m`: `mọgara a don se may gari finishoro adon se na finish`
- `parakeet-tdt`: `My guy, I don't say my guy finish though, I don't say them finish.`
- `sahara-v2`: `Mo guy, I no sell my garri finish oo, I no sell am finish.`
- `sahara-v2.5`: `Mo guy i don sell my garri finish oo i don sell am finish`
- `whisper-large-v3`: `My guy, I don't say my guy will finish you. I don't say he won't finish you.`

**case03** — truth: `I buy fuel ten thousand naira`

- `chirp-3`: `I buy fuel 10,000 Naira.`
- `gpt-4o-transcribe`: `I buy fuel 10,000 naira.`
- `mai-transcribe-2`: `I buy fuel 10,000 naira.`
- `omnilingual-ctc-300m`: `abi fol tentou air`
- `parakeet-tdt`: `I buy fuel ten thousand ayah`
- `sahara-v2`: `i buy fuel thousand naira`  ✗ AMOUNT CORRUPTED
- `sahara-v2.5`: `I buy fuel0 naira`
- `whisper-large-v3`: `Abai Fouil, 10,000 Naira`

**case10** — truth: `no no na five k not five thousand five`

- `chirp-3`: `No, no, now 5K not 5005.`  ✗ AMOUNT CORRUPTED
- `gpt-4o-transcribe`: `No, na five K, not five thousand five.`
- `mai-transcribe-2`: `No, no, na 5K, not 5005.`
- `omnilingual-ctc-300m`: `no no na  k nos`
- `parakeet-tdt`: `No no na five K not five thousand five`
- `sahara-v2`: `no no na 5 key not 500`
- `sahara-v2.5`: `No know na 5 k not 50005`
- `whisper-large-v3`: `No, no, not 5K, not 5,000, 5.`

**sh03** — truth: `Customer atora two mabuckets enzungu achiita two fifty hwani`

- `chirp-3`: `Customer athora ma bucket enzungu angachite 250 bucket 1.`
- `gpt-4o-transcribe`: `Customer atora mabuckets enzungu, angachita two-fifty bucket one.`  ✗ AMOUNT CORRUPTED
- `mai-transcribe-2`: `Customer athola mabaketi enzungu angachitha 250 bucket 1.`  ✗ AMOUNT CORRUPTED
- `omnilingual-ctc-300m`: `castome atora mabhakets enzungu angachita backet`
- `parakeet-tdt`: `Customer Autora ma bucket en Zungo and I cheat a two fifty bucket one.`
- `sahara-v2.5`: `kastum atora mabhaketi enzungu anga achiita 250 bake 1`
- `whisper-large-v3`: `customer atorama buckets in Zungu and got cheetah 250 bucket one`  ✗ AMOUNT CORRUPTED

## 7. Per-model assessment

**`chirp-3`** — Google's production ASR (distinct from Gemini). **Pros:** the second-best broadcast WER in the benchmark (0.376), close behind Sahara. **Cons:** 29% exact on our Pidgin/Yoruba tier with 7% corrupted, and it mangles market units — `three derica of rice` became `3 L of rice`. Two clips returned no transcript at all.

**`gpt-4o-transcribe`** — Frontier multimodal ASR; strong on clean accented English, unknown exposure to Pidgin/Yoruba market speech. Cloud-only and per-call priced.

**`mai-transcribe-2`** — Microsoft AI's multilingual STT (#1 on FLEURS across 60 languages), via OpenRouter at $0.10/hour. **Pros:** the strongest system on our Pidgin/Yoruba market tier — 60% of transactions exactly right with **zero corrupted amounts**, the best combination in the benchmark — and the best CER on broadcast speech. **Cons:** it collapses on Shona (13% exact, 13% corrupted), and it inverts the Pidgin perfective, turning a sale into its denial. Cloud-only.

**`omnilingual-ctc-300m`** — Meta's omnilingual-ASR (CTC, 300M), open weights (Apache-2.0), run locally via fairseq2. **Pros:** the strongest open model on our languages in Microsoft's PazaBench, claims 1,672 languages including `pcm_Latn` and `sna_Latn`, costs nothing to run, and is the only model in this benchmark that renders Yoruba numerals with correct diacritics. **Cons:** no Windows build (needs WSL/Linux), ~20s per clip on CPU, and it transcribes phonetically rather than semantically — it hears the words but drops or mangles the digits that a ledger depends on. **Operational cost:** full coverage was reached, but only after two passes were terminated by memory pressure on a CPU-only laptop, at roughly 1–2 minutes per clip against seconds for the hosted APIs. An open model you can self-host is only free if you have the hardware to run it.

**`parakeet-tdt`** — NVIDIA's Parakeet TDT 0.6B — the model family presented at Intron's own 28 August masterclass. **Pros:** never corrupted an amount on the Pidgin/Yoruba tier, good broadcast WER (0.642), and extremely cheap ($0.0015/min) thanks to non-autoregressive TDT decoding. **Cons:** 33% exact on Pidgin/Yoruba and 7% on Shona, where it also corrupts 13% — the speed advantage does not carry to code-switched market speech.

**sahara *(5 Aug snapshot)*** — No notes.

**`sahara-v2.5`** — **Pros:** the best WER on every tier; **tied first on Shona** with Meta's omnilingual-ASR (both 27% transactions exact, both zero corruption — double the best frontier system), and one of only two that render Nigerian Pidgin's perfective `I don sell` without inverting it into `I don't sell`. Ships TTS in the same voice register, so the readback speaks the user's language. **Cons:** it is *not* the strongest on its own flagship Pidgin/Yoruba pair — MAI-Transcribe-2 and GPT-4o-transcribe both record more transactions exactly. Cloud-only (offline deployment is enterprise-tier), no model/version field in responses, and the documented `use_disable_llm_corrections` control has no observable effect.

**`whisper-large-v3`** — **Pros:** strong general-purpose local model, fully offline, no per-call cost. **Cons:** three failure modes that matter here. It anglicises code-switched speech; it inverts Pidgin's perfective 'I don sell' into the negated 'I don't sell', reversing the meaning of a sale; and on low-resource African audio it **hallucinates its own training data** — two Shona clips returned "Thank you for watching my video" and "Thank you for watching. This is Mrs. Jessie.", fluent English sentences with no relationship to the audio. Most seriously, it turned a *correction* into a corrupted amount: the utterance "Aiwa yairi five dollars kwete five fifty" ("no, it was five dollars, **not** five fifty") was transcribed as "$5, kwete $5.50" and parsed to log 550 — the exact figure the trader was correcting away from.

## 8. Text-to-speech benchmark (round-trip)

SautiLedger speaks every confirmation aloud, so the TTS is part of the safety loop, not decoration: a trader who cannot hear the amount cannot catch our mistake. Intron asked TTS entrants to report hallucination, transcript loss, segment loss, WER and accuracy. The paper they cite (ASR-FairBench) is an ASR fairness benchmark and does not define these, so we define them explicitly and measure them by **round trip**: the app's real confirmation lines are synthesised, then transcribed back by a NEUTRAL third-party ASR (`whisper-small`, never Sahara's own recogniser, which would be same-vendor circular), and the transcript is compared to the input text.

| Metric | Definition |
|---|---|
| WER | (S+D+I)/N over the round trip |
| Accuracy | utterance-level exact match after normalisation |
| Transcript loss | D/N — input words that vanished in the audio |
| Hallucination | I/N — words that appeared from nowhere |
| Segment loss | longest contiguous deletion ÷ N — a dropped *phrase*, which D/N alone hides |
| **Amount survival** | did the money figure survive the round trip? |

| System | WER | Accuracy | Transcript loss | Hallucination | Segment loss | **Amount survival** |
|---|---|---|---|---|---|---|
| `sahara-tts-pidgin` | 0.514 | 0.00 | 0.141 | 0.000 | 0.120 | **100%** |
| `sahara-tts-yoruba` | 0.521 | 0.00 | 0.116 | 0.013 | 0.105 | **100%** |

### The benchmark immediately found a product bug

The first round trip came back like this:

> **said:** `Logged expense: fuel, ten thousand naira. Correct?`  
> **heard:** `Log the expense call on 410,000 naira, correct?`

"call on" is *colon*. The app was **reading its punctuation aloud to the trader**, and the spoken artefact was corrupting the amount in the round trip. This is a defect no WER table would have surfaced as anything but noise, and no unit test would have caught, because the string was correct — it was only wrong when spoken. We fixed it (`speakable()` in `tts.py`: colons and brackets become pauses, commas and full stops stay as prosody), added tests, and re-ran the identical benchmark:

| System | WER before → after | Hallucination before → after | **Amount survival before → after** |
|---|---|---|---|
| `sahara-tts-pidgin` | 0.598 → **0.514** | 0.117 → **0.000** | 91% → **100%** |
| `sahara-tts-yoruba` | 0.557 → **0.521** | 0.064 → **0.013** | 91% → **100%** |

Hallucination fell to zero and amount survival reached 100%. Both scorings are kept (`tts_metrics_punctuated.json` is the before), and the table above is the whole argument for benchmarking your own TTS rather than assuming a good voice is a good readback.

*Accuracy reads 0.00 for both systems: utterance-level exact match over a fifteen-word sentence is close to unattainable when the judge is a small ASR model — one substituted word anywhere loses the point. It is reported because Intron asked for it, but transcript loss, hallucination and amount survival carry the signal here.*

**What the round trip can and cannot tell you.** The judge is an ASR system, so these numbers measure a *chain* — voice plus recogniser — not the voice alone. We assume a weaker judge inflates both systems' error similarly, but that assumption is untested and need not hold: a recogniser can be differentially better on one accent than another, and both voices here are Sahara's, differing only in accent setting. The **before/after on a fixed voice and a fixed judge** is therefore the soundest reading in this section; the between-voice comparison is weaker, and the absolute WER weaker still. The readback also exists to be checked by a **human ear**, which handles accented speech far better than a small ASR model, so these figures are conservative by construction.

> **Note:** piper-local (offline neural TTS) was not benchmarked: no Nigerian Pidgin voice model exists for Piper, and an en_US voice cannot pronounce the code-switched readback. Set PIPER_VOICE to include it.
> **Note:** Browser speechSynthesis (the app's fallback voice) is NOT measurable here: Chrome renders it straight to the audio device with no capture path, so no round-trip audio can be obtained. It is described qualitatively in the report instead.
> **Note:** Round-trip judge was whisper-small, not the stronger whisper-large-v3: the benchmark machine is a CPU-only laptop and the larger judge exhausted memory. Absolute figures are therefore an upper bound on round-trip error, not a measure of the voices alone. We assume a weaker judge inflates both systems similarly, but that is an assumption we have not tested — a recogniser can be differentially worse on one accent — so the before/after on a fixed voice is the soundest comparison here, and the between-voice difference should be read as indicative only.

## 8b. Conversation benchmark (scripted replay)

Sections 1–7 score a **transcript** through the parser. That is not the same as a trader finishing a task: a real session has clarifying questions, confirmations, rejections and repairs, and an entry can be written wrongly and then corrected. This section measures the loop end to end — scripted transcripts replayed through **the real agent and a real SQLite ledger**.

**What this is not.** No audio recognition, no synthesis, no network, no LLM, and no human. Turns are scripted, so this measures our conversational logic, not user behaviour or task success with real people. It is a development benchmark and we label it as one; the millisecond figures are local Python and SQLite only.

| Measure | Value |
|---|---|
| Scenarios | 16 (15 graded, 1 control) |
| **Completed** | **12/15** (80%) |
| Controls behaving correctly | 1/1 |
| Median turns to completion | 2.0 |
| Scenarios that ever wrote a wrong amount | 2 |
| **Scenarios ending with a wrong amount** | **0** |

Two rows deserve emphasis. **A control scenario asserts the agent must NOT complete** — a sale with no price spoken has to end in a question, and counting that refusal as a failed task would reward guessing. It is scored separately rather than diluting the denominator. And the last two rows are deliberately different measures: an amount can be written wrongly and *then repaired*, so we count wrong amounts **at any turn**, not just at the end. 2 scenario(s) wrote a wrong amount at some point; 0 ended with one. A benchmark that only inspected the final ledger would have scored the repair as a clean run.

### Scenarios taken from a real session

Four scenarios are **verbatim turns from a field session** (device `671e01f8`, 10 September) rather than authored examples — what a trader actually typed when left alone with the app. They are kept in the suite while failing, because a benchmark you only add passing cases to stops being a measurement:

| Scenario | Completes | What the trader hit |
|---|---|---|
| `field-buyer-name-suffix` | yes | a buyer's name after the price (`…220 naira **for iya chinonso**`) is absorbed into the item, and the follow-up amount is then refused by the garbled-item guard |
| `field-yoruba-confirmation` | yes | `beeni` — Yoruba for yes — is not accepted as confirmation, so a correctly logged entry stays unconfirmed |
| `field-english-sales-query` | yes | `what are my sales today` is not recognised as a query, the most natural English phrasing of the app's core question |
| `field-yoruba-query` | yes | `kini gbogbo oja mi leni` — the same question in Yoruba — is likewise unrecognised |

None of these lose money: the ledger rows written were correct, and the failures are refusals and unanswered questions rather than wrong amounts. They are *task-completion* failures — the trader could not finish what she started — which is precisely the class this section exists to surface and the transcript benchmark cannot see.

## 9. Product feedback to Intron

Offered in the spirit the challenge asked for — everything below was observed while building on the API, with traces retained.

1. **Streaming STT never returns `COMMITTED_TRANSCRIPT`.** Sending `COMMIT` is answered with `INPUT_ERROR: "Error processing data"`, verified repeatedly (26 Aug, and again on v2.5 on 2 September with real-time-paced chunks). Our client works around it by treating the last `PARTIAL_TRANSCRIPT` as final. First partial arrives ~10s after commit, so streaming is currently slower than the sync endpoint for short utterances; we ship with streaming disabled and a one-variable switch to re-enable it.
2. **Unknown form fields are silently ignored.** Posting `language=pcm` instead of `use_language_asr_input=pcm` does not error — the request quietly falls back to English ASR and returns a confident, wrong-language transcript. This cost us a day of chasing a phantom model regression. Rejecting unknown `use_*` fields, or echoing the effective configuration in the response, would prevent an entire class of silent integration bugs.
3. **No model or version identifier in any response.** We measured deterministic changes in output on identical audio between 5 August and 2 September. Benchmarks are not reproducible against a moving, unlabelled backend; a `model_version` field would fix this.
4. **Shona is a supported language but not a supported code-switch pair.** AfriSwitch itself ships 3.86 h of Shona at CMI 24.55 — among the most balanced code-mixing in the dataset — so the data to close this gap already exists in-house.
5. **`use_disable_llm_corrections` appears to do nothing.** Documented with a default of FALSE, implying an LLM rewrites transcripts unless told otherwise. Setting it to `TRUE` returned byte-identical output on all 70 clips (§4), and an invalid value (`=BANANA`) was accepted with HTTP 200. Either the flag is unwired or corrections are not applied for this configuration; either way the documentation implies a control that integrators do not have.
6. **TTS accent values are language-named and undocumented in tutorials.** Finding `voice_language="pcm"` + `voice_accent="pidgin"` required probing; the combination is correct and produces a genuinely Nigerian voice, which materially improved how our testers received the app.

## 10. Related work and how this benchmark differs

- **PazaBench** (Microsoft Research Africa; `aka.ms/pazabench`) — the ASR leaderboard for low-resource languages, 61 African languages × 53 models. Snapshot taken 28 August (`results/pazabench-wer-2026-08-28.md`). Two verified gaps motivate this work: **Nigerian Pidgin does not appear among its 61 languages**, and **no Intron/Sahara model appears among its 53 models**. Note the precision: omnilingual-ASR *claims* `pcm_Latn` support, so the gap is in public *evaluation*, not claimed coverage — and to our knowledge this report contains the first published Pidgin numbers for it.
- **ASR-FairBench** (Rai et al., Interspeech 2025) — motivates §3. Their core argument, that aggregate accuracy conceals group disparity, is the reason we report per-group WER and a disparity ratio.
- **AfriSwitch** (`intronhealth/AfriSwitch`, CC BY-NC-SA 4.0) — 54.41 h / 16,602 code-switched utterances across 14 African languages, used for evaluation only, never redistributed, never used to train the product. **Version matters here and we were caught by it.** Our tier-b sample was drawn from the release as it stood before **7 September 2026, 21:25 UTC**, when the dataset was re-published. The headline totals are identical across that boundary — same 14 languages, same 54.41 hours, same 16,602 utterances — so a check of the summary figures (which is what we ran on the morning of the 7th) shows no change at all. The per-utterance data did change: utterances outside each language's 5th–95th percentile of characters-per-second were filtered out, code-mixing metrics were recomputed, and a `transcription_tagged` field marking English spans was added. The recomputation moved some figures sharply — **Pidgin's Code-Mixing Index went from 4.19 to 30.15**, from the lowest in the corpus to among the highest. Our cached Pidgin clips average CMI 4.63, consistent with the earlier release, which confirms which side of the boundary our sample sits on.
  
  We did not re-draw the corpus after this. Re-drawing would have invalidated every cached transcript and every number in this report four days before the deadline, and a frozen corpus is supposed to be pinned to a version — that is the point of publishing a manifest hash. So the tier-b results here describe the pre-7-September release, and we say so rather than citing the current statistics table as though our sample came from it. **The lesson generalises**: we asked Intron in §9 to expose a model version because an unlabelled moving backend makes benchmarks irreproducible, and the same argument applies to an unversioned dataset. A dated snapshot and a published hash are what let us notice this at all.
- **LyngualLabs Yoruba-English code-switching** — listed in Intron's code-switching collection and worth an honourable mention, but it is a **TTS model** (a VoxCPM2 fine-tune), not a corpus: it has no human audio paired with ground-truth transcripts, and benchmarking ASR on synthesised speech would be circular. It is therefore cited, not used.

**Mercy Muchai** (Microsoft Research Africa), at the same masterclass, made the point this corpus is built around: code-switching evaluation requires datasets that are themselves code-mixed — a single-language corpus cannot measure it. Our tier-a and tier-sh corpora are natively recorded code-mixed market speech, and tier-b is AfriSwitch.

## 11. Methodology, provenance and caveats

- **Corpus frozen before the first run.** The manifest sha256 is printed at the top of this report; no clip was added or dropped after seeing any result. Raw transcripts are cached per clip per model, so every number here is reproducible without re-spending API credits.
- **Provenance.** tier-a utterances were drafted by an AI assistant and then CORRECTED by a native Nigerian Pidgin/Yoruba speaker before recording; tier-sh identically, by a native Shona speaker (7 September). The sw-KE and ha-NG cases remain non-native drafts and are flagged as such — they are excluded from the recorded tiers rather than presented as validated. Even our test corpus needed native repair: that is the same gap the product exists to close.
- **Transaction accuracy** feeds each raw transcript through the shipped grammar-first normaliser with the LLM fallback disabled, so the number reflects deterministic behaviour only.
- **Diacritic folding.** omnilingual returns correctly accented Yoruba (`ẹgbẹrùn mẹ́ta`). Our scorer folds diacritics before comparison, because penalising a model for orthographic faithfulness the reference lacks would be a bias in *our* instrument. The fold is a no-op on ASCII output, so it does not advantage any model.
- **What the transaction metric does and does not measure.** Each transcript is passed through the shipped *normaliser* — the deterministic grammar — and the resulting ParseResult is compared to the expected one. It is **not** a simulation of the full conversation: the agent's commit gate, its unknown-item and suspicious-amount confirmations, the user's "yes"/"no" turn, and the actual database write are not exercised. Those gates can only convert a bad parse into a question, so a real session would corrupt no more often than these figures suggest — but "amount corrupted" should be read as *the parser would have produced a wrong amount*, not as *a wrong row reached a ledger*.
- **Caveats on generalisation.** Small n per tier (15 clips each on the native tiers). Tier-a is one Nigerian male speaker and tier-sh is one Zimbabwean female speaker, each recorded on their own device in their own room — so **language is confounded with speaker, microphone and acoustic environment**, and no cross-tier comparison here isolates the language. Sahara failures are reported unedited — the claim under test is downstream safety, not vendor perfection.
- **Retired model.** `whisper-small` appeared in our August workshop benchmark as a placeholder for a frontier model we had no key for. With frontier ASR available it is replaced by MAI-Transcribe-2 rather than left in as filler; it also never ran on the Shona tier, so it could not join the comparison that matters most here. Its workshop-era numbers remain in `REPORT-workshop-2026-08.md`.
