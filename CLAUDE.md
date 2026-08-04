# SautiLedger

Voice bookkeeping agent for African market traders. The trader speaks
naturally in code-switched African speech (Pidgin/Yoruba/English,
Swahili/English, Hausa/English), the agent logs transactions to a
local ledger, answers questions about it, and reads confirmations back.

## Hard constraints — never violate these
1. PRIVACY IS THE PRODUCT. The ONLY data that may ever leave this
   device is a short audio clip sent to the Sahara ASR API. The
   ledger, transcripts, agent reasoning, and queries NEVER touch the
   network. Any code that sends anything else is a bug.
2. Every network transmission MUST be logged to the egress ledger
   (timestamp, destination, purpose, bytes, disposition). The UI
   displays this. The app must be able to prove what it shared.
3. NEVER fabricate an amount or transaction detail. If a parse is
   ambiguous or empty, return a clarify intent. A confident wrong
   entry in someone's money records is the worst possible failure.
4. The normaliser is grammar-first and deterministic. The LLM is a
   fallback ONLY, and only where normaliser_tests.json permits.
5. Language support lives in config packs (packs/*.yaml). Adding a
   language = new pack file + new test cases. NO code changes.
6. Offline-swappable: ASR and TTS sit behind interfaces with cloud
   and local implementations selected by config, so Sahara's offline
   deployment can be dropped in without touching call sites.

## Stack
- Python 3.11, FastAPI backend, single-page vanilla JS frontend
  (browser mic capture via MediaRecorder)
- SQLite via sqlite3 stdlib — no ORM
- Agent LLM: local model via Ollama (assume `ollama run llama3.2:3b`
  is available; wrap it behind an LlmClient interface)
- ASR: AsrClient interface. Implementations: SaharaCloudAsr (HTTP),
  SaharaOfflineAsr (stub until confirmed), FakeAsr (returns text from
  test fixtures — used for all development)
- TTS: TtsClient interface. Implementations: PiperLocalTts,
  SaharaTts (stub), NullTts
- Tests: pytest. normaliser_tests.json is the source of truth.

## Style
- Small modules, typed, no cleverness. This ships Thursday morning.
- Every phase ends with passing tests and a one-line demo command.
- Commit after each phase with a clear message.
