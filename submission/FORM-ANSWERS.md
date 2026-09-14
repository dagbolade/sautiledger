# Submission form answers

Paste-ready answers for the Sahara CodeSwitch Africa Challenge form. Every
claim here matches the repository and the deployed app as of 14 September
2026. Word counts are in brackets; the form's targets are approximate.

**Website:** https://sautiledger-production.up.railway.app

**Solution title:** SautiLedger: a voice ledger for code-switching market traders

---

### 1. A short description of the problem your app addresses (~50)

Market traders and small farmers sell all day with their hands full, and their records live in their heads. Without books they cannot see profit, track who owes them, or show a lender what the business earns. Typing needs a free hand, and voice tools break when traders mix languages, which is nearly every sentence.

### 2. Target users and the potential number of users (~50)

Traders, farmers and kiosk owners in informal commerce who speak code-switched languages. Nigeria has 39.6 million micro, small and medium enterprises (SMEDAN/NBS, 2021); Zimbabwe has 1.9 million businesses, 86% informal and 71% rural (FinScope, 2022). We support Pidgin/Yoruba/English and Shona/English, field-tested on phones.

### 3. How your app solves the user problem (~50)

The trader just talks: "I don sell three derica of rice five thousand five." Sahara transcribes the mixed-language speech, and SautiLedger turns it into a ledger entry, reads it back aloud for a yes or no, answers questions such as "wetin remain?", accepts spoken corrections, and produces a trading statement a lender can read.

### 4. Does your solution support code-switching?

Yes.

### 5. Does your solution use the Sahara APIs?

Yes.

### 6. How is the solution agentic? What downstream task does the code-switched transcript enable? (~50)

The transcript drives bookkeeping, not just text. The agent decides whether each utterance is a sale, expense, question or correction; writes, voids and replaces ledger rows; calculates totals and net balance; and, when an amount is missing or looks wrong, asks the trader instead of guessing, before anything is written.

### 7. High-level technical overview: key design decisions, at least 3 architecture choices and the tradeoffs (~250)

**Grammar first, LLM as a guarded fallback.** A deterministic parser reads amounts, units and intent; a language model is consulted only when the grammar has no reading, and its answer is discarded if it contains an amount not literally spoken. Tradeoff: the app never invents money, but new phrasings need grammar updates. Preparing a new test set exposed unparsed teen numbers; the safety gate had caught them, and we fixed the grammar.

**Languages are data.** Each language is a YAML pack of numbers, units and trigger words, written with native speakers. Adding Shona meant a pack and a native-recorded test set, not new code. Tradeoff: every language needs native validation, so Swahili and Hausa ship marked unvalidated.

**One gate before every write.** Unfamiliar items and unusually shaped amounts are confirmed, and every entry is read back aloud. This exists because a real user's "5,700" was once transcribed as "570007". Tradeoff: an extra turn sometimes, instead of a silently wrong book.

**One audited network path.** A single module may touch the network, enforced by a test, and every transmission is logged and shown to the user. Tradeoff: on the hosted demo, audio and read-back text go to Sahara and unparsed text may go to a Hugging Face model, each disclosed; self-hosting keeps the book off our server and can disable the fallback.

**Sync ASR over streaming.** Streaming never returned a committed transcript and was slower for short utterances, so we use the sync endpoint.

We benchmarked seven ASR systems on transactions recorded correctly, not only WER.

### 8. Ethics/Inclusion: privacy, consent, safety, security and responsible data use (~100)

Every transmission is logged and shown in plain language: audio and read-back text go to Sahara, and on the hosted demo unparsed text may go to a Hugging Face model, labelled per call. Voice-clip retention is off by default. Nothing is written without an amount actually spoken, and wrong entries are voided, not deleted. Published benchmark audio comes only from speakers who consented to public release; tester recordings were excluded. Hosted books are isolated per device on our server; self-hosting keeps them on the operator's machine. Unvalidated languages are labelled as such.

---

**Demo video URL:** _(unlisted YouTube link, once filmed)_

**Benchmark report link:** _(Google Drive link to `submission/SautiLedger-Benchmark-Report.pdf`, "anyone with the link can view")_

**Benchmark audios link:** _(Hugging Face dataset URL, once uploaded)_

Sources for question 2: [SMEDAN/NBS MSME survey (2021)](https://www.nigerianstat.gov.ng/download/290); [FinScope MSME Survey Zimbabwe 2022](https://finmark.org.za/Publications/FinScope_MSME_Survey_Zimbabwe2022_findings.pdf).
