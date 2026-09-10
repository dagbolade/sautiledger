# Intron reply voices

Verified against the [accent catalogue](https://docs.voice.intron.io/docs/tts/supported-languages-and-accents)
and [synchronous generation contract](https://docs.voice.intron.io/docs/tts/tts-generate).
English uses `en` with Yoruba by default; Pidgin uses `pcm` / `pidgin`.
The English catalogue also lists Hausa, Igbo, Afrikaans, Luganda, Sepedi,
Swahili, Setswana, Xhosa and Zulu, each male/female. These are accent choices,
not additional transaction-parser languages. Shona TTS (`sn` / `shona`) is
listed, but the current Shona speech pack replies in English; it must therefore
use an English voice until native Shona reply templates are validated.

Enable `SAUTI_MODE=cloud`, `SAUTI_TTS=auto` and the existing `SAHARA_API_KEY`.
The app offers a synthetic voice preview in Conversation → Reply voice.
Keys remain server-side. Generation and WAV retrieval go through EgressRecorder;
voice preferences do not enable audio retention. Long text is rejected rather
than silently cutting off the final confirmation. The cache includes voice
language, accent, gender, text and a formatting version. Failed online playback
keeps the full written reply and offers retry instead of substituting device TTS.

Also reviewed [streaming TTS](https://docs.voice.intron.io/docs/tts/tts-streaming)
and [queued generation](https://docs.voice.intron.io/docs/tts/tts-queue).
Streaming is a useful next latency experiment, but its 10–100 character chunks
require a sentence-aware adapter, audio ordering, and reconnection tests to avoid
splitting amounts or dropping “Correct?”. This change uses complete synchronous
readbacks and cached replay. The remote Question Answering endpoint is not needed
for ledger queries; bookkeeping remains local and deterministic.
