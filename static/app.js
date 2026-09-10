/* SautiLedger UI — no frameworks, no CDN, works with wifi off in offline mode. */
"use strict";

const $ = (id) => document.getElementById(id);
const chat = $("chat");

let restoredReview = false;
let replyLanguage = "en";
let languageBusy = false;
let voiceBusy = false;
let currencyCode = "NGN";
let currency = "₦"; // naira sign; swapped from /state
const CURRENCY_SIGNS = { NGN: "₦", KES: "KSh " };

// ---------------------------------------------------------------- state

async function refreshState() {
  try {
    const state = await (await fetch("/state")).json();
    currencyCode = state.currency;
    currency = CURRENCY_SIGNS[state.currency] || state.currency + " ";
    replyLanguage = state.reply_language || "en";
    if (!languageBusy) $("language-choice").value = `${state.pack || "pcm-yo-NG"}:${replyLanguage}`;
    renderLanguageExamples(state.pack);
    renderMode(state.mode);
    ttsMode = state.tts || "browser";
    if (!voiceBusy && state.voice) {
      $("voice-accent").value = state.preferred_accent || state.voice.accent;
      $("voice-gender").value = state.voice.gender;
      $("voice-accent").disabled = replyLanguage === "pcm";
      $("voice-summary").textContent = ttsMode === "sahara"
        ? `Intron voice · ${state.voice.accent} · ${state.voice.gender}` : "Device voice · offline playback";
    }
    streamMode = !!state.stream;
    renderEgress(state.egress_total, state.egress_log);
    renderLedger(state.entries, state.sales_total);
    renderConsent(state.retain_audio);
    if (!restoredReview) {
      restoredReview = true;
      if (state.review && state.review_reply) {
        updateSafetyReply(state.review_reply, null, state.review);
        bubble(state.review_reply, "sauti", true);
      }
    }
  } catch (err) {
    /* server briefly unreachable — keep last view */
  }
}

let currentMode = "offline";
function renderMode(mode) {
  currentMode = mode;
  const badge = $("mode");
  badge.textContent = mode === "cloud" ? "Voice online" : "Offline mode";
  badge.className = mode === "cloud" ? "cloud" : "offline";
}

function fmtKB(bytes) {
  return (bytes / 1024).toFixed(2) + " KB";
}

let egressLog = [];
let lastEgress = null;
function renderEgress(total, log) {
  egressLog = log || [];
  const el = $("egress-total");
  const zero = total === 0;
  el.textContent = fmtKB(total);
  el.title = `${total.toLocaleString()} bytes recorded`;
  $("egress").classList.toggle("zero", zero);
  if (lastEgress !== null && total > lastEgress && !reduceMotion) {
    // bytes just left: the meter visibly registers it
    el.classList.remove("flash");
    void el.offsetWidth;
    el.classList.add("flash");
  }
  lastEgress = total;
}

const reduceMotion = window.matchMedia
  && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// the total counts up to its new value — money arriving should feel like it
let lastTotal = null;
function renderTotal(newTotal) {
  const el = $("total");
  const show = (n) => { el.textContent = formatMoney(Math.round(n)); };
  if (lastTotal === null || newTotal === lastTotal || reduceMotion) {
    show(newTotal);
    lastTotal = newTotal;
    return;
  }
  const start = lastTotal, diff = newTotal - start, t0 = performance.now();
  const step = (t) => {
    const p = Math.min(1, (t - t0) / 450);
    show(start + diff * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  el.classList.remove("bump");
  void el.offsetWidth; // restart the animation
  el.classList.add("bump");
  lastTotal = newTotal;
}

const seenRowIds = new Set();
function formatMoney(amount, code = currencyCode) {
  // USD language packs store integer cents; naira/shillings use whole units.
  const minor = code === "USD";
  const sign = minor ? "$" : (CURRENCY_SIGNS[code] || code + " ");
  return sign + (Number(amount || 0) / (minor ? 100 : 1)).toLocaleString(undefined,
    { minimumFractionDigits: minor ? 2 : 0, maximumFractionDigits: minor ? 2 : 0 });
}

function renderLedger(entries, salesTotal) {
  renderTotal(salesTotal || 0);
  const active = (entries || []).filter(e => e.payment_status !== "voided");
  $("expenses-total").textContent = formatMoney(active.filter(e => e.type === "expense").reduce((n,e) => n + e.amount, 0));
  $("credit-total").textContent = formatMoney(active.filter(e => e.type === "sale" && e.payment_status === "credit").reduce((n,e) => n + e.amount, 0));
  const sales = active.filter(e => e.type === "sale").length;
  $("sales-caption").textContent = sales ? `${sales} ${sales === 1 ? "sale" : "sales"} in your book. One less thing to remember.` : "Your day starts here.";
  $("entry-count").textContent = active.length;
  $("book-empty").hidden = (entries || []).length > 0;
  const list = $("entries");
  list.replaceChildren();
  (entries || []).slice().reverse().forEach(e => {
    const li = document.createElement("li");
    const voided = e.payment_status === "voided";
    li.classList.toggle("expense", e.type === "expense");
    li.classList.toggle("voided", voided);
    if (!seenRowIds.has(e.id)) { li.classList.add("new"); seenRowIds.add(e.id); }
    const icon = document.createElement("span"); icon.className = "entry-icon";
    icon.textContent = voided ? "−" : e.type === "expense" ? "↗" : "↙";
    icon.setAttribute("aria-hidden", "true");
    const copy = document.createElement("div"); copy.className = "entry-copy";
    const item = document.createElement("span"); item.className = "item";
    item.textContent = e.item || "Entry";
    const meta = document.createElement("span"); meta.className = "entry-meta";
    const parts = [voided ? "Voided" : e.type === "expense" ? "Expense" : "Sale"];
    if (e.quantity) parts.push(`${e.quantity}${e.unit ? " " + e.unit : " items"}`);
    if (e.payment_status === "credit") parts.push("Credit" + (e.due ? " · " + e.due : ""));
    if (e.ts) parts.push(e.ts.slice(11,16));
    meta.textContent = parts.join(" · "); copy.append(item, meta);
    const amount = document.createElement("span"); amount.className = "amt";
    amount.textContent = (e.type === "expense" ? "−" : "") + formatMoney(e.amount);
    li.append(icon, copy, amount);
    if (!voided) {
      const btn = document.createElement("button"); btn.className = "del";
      btn.textContent = "Void"; btn.setAttribute("aria-label", `Void ${e.item || "entry"}, ${formatMoney(e.amount)}`);
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          const response = await fetch(`/void/${e.id}`, { method: "POST" });
          if (!response.ok) throw new Error("Void failed");
          const result = await response.json();
          updateSafetyReply(result.reply_text, null, result.review);
          await refreshState();
        } catch (_) { bubble("Could not remove this entry. Check your connection and try again.", "sauti"); btn.disabled = false; }
      });
      li.append(btn);
    }
    list.append(li);
  });
}

// ---------------------------------------------------------------- chat

function scrollToLatest() {
  const mobile = window.matchMedia("(max-width: 760px)").matches;
  const sc = mobile ? $("scroll") : $("conversation-panel");
  if (chat.childElementCount < 2 || (mobile && sc.dataset.view === "book")) return;
  sc.scrollTo({ top: sc.scrollHeight, behavior: reduceMotion ? "auto" : "smooth" });
}

function bubble(text, who, isQuestion) {
  if (who === "sauti" && chat.childElementCount > 0) selectView("conversation");
  const div = document.createElement("div");
  div.className = "bubble " + who + (isQuestion ? " question" : "");
  if (who === "sauti") {
    const label = document.createElement("span"); label.className = "bubble-label";
    label.textContent = "SAUTI"; div.append(label);
  }
  div.append(document.createTextNode(text));
  chat.appendChild(div);
  scrollToLatest();
}

let ttsMode = "browser"; // from /state: "sahara" = real Pidgin voice

function browserSpeak(text) {
  // Local browser TTS: synthesised on-device, nothing egresses.
  if (!window.speechSynthesis) return;
  const voices = window.speechSynthesis.getVoices();
  const voice = voices.find(v => v.localService && /^en[-_]NG$/i.test(v.lang))
    || voices.find(v => v.localService && /^en(?:[-_]|$)/i.test(v.lang));
  if (!voice) return; // Keep the full written reply; never use an unmetered remote voice.
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  u.lang = replyLanguage === "pcm" ? "en-NG" : "en";
  u.rate = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

let currentVoice = null;
let voiceRequest = 0;
async function speak(text) {
  const request = ++voiceRequest;
  if (currentVoice) { currentVoice.pause(); currentVoice = null; }
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  if (ttsMode !== "sahara") {
    $("voice-playback-status").textContent = "Device voice. Intron playback needs online mode and a configured API key.";
    browserSpeak(text); return;
  }
  $("voice-playback-status").textContent = "Preparing Intron voice…";
  try {
    const form = new FormData(); form.append("text", text);
    const resp = await fetch("/tts", { method:"POST", body:form });
    if (request !== voiceRequest) return;
    if (resp.status !== 200) throw new Error("Voice unavailable");
    const url = URL.createObjectURL(await resp.blob());
    if (request !== voiceRequest) { URL.revokeObjectURL(url); return; }
    const audio = new Audio(url); currentVoice = audio;
    audio.onended = () => { URL.revokeObjectURL(url); if (request === voiceRequest) $("voice-playback-status").textContent = ""; };
    audio.onerror = () => { URL.revokeObjectURL(url); if (request === voiceRequest) $("voice-playback-status").textContent = "Playback failed. Your written reply remains available."; };
    await audio.play();
    if (request === voiceRequest) $("voice-playback-status").textContent = "Playing Intron voice";
  } catch (err) {
    if (request === voiceRequest) $("voice-playback-status").textContent = "Intron voice is unavailable. Read the reply or use Hear again to retry.";
  } finally { await refreshState(); }
}

let statusBubble = null;
function showStatus(text) {
  clearStatus();
  $("voice-status").textContent = text;
  statusBubble = document.createElement("div");
  statusBubble.className = "bubble sauti status";
  statusBubble.textContent = text;
  chat.appendChild(statusBubble);
  scrollToLatest();
}
function clearStatus() {
  if (statusBubble) { statusBubble.remove(); statusBubble = null; }
  $("voice-status").textContent = "Hold the mic, talk, then release.";
}

let sending = false;
function setSending(value) {
  sending = value;
  ["send", "confirm-yes", "confirm-no", "talk", "language-choice"].forEach(id => { $(id).disabled = value; });
}
async function submit(formData, shownText) {
  if (sending) return;
  setSending(true);
  if (shownText) bubble(shownText, "you");
  showStatus("Working on your entry…");
  try {
    const resp = await fetch("/utterance", { method: "POST", body: formData });
    const body = await resp.json();
    clearStatus();
    if (!resp.ok) {
      bubble(body.error || "Something went wrong. Please try again.", "sauti");
      return;
    }
    if (!shownText && body.transcript) bubble(body.transcript, "you");
    if (!body.error) updateSafetyReply(body.reply_text, body.parse, body.review);
    bubble(body.reply_text, "sauti", body.reply_text.includes("?"));
    speak(body.reply_text);
  } catch (err) {
    clearStatus();
    bubble("Could not reach your book. Check your connection and try again.", "sauti");
  } finally {
    setSending(false);
  }
  refreshState();
}

// ------------------------------------------------- voice-clip retention

function renderConsent(on) {
  const box = $("retain");
  if (document.activeElement !== box) box.checked = !!on;
  $("consent").classList.toggle("on", !!on);
  $("retention-state").textContent = box.checked ? "Saving new clips" : "Not saving new clips";
  $("retention-position").textContent = box.checked ? "ON" : "OFF";
}

// debounced: rapid flicking settles to ONE saved state and ONE bubble
let consentTimer = null;
let consentAnnounced = null;
$("retain").addEventListener("change", () => {
  $("consent").classList.toggle("on", $("retain").checked); // instant visual
  $("retention-state").textContent = $("retain").checked ? "Saving new clips" : "Not saving new clips";
  $("retention-position").textContent = $("retain").checked ? "ON" : "OFF";
  clearTimeout(consentTimer);
  consentTimer = setTimeout(async () => {
    const on = $("retain").checked;
    if (on === consentAnnounced) return;
    const form = new FormData();
    form.append("retain_audio", on ? "true" : "false");
    try {
      await fetch("/consent", { method: "POST", body: form });
      consentAnnounced = on;
      bubble(on
        ? "Voice-clip retention is now on. You can turn it off anytime."
        : "Voice-clip retention is now off. No new clips will be retained.", "sauti");
    } catch (err) {
      bubble("Could not reach your book. Check your connection and try again.", "sauti");
    }
    refreshState();
  }, 400);
});

// ---------------------------------------------------------------- text input

$("send").addEventListener("click", sendText);
$("text").addEventListener("keydown", (e) => { if (e.key === "Enter") sendText(); });

function sendText() {
  if (sending || recordingRequested || live) return;
  const text = $("text").value.trim();
  if (!text) return;
  $("text").value = "";
  const form = new FormData();
  form.append("text", text);
  submit(form, text);
}

// ------------------------------------------------- live streaming voice
// Hold to talk and the words appear AS you speak: PCM goes up our
// egress-logged relay to Sahara's streaming STT, partials come straight
// back. Any failure falls back to the classic record-then-send path.

let streamMode = false; // from /state
let live = null;        // {ws, ctx, node, stream, bubble} while streaming

function downsampleTo16k(f32, fromRate) {
  const ratio = fromRate / 16000;
  const out = new Int16Array(Math.floor(f32.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const v = f32[Math.floor(i * ratio)] || 0;
    out[i] = Math.max(-1, Math.min(1, v)) * 0x7fff;
  }
  return out;
}

function liveBubbleSet(text) {
  if (!live) return;
  if (!live.bubble) {
    live.bubble = document.createElement("div");
    live.bubble.className = "bubble you";
    live.bubble.style.opacity = "0.7";
    chat.appendChild(live.bubble);
  }
  live.bubble.textContent = text;
  scrollToLatest();
}

async function startStreaming(stream) {
  const proto = location.protocol === "https:" ? "wss://" : "ws://";
  const ws = new WebSocket(proto + location.host + "/stream");
  ws.binaryType = "arraybuffer";
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const source = ctx.createMediaStreamSource(stream);
  const node = ctx.createScriptProcessor(4096, 1, 1);
  live = { ws, ctx, node, stream, bubble: null, done: false };

  node.onaudioprocess = (e) => {
    if (!live || live.ws.readyState !== WebSocket.OPEN) return;
    const pcm = downsampleTo16k(e.inputBuffer.getChannelData(0), ctx.sampleRate);
    live.ws.send(pcm.buffer);
  };

  ws.onmessage = (e) => {
    let msg;
    try { msg = JSON.parse(e.data); } catch (err) { return; }
    if (msg.type === "partial") {
      liveBubbleSet(msg.text);
    } else if (msg.type === "final") {
      finishStreaming(msg);
    } else if (msg.type === "error" || msg.type === "unavailable") {
      teardownStreaming();
      clearStatus();
      if (msg.reply_text) { bubble(msg.reply_text, "sauti"); speak(msg.reply_text); }
    }
  };
  ws.onerror = () => { teardownStreaming(); clearStatus(); };

  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onclose = reject;
    setTimeout(reject, 4000);
  });
  source.connect(node);
  node.connect(ctx.destination);
}

function finishStreaming(msg) {
  const b = live && live.bubble;
  teardownStreaming();
  clearStatus();
  setSending(false);
  if (msg.transcript) {
    if (b) { b.textContent = msg.transcript; b.style.opacity = "1"; }
  } else if (b) {
    b.remove();
  }
  if (!msg.error) updateSafetyReply(msg.reply_text, msg.parse, msg.review);
  bubble(msg.reply_text, "sauti", msg.reply_text.includes("?"));
  speak(msg.reply_text);
  refreshState();
}

function teardownStreaming() {
  setSending(false);
  if (!live) return;
  const l = live;
  live = null;
  try { l.node.disconnect(); } catch (err) {}
  try { l.ctx.close(); } catch (err) {}
  try { l.stream.getTracks().forEach((t) => t.stop()); } catch (err) {}
  if (l.ws.readyState === WebSocket.OPEN || l.ws.readyState === WebSocket.CLOSING) {
    setTimeout(() => { try { l.ws.close(); } catch (err) {} }, 8000);
  }
}

function stopStreaming() {
  if (!live) return;
  try { live.node.disconnect(); } catch (err) {}
  try { live.stream.getTracks().forEach((t) => t.stop()); } catch (err) {}
  if (live.ws.readyState === WebSocket.OPEN) {
    live.ws.send(JSON.stringify({ type: "stop" }));
    setSending(true);
    showStatus("Working on your entry…");
    // if the final never lands, don't hang the conversation
    const l = live;
    setTimeout(() => {
      if (live === l) {
        teardownStreaming();
        clearStatus();
        bubble("The connection was interrupted. Please try again.", "sauti");
      }
    }, 20000);
  } else {
    teardownStreaming();
  }
}

// ---------------------------------------------------------------- push-to-talk

let recorder = null;
let chunks = [];
let recordingRequested = false;

// Chrome and Firefox record webm; Safari on iOS and macOS records mp4 and
// nothing else. Asking for a type the browser cannot produce makes the
// MediaRecorder constructor throw, so pick one it actually supports.
function pickRecordingType() {
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) return "";
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) || "";
}

function extensionFor(mime) {
  if (mime.includes("mp4")) return "m4a";
  if (mime.includes("ogg")) return "ogg";
  return "webm";
}

// Say what actually went wrong. "Microphone unavailable" sent testers to
// check a microphone that was fine — the usual cause is a blocked
// permission, which needs a different action entirely.
function micFailure(err) {
  const name = (err && err.name) || "";
  if (name === "NotAllowedError" || name === "SecurityError") {
    bubble("Microphone permission is blocked. Allow the microphone for this site in your browser settings, then hold the button again. You fit type am instead for now.", "sauti");
  } else if (name === "NotFoundError" || name === "OverconstrainedError") {
    bubble("I no see any microphone for this device. You fit type your message instead.", "sauti");
  } else {
    bubble("The microphone no gree start (" + (name || "unknown error") + "). You fit type your message instead.", "sauti");
  }
}

let micPrimed = false;

async function startRecording() {
  if (recordingRequested || sending) return;
  recordingRequested = true;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (!recordingRequested) {
      stream.getTracks().forEach((t) => t.stop());
      // First run: the permission dialog steals the press-and-hold. The
      // finger lifts to tap "Allow", which cancels the recording before it
      // begins — so the user grants access and gets silence. Tell them it
      // worked and invite a fresh hold instead of failing quietly.
      if (!micPrimed) {
        micPrimed = true;
        bubble("Microphone ready now. Hold the green button again and talk.", "sauti");
      }
      return;
    }
    micPrimed = true;
    if (streamMode) {
      try {
        await startStreaming(stream);
        if (!recordingRequested) { stopStreaming(); return; }
        if (navigator.vibrate) navigator.vibrate(25);
        $("talk").classList.add("recording");
        $("talk-label").textContent = "LISTENING…";
        showStatus("Listening. Release the microphone when you finish.");
        return;
      } catch (err) {
        teardownStreaming(); // relay unreachable — classic path takes over
      }
    }
    chunks = [];
    const wanted = pickRecordingType();
    recorder = wanted ? new MediaRecorder(stream, { mimeType: wanted }) : new MediaRecorder(stream);
    const recordedType = recorder.mimeType || wanted || "audio/webm";
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunks, { type: recordedType });
      if (blob.size < 1000) {
        // accidental tap — teach the gesture instead of going silent
        bubble("That recording was too short. Hold the microphone while speaking, then release.", "sauti");
        return;
      }
      const form = new FormData();
      form.append("audio", blob, "utterance." + extensionFor(recordedType));
      submit(form, null);
    };
    recorder.start();
    if (navigator.vibrate) navigator.vibrate(25);
    $("talk").classList.add("recording");
    $("talk-label").textContent = "LISTENING…";
    showStatus("Listening. Release the microphone when you finish.");
  } catch (err) {
    recordingRequested = false;
    micFailure(err);
  }
}

function stopRecording() {
  recordingRequested = false;
  if (live) {
    if (navigator.vibrate) navigator.vibrate(12);
    $("talk").classList.remove("recording");
    $("talk-label").textContent = "HOLD TO TALK";
    stopStreaming();
    return;
  }
  clearStatus();
  if (recorder && recorder.state === "recording") {
    recorder.stop();
    if (navigator.vibrate) navigator.vibrate(12);
  }
  recorder = null;
  $("talk").classList.remove("recording");
  $("talk-label").textContent = "HOLD TO TALK";
}

const talk = $("talk");
talk.addEventListener("pointerdown", (e) => { e.preventDefault(); startRecording(); });
talk.addEventListener("pointerup", stopRecording);
talk.addEventListener("pointerleave", stopRecording);
talk.addEventListener("pointercancel", stopRecording);
talk.addEventListener("keydown", e => {
  if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); startRecording(); }
});
talk.addEventListener("keyup", e => {
  if (e.key === " " || e.key === "Enter") { e.preventDefault(); stopRecording(); }
});
talk.addEventListener("blur", () => { if (recordingRequested) stopRecording(); });

// ---------------------------------------------------------------- egress modal

$("egress").addEventListener("click", () => {
  const rows = $("egress-rows");
  rows.innerHTML = "";
  if (!egressLog.length) {
    rows.innerHTML = '<div class="empty">Nothing has ever left this device.</div>';
  } else {
    egressLog.forEach((r) => {
      const div = document.createElement("div");
      div.className = "erow";
      div.innerHTML =
        `<div class="top"><span>${r.ts.replace("T", " ")}</span><span>${fmtKB(r.bytes_sent)}</span></div>` +
        `<div class="purpose">${r.purpose} → ${r.destination}</div>` +
        `<div class="disp">${r.disposition}</div>`;
      rows.appendChild(div);
    });
  }
  $("modal").classList.add("open");
});
$("close").addEventListener("click", () => $("modal").classList.remove("open"));
// tapping the dimmed backdrop closes the sheet too — the gesture people expect
$("modal").addEventListener("click", (e) => {
  if (e.target === $("modal")) $("modal").classList.remove("open");
});

// ------------------------------------------------- welcome guide
// The landing experience lives in the app: three screens — what it is,
// how to talk, and the data story with the consent choice made openly.

const OB_KEY = "sauti_onboarded";
let obStep = 0;

function obSeen() {
  try { return !!localStorage.getItem(OB_KEY); } catch (err) { return false; }
}
function obMarkSeen() {
  try { localStorage.setItem(OB_KEY, "1"); } catch (err) { /* private mode */ }
}

function setObStep(n) {
  obStep = n;
  document.querySelectorAll(".ob-panel").forEach((p) =>
    p.classList.toggle("on", Number(p.dataset.step) === n));
  document.querySelectorAll(".dots span").forEach((d, i) =>
    d.classList.toggle("on", i === n));
  $("ob-next").textContent = n === 2 ? "Open my book" : "Continue";
}

function showOnboard() { $("retain-ob").checked = false; $("ob-consent").classList.remove("on"); setObStep(0); $("onboard").classList.add("open"); }

async function finishOnboard(skip = false) {
  obMarkSeen();
  $("onboard").classList.remove("open");
  if (!skip && $("retain-ob").checked) {
    // an explicit yes during welcome; never posts a silent no
    const form = new FormData();
    form.append("retain_audio", "true");
    try {
      await fetch("/consent", { method: "POST", body: form });
      consentAnnounced = true;
    } catch (err) { /* sheet toggle remains the fallback */ }
    refreshState();
  }
}

$("ob-next").addEventListener("click", () => {
  if (obStep < 2) setObStep(obStep + 1); else finishOnboard();
});
$("retain-ob").addEventListener("change", () => {
  $("ob-consent").classList.toggle("on", $("retain-ob").checked);
});
document.querySelectorAll(".chip-ex").forEach((chip) => {
  chip.addEventListener("click", () => {
    finishOnboard(true);
    $("text").value = chip.textContent;
    $("text").focus();
  });
});
$("welcome-help").addEventListener("click", showOnboard);
$("guide").addEventListener("click", () => {
  $("modal").classList.remove("open");
  showOnboard();
});

// A question stays outside the scrolling history until the next successful
// agent turn. Recording, typing, consent messages and failed requests never clear it.
let pendingReply = "";
function updateSafetyReply(text, parse, review = null) {
  const question = !!review || text.includes("?") || (parse && parse.intent === "clarify");
  renderTransactionReview(review);
  pendingReply = question ? text : "";
  $("reply-panel").hidden = !question;
  $("pending-reply").textContent = pendingReply;
  const confirm = review ? review.status === "recorded_awaiting_confirmation" : /correct\?/i.test(text);
  $("reply-kind").textContent = confirm ? "Check this entry · your answer matters" : "Please clarify";
  $("confirm-actions").hidden = !confirm;
  $("reply-dot").hidden = !question;
}
function renderTransactionReview(review) {
  const transaction = review && review.transaction;
  $("transaction-review").hidden = !transaction;
  if (!transaction) return;
  $("review-item").textContent = transaction.item || "Item to clarify";
  $("review-amount").textContent = transaction.amount == null
    ? "Amount to clarify" : formatMoney(transaction.amount, transaction.currency || currencyCode);
  const details = [];
  if (transaction.type) details.push(transaction.type === "expense" ? "Expense" : "Sale");
  if (transaction.quantity != null) details.push(`${transaction.quantity} ${transaction.unit || "items"}`);
  if (transaction.amount_each != null) details.push(formatMoney(transaction.amount_each, transaction.currency || currencyCode) + " each");
  if (transaction.payment_status === "credit") details.push("On credit");
  $("review-details").textContent = details.join(" · ");
  $("review-status").textContent = review.status === "not_recorded"
    ? "Not recorded — answer the question below."
    : "Recorded — please check. Rejecting this entry will void it.";
}
$("replay").addEventListener("click", () => { if (pendingReply) speak(pendingReply); });
function answer(text) { $("text").value = text; sendText(); }
$("confirm-yes").addEventListener("click", () => answer("yes"));
$("confirm-no").addEventListener("click", () => answer("no"));
$("ob-skip").addEventListener("click", () => finishOnboard(true));
$("egress").addEventListener("keydown", e => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("egress").click(); }
});
document.addEventListener("keydown", e => { if (e.key === "Escape") $("modal").classList.remove("open"); });
document.querySelectorAll("[data-view]").forEach(button => {
  if (button.tagName !== "BUTTON") return;
  button.addEventListener("click", () => selectView(button.dataset.view));
});
function selectView(view) {
  if ($("scroll").dataset.view === view) return;
  $("scroll").dataset.view = view;
  document.querySelectorAll("#view-tabs button").forEach(b => {
    const selected = b.dataset.view === view;
    b.classList.toggle("active", selected); b.setAttribute("aria-pressed", String(selected));
  });
  $("scroll").scrollTop = 0;
}
document.querySelectorAll("[data-prompt]").forEach(button => {
  button.addEventListener("click", () => { $("text").value = button.dataset.prompt; $("text").focus(); });
});
$("today-date").textContent = new Date().toLocaleDateString(undefined, {weekday:"short",day:"numeric",month:"short"});

// Mobile keyboards can shrink the visual viewport without changing 100dvh.
// Keep the question and composer inside the space the trader can actually see.
if (window.visualViewport) {
  const fitKeyboard = () => {
    document.body.style.height = window.visualViewport.scale === 1
      ? `${window.visualViewport.height}px` : "";
  };
  window.visualViewport.addEventListener("resize", fitKeyboard);
  fitKeyboard();
}

// ---------------------------------------------------------------- boot
bubble("Tell me about a sale or expense. If something is unclear, I will ask you.", "sauti");
if (!obSeen()) showOnboard();
refreshState();
setInterval(refreshState, 5000);

$("language-choice").addEventListener("change", async () => {
  languageBusy = true;
  $("language-choice").disabled = true;
  const [pack, reply] = $("language-choice").value.split(":");
  const form = new FormData();
  form.append("speech_pack", pack); form.append("reply_language", reply);
  try {
    const response = await fetch("/language", {method:"POST", body:form});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save language choice.");
    lastTotal = null;
    bubble(reply === "pcm" ? "You fit talk Pidgin, English or Yoruba. I go reply for Pidgin." : (pack === "sh-ZW" ? "You can speak Shona and English. Replies use English; this book uses US dollars." : "You can speak English, Pidgin or Yoruba. Replies will use English."), "sauti");
  } catch (error) { bubble(error.message, "sauti"); }
  finally { languageBusy = false; $("language-choice").disabled = false; await refreshState(); }
});

function renderLanguageExamples(pack) {
  const shona = pack === "sh-ZW";
  $("speech-example").textContent = shona ? "“Ndatengesa three cups dze rice nefive dollars fifty”" : "“I sell 3 cup of garri for 600 naira”";
  const examples = shona
    ? ["Ndatengesa matomatisi ethree dollars", "Ndatenga fuel for five dollars", "Ndawana marii nhasi"]
    : ["I sell rice for 600 naira", "I buy fuel for 1200 naira", "How much did I sell today?"];
  document.querySelectorAll(".chip-ex").forEach((chip, i) => { chip.textContent = examples[i]; });
  document.querySelectorAll("#suggestions button").forEach((button, i) => {
    button.dataset.prompt = shona ? ["ledger", "ndawana marii nhasi"][i] : ["Read my book", "How much did I sell today?"][i];
  });
}

async function saveVoiceChoice() {
  voiceBusy = true;
  $("voice-preview").disabled = true;
  const form = new FormData();
  form.append("accent", $("voice-accent").value); form.append("gender", $("voice-gender").value);
  try {
    const response = await fetch("/voice", {method:"POST", body:form});
    if (!response.ok) throw new Error("Could not save voice choice.");
    $("voice-playback-status").textContent = "Voice choice saved.";
  } catch (error) { $("voice-playback-status").textContent = error.message; }
  finally { voiceBusy = false; $("voice-preview").disabled = false; await refreshState(); }
}
$("voice-accent").addEventListener("change", saveVoiceChoice);
$("voice-gender").addEventListener("change", saveVoiceChoice);
$("voice-preview").addEventListener("click", () => speak(replyLanguage === "pcm"
  ? "This na SautiLedger. I go read your entry make you check am."
  : "This is SautiLedger. I will read your entry so you can check it."));
