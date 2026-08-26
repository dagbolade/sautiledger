/* SautiLedger UI — no frameworks, no CDN, works with wifi off in offline mode. */
"use strict";

const $ = (id) => document.getElementById(id);
const chat = $("chat");

let currency = "₦"; // naira sign; swapped from /state
const CURRENCY_SIGNS = { NGN: "₦", KES: "KSh " };

// ---------------------------------------------------------------- state

async function refreshState() {
  try {
    const state = await (await fetch("/state")).json();
    currency = CURRENCY_SIGNS[state.currency] || state.currency + " ";
    renderMode(state.mode);
    renderEgress(state.egress_total, state.egress_log);
    renderLedger(state.entries, state.sales_total);
    renderConsent(state.retain_audio);
  } catch (err) {
    /* server briefly unreachable — keep last view */
  }
}

let currentMode = "offline";
function renderMode(mode) {
  currentMode = mode;
  const badge = $("mode");
  badge.textContent = mode === "cloud" ? "CLOUD ASR" : "OFFLINE";
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
  el.textContent = zero && currentMode !== "cloud"
    ? "0.00 KB — nothing don leave this phone."
    : fmtKB(total);
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
  const show = (n) => { el.textContent = currency + Math.round(n).toLocaleString(); };
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
function renderLedger(entries, salesTotal) {
  renderTotal(salesTotal || 0);
  const list = $("entries");
  list.innerHTML = "";
  (entries || []).slice().reverse().forEach((e) => {
    const li = document.createElement("li");
    const classes = [];
    if (e.type === "expense") classes.push("expense");
    if (e.payment_status === "voided") classes.push("voided");
    if (!seenRowIds.has(e.id)) { classes.push("new"); seenRowIds.add(e.id); }
    li.className = classes.join(" ");
    const chip = e.quantity && e.unit ? `${e.quantity} ${e.unit}`
      : e.quantity ? `×${e.quantity}` : "";
    const credit = e.payment_status === "credit"
      ? `<span class="credit">CREDIT${e.due ? " · " + e.due : ""}</span>` : "";
    const sign = e.type === "expense" ? "-" : "";
    const voidBtn = e.payment_status === "voided" ? ""
      : `<button class="del" data-id="${e.id}" title="void this entry">✕</button>`;
    li.innerHTML =
      `<span class="item">${e.item || "entry"}</span>` +
      (chip ? `<span class="chip">${chip}</span>` : "") + credit +
      `<span class="amt">${sign}${currency}${(e.amount || 0).toLocaleString()}${voidBtn}</span>`;
    list.appendChild(li);
  });
  list.querySelectorAll(".del").forEach((btn) => {
    btn.addEventListener("click", async () => {
      // soft delete: the row is marked voided in the DB, never silently erased
      await fetch(`/void/${btn.dataset.id}`, { method: "POST" });
      refreshState();
    });
  });
}

// ---------------------------------------------------------------- chat

function scrollToLatest() {
  const sc = $("scroll");
  sc.scrollTo({ top: sc.scrollHeight, behavior: reduceMotion ? "auto" : "smooth" });
}

function bubble(text, who, isQuestion) {
  const div = document.createElement("div");
  div.className = "bubble " + who + (isQuestion ? " question" : "");
  div.textContent = text;
  chat.appendChild(div);
  scrollToLatest();
}

function speak(text) {
  // Local browser TTS: synthesised on-device, nothing egresses.
  if (!window.speechSynthesis) return;
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

let statusBubble = null;
function showStatus(text) {
  clearStatus();
  statusBubble = document.createElement("div");
  statusBubble.className = "bubble sauti status";
  statusBubble.textContent = text;
  chat.appendChild(statusBubble);
  scrollToLatest();
}
function clearStatus() {
  if (statusBubble) { statusBubble.remove(); statusBubble = null; }
}

async function submit(formData, shownText) {
  if (shownText) bubble(shownText, "you");
  showStatus("I dey reason am…");
  try {
    const resp = await fetch("/utterance", { method: "POST", body: formData });
    const body = await resp.json();
    clearStatus();
    if (!resp.ok) {
      bubble(body.error || "Something spoil small. Abeg try am again.", "sauti");
      return;
    }
    if (!shownText && body.transcript) bubble(body.transcript, "you");
    bubble(body.reply_text, "sauti", body.reply_text.trim().endsWith("?"));
    speak(body.reply_text);
  } catch (err) {
    clearStatus();
    bubble("Server no answer o. Check your network, then try again.", "sauti");
  }
  refreshState();
}

// ------------------------------------------------- voice-clip retention

function renderConsent(on) {
  const box = $("retain");
  if (document.activeElement !== box) box.checked = !!on;
  $("consent").classList.toggle("on", !!on);
}

// debounced: rapid flicking settles to ONE saved state and ONE bubble
let consentTimer = null;
let consentAnnounced = null;
$("retain").addEventListener("change", () => {
  $("consent").classList.toggle("on", $("retain").checked); // instant visual
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
        ? "I go dey keep your voice clips from now. You fit off am anytime."
        : "Okay — I no go keep your clips again.", "sauti");
    } catch (err) {
      bubble("Server no answer o. Check your network, then try again.", "sauti");
    }
    refreshState();
  }, 400);
});

// ---------------------------------------------------------------- text input

$("send").addEventListener("click", sendText);
$("text").addEventListener("keydown", (e) => { if (e.key === "Enter") sendText(); });

function sendText() {
  const text = $("text").value.trim();
  if (!text) return;
  $("text").value = "";
  const form = new FormData();
  form.append("text", text);
  submit(form, text);
}

// ---------------------------------------------------------------- push-to-talk

let recorder = null;
let chunks = [];

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunks = [];
    recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunks, { type: "audio/webm" });
      if (blob.size < 1000) {
        // accidental tap — teach the gesture instead of going silent
        bubble("That one too short o. Press and hold am, talk finish, then leave am.", "sauti");
        return;
      }
      const form = new FormData();
      form.append("audio", blob, "utterance.webm");
      submit(form, null);
    };
    recorder.start();
    if (navigator.vibrate) navigator.vibrate(25);
    $("talk").classList.add("recording");
    $("talk-label").textContent = "LISTENING…";
    showStatus("I dey hear you… leave am when you don talk finish.");
  } catch (err) {
    bubble("I no fit reach the mic o. Abeg type am for the box instead.", "sauti");
  }
}

function stopRecording() {
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
  $("ob-next").textContent = n === 2 ? "Start" : "Next";
}

function showOnboard() { setObStep(0); $("onboard").classList.add("open"); }

async function finishOnboard() {
  obMarkSeen();
  $("onboard").classList.remove("open");
  if ($("retain-ob").checked) {
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
    finishOnboard();
    $("text").value = chip.textContent;
    $("text").focus();
  });
});
$("guide").addEventListener("click", () => {
  $("modal").classList.remove("open");
  showOnboard();
});

// ---------------------------------------------------------------- boot

bubble("Oya, talk your sale make I write am down.", "sauti");
if (!obSeen()) showOnboard();
let greetedEmpty = false;
(async () => {
  await refreshState();
  const state = await (await fetch("/state")).json().catch(() => null);
  if (!greetedEmpty && state && (state.entries || []).length === 0) {
    greetedEmpty = true;
    bubble("Ledger empty. Hold the green button, talk your first sale, then leave am.", "sauti");
  }
})();
setInterval(refreshState, 5000);
