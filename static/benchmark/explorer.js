"use strict";
const $ = id => document.getElementById(id);
const tierNames = {"sautiledger-clips":"Pidgin / Yoruba market speech", "sh-clips":"Shona / English market speech", "afriswitch-sample":"AfriSwitch broadcast speech"};
let evidence;
let audioClips = new Set();
let turn = 0;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text != null) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function option(value, label) { const el = node("option", label); el.value = value; return el; }
function stat(value, label) { const el = node("div", null, "stat"); el.append(node("strong",value),node("span",label)); return el; }
function money(amount, currency) {
  if (amount == null) return "No amount";
  const code = currency || "NGN";
  const sign = {NGN:"₦",USD:"$",KES:"KSh "}[code] || code + " ";
  return sign + (amount / (code === "USD" ? 100 : 1)).toLocaleString(undefined,{minimumFractionDigits:code === "USD" ? 2 : 0,maximumFractionDigits:code === "USD" ? 2 : 0});
}
function models() { return [...new Set(evidence.asr.map(r=>r.model))].filter(m=>$('controls').checked || !evidence.controls[m]).sort(); }
function modelLabel(model) { return model + (evidence.controls[model] ? " · " + evidence.controls[model] : ""); }
function selectedClip() { return evidence.clips.find(c=>c.tier===$("tier").value && c.id===$("clip").value); }
function expectedDescription(expected) {
  if (!expected) return "Transcript-only ground truth. Transaction metrics are not applicable.";
  if (expected.intent !== "log_transaction") return "Expected task: " + expected.intent.replaceAll("_"," ") + (expected.new_value != null ? " · " + expected.new_value : "");
  return [expected.type,expected.item,expected.quantity != null ? `${expected.quantity} ${expected.unit || "items"}` : null,money(expected.amount,expected.currency)].filter(Boolean).join(" · ");
}
function setModels() {
  const previous = $("model").value;
  $("model").replaceChildren(option("all","All systems"),...models().map(m=>option(m,modelLabel(m))));
  if (models().includes(previous)) $("model").value=previous;
}
function setClips() {
  $("clip").replaceChildren(...evidence.clips.filter(c=>c.tier===$("tier").value).map(c=>option(c.id,c.id)));
  renderComparison();
}
function resultBadge(row) {
  if (!row) return node("span","Not measured","badge neutral");
  if (!row.has_expected) return node("span","Transcript only","badge neutral");
  if (row.amount_corrupted) return node("span","Wrong amount","badge danger");
  if (row.exact_match) return node("span","Exact task match","badge");
  if (row.got_intent === "clarify") return node("span","Asked for clarification","badge");
  if (row.amount_safe) return node("span","Amount safe · task differs","badge neutral");
  return node("span","Task not completed","badge neutral");
}
function renderComparison() {
  const clip = selectedClip();
  if (!clip) return;
  $("clip-label").textContent = `${clip.id} · ${tierNames[clip.tier] || clip.tier}`;
  $("reference-text").textContent = clip.redacted ? "Transcript withheld — evaluation-only corpus. Numerical scores remain available." : clip.truth;
  $("expected").textContent = expectedDescription(clip.expected);
  const audio = $("reference-audio");
  audio.pause(); audio.removeAttribute("src");
  const available = audioClips.has(`${clip.tier}/${clip.id}`);
  audio.hidden = !available;
  if (available) audio.src=`audio/${encodeURIComponent(clip.tier)}/${encodeURIComponent(clip.id)}`;
  $("audio-note").textContent = available
    ? "Reference audio from this machine's evaluation corpus. Not included in the downloadable evidence."
    : "Audio is not bundled. Local playback is available via python -m bench.explorer --serve when the corpus file is present.";
  const shown = $("model").value === "all" ? models() : [$("model").value];
  $("comparison").replaceChildren(...shown.map(model=>{
    const row=evidence.asr.find(r=>r.model===model && r.tier===clip.tier && r.clip===clip.id);
    const card=node("article",null,"model-card");
    const head=node("div",null,"card-head"); head.append(node("h3",modelLabel(model)),resultBadge(row)); card.append(head);
    if (!row) { card.append(node("p","No cached output for this clip. Excluded from scored denominators.","transcript")); return card; }
    card.append(node("p",row.redacted ? "Transcript withheld — evaluation-only corpus." : row.hyp || "(Empty transcript)","transcript"));
    card.append(node("div",`WER ${Number(row.wer).toFixed(3)} · CER ${Number(row.cer).toFixed(3)}`,"card-metrics"));
    if (row.has_expected) {
      card.append(node("p",`Cached normaliser: ${(row.got_intent || "unknown").replaceAll("_"," ")} · ${money(row.got_amount,clip.expected && clip.expected.currency)}`,"outcome"));
      if (clip.expected && clip.expected.intent === "clarify" && row.exact_match) card.append(node("p","Expected clarification: an exact score does not establish comprehension.","flag"));
    }
    (row.flags || []).forEach(flag=>card.append(node("p",flag.replaceAll("_"," "),"flag")));
    return card;
  }));
  renderSummary();
}
function fraction(rows, field) {
  if (!rows.length) return "—";
  const n=rows.filter(r=>r[field]).length;
  return `${n}/${rows.length} (${Math.round(100*n/rows.length)}%)`;
}
function renderSummary() {
  const tier=$("tier").value;
  const total=evidence.clips.filter(c=>c.tier===tier).length;
  $("summary-rows").replaceChildren(...models().map(model=>{
    const rows=evidence.asr.filter(r=>r.model===model && r.tier===tier);
    const scored=rows.filter(r=>r.has_expected);
    const tr=node("tr");
    [modelLabel(model),`${rows.length}/${total}`,rows.length ? (rows.reduce((n,r)=>n+r.wer,0)/rows.length).toFixed(3) : "—",fraction(scored,"exact_match"),fraction(scored,"amount_safe"),fraction(scored,"amount_corrupted")].forEach(value=>tr.append(node("td",value)));
    return tr;
  }));
}
function renderConversation() {
  const scenario=evidence.conversations.results.find(r=>r.id===$("scenario").value);
  if (!scenario) return;
  turn=Math.min(turn,scenario.trace.length-1);
  const frame=scenario.trace[turn];
  $("scenario-summary").replaceChildren(node("h3",scenario.name),node("p",`${scenario.pack} · ${scenario.completed ? "Completed" : "Unresolved"} · ${scenario.turns_used} scripted turns`),node("p","Target: " + scenario.expected.map(r=>expectedDescription({...r,intent:"log_transaction"})).join("; ")));
  if (scenario.note) $("scenario-summary").append(node("p",scenario.note,"caveat"));
  $("turn-position").textContent=`Turn ${turn+1} of ${scenario.trace.length}`;
  $("previous-turn").disabled=turn===0;
  $("next-turn").disabled=turn===scenario.trace.length-1;
  const dialogue=node("article",null,"replay-card");
  dialogue.append(node("p","SCRIPTED INPUT","eyebrow"),node("p",frame.input,"utterance"),node("p","AGENT REPLY","eyebrow"),node("p",frame.reply,"reply"));
  const state=frame.clarification_pending ? "Clarification pending" : frame.confirmation_pending ? "Confirmation pending" : frame.completed ? "Completed" : "Unresolved";
  dialogue.append(node("span",state,"badge"));
  const ledger=node("article",null,"replay-card"); ledger.append(node("h3","Actual ledger after this turn"));
  if (!frame.after.length) ledger.append(node("p","No entries have been written.","ledger-empty"));
  frame.after.forEach(row=>{
    const entry=node("div",null,"ledger-row" + (row.payment_status==="voided" ? " voided" : ""));
    const name=node("div",row.item || "Entry"); name.append(node("small",`${row.type} · ${row.payment_status}`));
    entry.append(name,node("strong",money(row.amount,row.currency))); ledger.append(entry);
  });
  ledger.append(node("p",frame.wrong_amounts_active ? `${frame.wrong_amounts_active} wrong-amount entry active at this turn.` : "No wrong-amount entry active at this turn.",frame.wrong_amounts_active ? "badge danger" : "badge"));
  ledger.append(node("p",frame.exact_ledger ? "Ledger matches all expected fields." : "Ledger does not yet match all expected fields.","caveat"));
  $("replay").replaceChildren(dialogue,ledger);
  $("timing-note").textContent=`Local agent processing: ${frame.processing_ms.toFixed(3)} ms this turn; ${scenario.local_processing_ms.toFixed(3)} ms across the script. Excludes speech recognition, synthesis, network and human response time.`;
}
function setView(conversation) {
  $("asr-view").hidden=conversation;
  $("conversation-view").hidden=!conversation;
  $("asr-tab").setAttribute("aria-pressed",String(!conversation));
  $("conversation-tab").setAttribute("aria-pressed",String(conversation));
  $("reference-audio").pause();
}
async function boot() {
  try {
    const response=await fetch("data.json");
    if (!response.ok) throw new Error("Evidence export is missing. Run python -m bench.explorer to build it.");
    evidence=await response.json();
    $("overview").replaceChildren(stat(evidence.source.observed_clips,"unique cached clips"),stat(models().length,"speech systems · controls excluded"),stat(new Set(evidence.clips.map(c=>c.tier)).size,"speech groups"),stat(evidence.conversations.summary.scenarios,"scripted conversation scenarios"));
    $("tier").replaceChildren(...[...new Set(evidence.clips.map(c=>c.tier))].sort((a,b)=>a==="sautiledger-clips" ? -1 : b==="sautiledger-clips" ? 1 : a.localeCompare(b)).map(t=>option(t,tierNames[t]||t)));
    setModels(); setClips();
    const report=evidence.conversations, summary=report.summary;
    $("conversation-stats").replaceChildren(stat(`${summary.completed}/${summary.scenarios}`,"scripts completed"),stat(summary.median_turns_to_completion ?? "—","median turns · completed scripts only"),stat(summary.scenarios_with_wrong_amount_at_any_turn,"scripts with any wrong-amount write"),stat(summary.scenarios_with_wrong_final_amount,"scripts with a wrong final amount"));
    $("scenario").replaceChildren(...report.results.map(r=>option(r.id,r.name)));
    renderConversation();
    const descriptions=[
      "ASR scores are read directly from the cached metrics; no model was called or re-scored for this viewer.",
      evidence.source.redaction || "",
      "Summary WER is the arithmetic mean of cached per-clip WER. Broadcast clips have no transaction ground truth, so their financial metrics are shown as not applicable.",
      `Source: ${evidence.source.file}. SHA-256: ${evidence.source.sha256}`,
      `Frozen manifest SHA-256: ${evidence.source.manifest_sha256}`,
      `Source declares ${evidence.source.declared_clips} clips; cached rows contain ${evidence.source.observed_clips} unique clip IDs across tiers. This viewer derives counts from those rows and does not modify the source.`,
      ...report.limitations,
      `Conversation fixtures SHA-256: ${report.scenarios_sha256}`,
      `Agent implementation and packs SHA-256: ${report.implementation_sha256}`,
      `Replay generated: ${report.generated_at}`,
      "Local audio playback serves only manifest-listed corpus files on localhost. The static export and downloaded JSON do not include audio, participant usage logs or product ledgers.",
    ];
    $("methodology").replaceChildren(...descriptions.map(s=>node("p",s)));
    try {
      const audio=await fetch("audio-index");
      if (audio.ok) audioClips=new Set((await audio.json()).map(c=>`${c.tier}/${c.clip}`));
    } catch (_) { /* Static deployment intentionally contains no corpus audio. */ }
    renderComparison();
  } catch (error) { $("load-error").hidden=false; $("load-error").textContent=error.message; }
}
$("tier").addEventListener("change",setClips);
$("clip").addEventListener("change",renderComparison);
$("model").addEventListener("change",renderComparison);
$("controls").addEventListener("change",()=>{setModels();renderComparison();});
$("asr-tab").addEventListener("click",()=>setView(false));
$("conversation-tab").addEventListener("click",()=>setView(true));
$("scenario").addEventListener("change",()=>{turn=0;renderConversation();});
$("previous-turn").addEventListener("click",()=>{turn--;renderConversation();});
$("next-turn").addEventListener("click",()=>{turn++;renderConversation();});
boot();
