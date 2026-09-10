// Run with: node --test tests/ui_safety.test.cjs
// A small DOM double exercises the real UI script without a browser or ASR calls.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup() {
  class Element {
    constructor() {
      this.children = []; this.dataset = {}; this.checked = false;
      this.hidden = false; this.value = ''; this.style = {}; this.events = {};
      this.textContent = ''; this.tagName = 'DIV';
      const classes = new Set();
      this.classList = {
        add: x => classes.add(x), remove: x => classes.delete(x),
        toggle: (x, on) => on ? classes.add(x) : classes.delete(x),
      };
    }
    get childElementCount() { return this.children.length; }
    append(...children) { children.forEach(c => { c.parent = this; this.children.push(c); }); }
    appendChild(child) { this.append(child); }
    replaceChildren(...children) { this.children = []; this.append(...children); }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(c => c !== this); }
    setAttribute(key, value) { this[key] = value; }
    addEventListener(event, handler) { this.events[event] = handler; }
    scrollTo() {} focus() {}
  }
  const root = path.join(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'static/index.html'), 'utf8');
  const elements = new Map([...html.matchAll(/id="([^"]+)"/g)].map(m => [m[1], new Element()]));
  elements.get('scroll').dataset.view = 'book';
  const calls = [];
  let failUtterance = false;
  const state = {currency:'NGN',mode:'offline',entries:[],sales_total:0,egress_total:0,egress_log:[],retain_audio:false};
  const context = vm.createContext({
    document: {
      getElementById: id => elements.get(id), createElement: () => new Element(),
      createTextNode: text => ({textContent:text}), querySelectorAll: () => [], addEventListener() {},
    },
    window: { matchMedia: () => ({matches:true}) }, navigator: {},
    localStorage: { getItem: () => null, setItem() {} },
    FormData, Date, setTimeout, clearTimeout, setInterval() {},
    fetch: async (url, options) => {
      calls.push({url, options});
      if (url === '/utterance' && failUtterance) throw new Error('offline');
      return {ok:true, json: async () => state};
    },
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'static/app.js'), 'utf8'), context);
  return {elements,calls,run: code => vm.runInContext(code,context),fail: () => {failUtterance=true;}};
}

test('confirmation survives scrolling, incidental replies, and a failed request; next agent reply resolves it', async () => {
  const ui = setup();
  ui.run('updateSafetyReply("Logged rice, five hundred naira. Correct?", null)');
  ui.run('selectView("book"); showStatus("I dey hear you"); bubble("Privacy choice saved", "sauti"); clearStatus()');
  ui.fail();
  await ui.run('submit(new FormData(), "no")');
  assert.equal(ui.elements.get('reply-panel').hidden, false);
  assert.match(ui.elements.get('pending-reply').textContent, /Correct\?/);
  assert.equal(ui.elements.get('text').disabled, undefined);
  assert.equal(ui.elements.get('send').disabled, false);
  ui.run('updateSafetyReply("Noted. Ledger correct.", null)');
  assert.equal(ui.elements.get('reply-panel').hidden, true);
});

test('clarification without question punctuation remains visible as a reply', () => {
  const ui = setup();
  ui.run('updateSafetyReply("Tell me the amount, abeg.", {intent:"clarify"}); bubble("Tell me the amount, abeg.", "sauti"); selectView("book")');
  assert.equal(ui.elements.get('reply-panel').hidden, false);
  assert.equal(ui.elements.get('confirm-actions').hidden, true);
  assert.ok(ui.elements.get('chat').children.length > 1);
});

test('default and skipped onboarding never enable retention, even after checking then skipping', async () => {
  const ui = setup();
  assert.equal(ui.elements.get('retain').checked, false);
  assert.equal(ui.elements.get('retain-ob').checked, false);
  await ui.run('finishOnboard()');
  ui.elements.get('retain-ob').checked = true;
  await ui.run('finishOnboard(true)');
  assert.equal(ui.calls.filter(c => c.url === '/consent').length, 0);
  ui.run('showOnboard()');
  assert.equal(ui.elements.get('retain-ob').checked, false);
  ui.elements.get('retain-ob').checked = true;
  await ui.run('finishOnboard()');
  const calls = ui.calls.filter(c => c.url === '/consent');
  assert.equal(calls.length, 1);
  assert.equal(calls[0].options.body.get('retain_audio'), 'true');
});

test('byte counter stays numeric and USD cents display without a 100-fold inflation', () => {
  const ui = setup();
  ui.run('renderEgress(1536, [])');
  assert.equal(ui.elements.get('egress-total').textContent, '1.50 KB');
  assert.equal(ui.run('currencyCode="USD"; formatMoney(550)'), '$5.50');
});

test('structured readback distinguishes unknown from recorded money', () => {
  const ui = setup();
  ui.run('updateSafetyReply("How much?", {intent:"clarify"}, {status:"not_recorded",transaction:{item:"rice",amount:null,currency:"NGN"}})');
  assert.equal(ui.elements.get('review-amount').textContent, 'Amount to clarify');
  assert.match(ui.elements.get('review-status').textContent, /Not recorded/);
  ui.run('updateSafetyReply("Logged. Correct?", null, {status:"recorded_awaiting_confirmation",transaction:{item:"rice",quantity:3,unit:"cup",amount:550,currency:"USD"}})');
  assert.equal(ui.elements.get('review-amount').textContent, '$5.50');
  assert.equal(ui.elements.get('confirm-actions').hidden, false);
});

test('nonempty book updates count, caption and empty state together', () => {
  const ui = setup();
  ui.run('renderLedger([{id:1,type:"sale",item:"biscuits",amount:500,payment_status:"paid"},{id:2,type:"sale",item:"isu",amount:6000,payment_status:"paid"},{id:3,type:"sale",item:"eyin",amount:6000,payment_status:"paid"}],12500)');
  assert.equal(ui.elements.get('entry-count').textContent, 3);
  assert.equal(ui.elements.get('book-empty').hidden, true);
  assert.match(ui.elements.get('sales-caption').textContent, /3 sales/);
  assert.equal(ui.elements.get('entries').children.length, 3);
  assert.match(ui.elements.get('total').textContent, /12,500/);
});

// --- microphone: it must start on iOS and Android alike ---------------
// Field reports, 10-11 Sep: "mic not available" on phones whose microphone
// was fine. Two distinct causes, both covered here.

function micSetup({supported, error}) {
  const fs2 = require('node:fs'), vm2 = require('node:vm'), path2 = require('node:path');
  const root = path2.join(__dirname, '..');
  const html = fs2.readFileSync(path2.join(root, 'static/index.html'), 'utf8');
  class El {
    constructor(){ this.dataset={}; this.children=[]; this.style={}; this.events={};
      this.textContent=''; this.hidden=false; this.value='';
      const c=new Set(); this.classList={add:x=>c.add(x),remove:x=>c.delete(x),toggle:(x,o)=>o?c.add(x):c.delete(x)}; }
    get childElementCount(){ return this.children.length; }
    append(...k){ k.forEach(x=>{x.parent=this; this.children.push(x);}); }
    appendChild(c){ this.append(c); } replaceChildren(...k){ this.children=[]; this.append(...k); }
    remove(){} setAttribute(k,v){ this[k]=v; } addEventListener(e,h){ this.events[e]=h; }
    scrollTo(){} focus(){}
  }
  const elements = new Map([...html.matchAll(/id="([^"]+)"/g)].map(m => [m[1], new El()]));
  elements.get('scroll').dataset.view = 'book';
  const made = [];
  class FakeRecorder {
    constructor(stream, opts){ made.push(opts && opts.mimeType); this.mimeType=(opts&&opts.mimeType)||'audio/webm'; this.state='inactive'; }
    static isTypeSupported(t){ return supported.includes(t); }
    start(){ this.state='recording'; } stop(){ this.state='inactive'; if(this.onstop) this.onstop(); }
  }
  const ctx = vm2.createContext({
    document:{ getElementById:id=>elements.get(id), createElement:()=>new El(),
      createTextNode:t=>({textContent:t}), querySelectorAll:()=>[], addEventListener(){} },
    window:{ matchMedia:()=>({matches:true}) },
    navigator:{ mediaDevices:{ getUserMedia: async () => {
      if (error) { const e=new Error('denied'); e.name=error; throw e; }
      return { getTracks: () => [{stop(){}}] };
    } } },
    localStorage:{ getItem:()=>null, setItem(){} },
    MediaRecorder: FakeRecorder, Blob: class { constructor(p,o){ this.size=5000; this.type=o&&o.type; } },
    FormData, Date, setTimeout, clearTimeout, setInterval(){},
    fetch: async () => ({ok:true, json: async () => ({currency:'NGN',mode:'cloud',entries:[],sales_total:0,egress_total:0,egress_log:[],retain_audio:false})}),
  });
  vm2.runInContext(fs2.readFileSync(path2.join(root,'static/app.js'),'utf8'), ctx);
  const deepText = (n) => (n.textContent || '') + (n.children || []).map(deepText).join(' ');
  return { elements, made, run: c => vm2.runInContext(c, ctx),
           chat: () => elements.get('chat').children.map(deepText).join(' | ') };
}

test('records on Safari, which supports mp4 and not webm', async () => {
  const ui = micSetup({supported:['audio/mp4']});
  await ui.run('startRecording()');
  assert.equal(ui.made[0], 'audio/mp4', 'must not force webm on a browser that cannot record it');
});

test('records on Chrome, which supports webm', async () => {
  const ui = micSetup({supported:['audio/webm;codecs=opus','audio/webm']});
  await ui.run('startRecording()');
  assert.equal(ui.made[0], 'audio/webm;codecs=opus');
});

test('a blocked permission says so, instead of blaming the microphone', async () => {
  const ui = micSetup({supported:['audio/webm'], error:'NotAllowedError'});
  await ui.run('startRecording()');
  assert.match(ui.chat(), /permission is blocked/i);
});

test('a missing microphone is reported as missing', async () => {
  const ui = micSetup({supported:['audio/webm'], error:'NotFoundError'});
  await ui.run('startRecording()');
  assert.match(ui.chat(), /no see any microphone/i);
});

test('releasing during the first permission prompt invites a retry rather than failing silently', async () => {
  const ui = micSetup({supported:['audio/webm']});
  // the finger lifts to tap "Allow", cancelling the hold before the grant lands
  const started = ui.run('startRecording()');
  ui.run('stopRecording()');
  await started;
  assert.match(ui.chat(), /Hold the green button again/i);
});
