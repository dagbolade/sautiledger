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
  } catch (err) {
    /* server briefly unreachable — keep last view */
  }
}

function renderMode(mode) {
  const badge = $("mode");
  badge.textContent = mode === "cloud" ? "CLOUD ASR" : "OFFLINE";
  badge.className = mode === "cloud" ? "cloud" : "offline";
}

function fmtKB(bytes) {
  return (bytes / 1024).toFixed(2) + " KB";
}

let egressLog = [];
function renderEgress(total, log) {
  egressLog = log || [];
  const el = $("egress-total");
  el.textContent = fmtKB(total);
  el.classList.toggle("nonzero", total > 0);
}

function renderLedger(entries, salesTotal) {
  $("total").textContent = currency + (salesTotal || 0).toLocaleString();
  const list = $("entries");
  list.innerHTML = "";
  (entries || []).filter((e) => e.payment_status !== "voided")
    .slice().reverse().forEach((e) => {
      const li = document.createElement("li");
      if (e.type === "expense") li.className = "expense";
      let what = e.item || "entry";
      if (e.quantity && e.unit) what += ` — ${e.quantity} ${e.unit}`;
      else if (e.quantity) what += ` ×${e.quantity}`;
      const credit = e.payment_status === "credit"
        ? ` <span class="credit">CREDIT${e.due ? " · due " + e.due : ""}</span>` : "";
      const sign = e.type === "expense" ? "-" : "";
      li.innerHTML = `<span>${what}${credit}</span>` +
        `<span class="amt">${sign}${currency}${(e.amount || 0).toLocaleString()}` +
        `<button class="del" data-id="${e.id}" title="void this entry">✕</button></span>`;
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

function bubble(text, who, isQuestion) {
  const div = document.createElement("div");
  div.className = "bubble " + who + (isQuestion ? " question" : "");
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function speak(text) {
  // Local browser TTS: synthesised on-device, nothing egresses.
  if (!window.speechSynthesis) return;
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

async function submit(formData, shownText) {
  if (shownText) bubble(shownText, "you");
  try {
    const resp = await fetch("/utterance", { method: "POST", body: formData });
    const body = await resp.json();
    if (!resp.ok) {
      bubble(body.error || "Something went wrong.", "sauti");
      return;
    }
    if (!shownText && body.transcript) bubble(body.transcript, "you");
    bubble(body.reply_text, "sauti", body.reply_text.trim().endsWith("?"));
    speak(body.reply_text);
  } catch (err) {
    bubble("No response from the app server.", "sauti");
  }
  refreshState();
}

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
      if (blob.size < 1000) return; // accidental tap
      const form = new FormData();
      form.append("audio", blob, "utterance.webm");
      submit(form, null);
    };
    recorder.start();
    $("talk").classList.add("recording");
    $("talk").textContent = "LISTENING...";
  } catch (err) {
    bubble("Mic unavailable — type the utterance instead.", "sauti");
  }
}

function stopRecording() {
  if (recorder && recorder.state === "recording") recorder.stop();
  recorder = null;
  $("talk").classList.remove("recording");
  $("talk").textContent = "HOLD TO TALK";
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

// ---------------------------------------------------------------- boot

bubble("Oya, talk your sale make I write am down.", "sauti");
let greetedEmpty = false;
(async () => {
  await refreshState();
  const state = await (await fetch("/state")).json().catch(() => null);
  if (!greetedEmpty && state && (state.entries || []).length === 0) {
    greetedEmpty = true;
    bubble("Ledger empty. Oya, talk your first sale.", "sauti");
  }
})();
setInterval(refreshState, 5000);
