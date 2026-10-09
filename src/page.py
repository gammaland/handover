"""Homepage: first say what it is, then offer the fetch box (D50).

Order: one-line value + a two-device conversation example (an idea in Muse on the phone -> Claude Code on the laptop, the core scenario of D46) -> fetch box -> "a handoff, not a workspace" -> the two modes -> For agents.
When opened with a code (handover.tools/<code>), the server adds prefill to .home and the fetch box moves to the top.
Keep it restrained, clean and quiet.
"""
from style import page
import icons
from tools import handoff as ho

_CSS = """
  .home { display: flex; flex-direction: column; }
  .hero { margin-bottom: 8px; }
  .eyebrow {
    margin: 0 0 14px; font: 600 13px/1.4 var(--mono); letter-spacing: .04em;
    color: var(--ink-tertiary); text-transform: uppercase;
  }
  .hero h1 { font-size: clamp(30px, 5.4vw, 44px); line-height: 1.08; max-width: 15em; margin-bottom: 14px; }

  /* The two-device conversation example: static, because being readable matters more than moving */
  .demo {
    display: grid; grid-template-columns: 1fr auto 1fr; align-items: stretch; gap: 14px;
    margin-top: 32px;
  }
  .device {
    margin: 0; min-width: 0; background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: 12px; padding: 14px 16px 16px; box-shadow: var(--shadow-md);
  }
  .device figcaption {
    display: flex; align-items: center; gap: 6px; margin-bottom: 12px;
    font: 600 12.5px/1.3 var(--mono); color: var(--ink-tertiary); letter-spacing: .02em;
  }
  .client {
    display: inline-flex; align-items: center; gap: 7px; margin-left: auto;
    font: 600 13.5px/1 var(--sans); color: var(--ink-primary); letter-spacing: 0;
  }
  .client img { width: 20px; height: 20px; border-radius: 22%; box-shadow: 0 0 0 1px var(--border-subtle); }
  /* Each side looks like its own client: phone chat vs terminal, so you can tell they are two different agents without reading */
  .msg { margin: 0; font-size: 14.5px; line-height: 1.45; max-width: none; padding: 8px 12px; }
  .msg + .msg { margin-top: 8px; }
  .msg.you {
    margin-left: 14%; background: rgba(0, 115, 245, .12); color: var(--ink-primary);
    border-radius: 16px 16px 4px 16px;
  }
  .msg.agent {
    margin-right: 8%; background: var(--bg-surface-inset); color: var(--ink-primary);
    border-radius: 16px 16px 16px 4px;
  }
  .term {
    background: var(--bg-surface-inset); border: 1px solid var(--border-subtle); border-radius: 8px;
    padding: 12px 14px; font: 13.5px/1.6 var(--mono); color: var(--ink-primary);
  }
  .term p { margin: 0; max-width: none; color: inherit; }
  .term p + p { margin-top: 6px; }
  .term .prompt { color: var(--ink-secondary); }
  .term .line { padding-left: 1.4em; text-indent: -1.4em; }   /* wrapped lines align after the ⏺, as in a terminal */
  .term .dot { display: inline-block; width: 1.4em; text-indent: 0; color: var(--ink-primary); }
  .term .dot.ok { color: var(--signal-green); }
  .term .sub { padding-left: 1.4em; color: var(--ink-tertiary); margin-top: 0; }
  /* The only thing carried from one side to the other: the same orange style on both ends, so the eye follows the arrow */
  .code8 {
    font: 700 .92em/1 var(--mono); letter-spacing: .03em; white-space: nowrap;
    color: var(--signal-orange); background: var(--signal-orange-dim);
    border: 1px solid var(--signal-orange-border); border-radius: 6px; padding: 2px 6px;
  }
  .hop {
    display: flex; flex-direction: column; align-items: center; align-self: center; gap: 4px;
    font: 600 12px/1.2 var(--mono); color: var(--signal-orange); text-align: center; white-space: nowrap;
  }
  .hop svg { width: 22px; height: 22px; }

  /* Fetch box */
  .fetch {
    margin-top: 40px; background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: 14px; padding: 22px 24px 18px; box-shadow: var(--shadow-xs);
  }
  .fetch h2 { margin: 0 0 4px; font-size: 20px; }
  .fetch .sub { margin: 0; font-size: 15px; }
  .home.prefill .fetch { order: -1; margin: 0 0 40px; border-color: var(--signal-orange-border); box-shadow: var(--shadow-md); }
  .entry { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 18px; }
  .codefield { position: relative; display: flex; align-items: center; gap: 6px; }
  .prefix {
    font: 500 clamp(15px, 3.6vw, 22px)/1 var(--mono); color: var(--ink-secondary);
    white-space: nowrap;
  }
  .cells { display: flex; align-items: center; gap: clamp(3px, 1vw, 6px); }
  .cell-group { display: flex; align-items: center; gap: clamp(3px, 1vw, 6px); }
  .cell {
    width: clamp(28px, 8.2vw, 48px); height: clamp(42px, 12vw, 60px);
    display: flex; align-items: center; justify-content: center;
    font: 600 clamp(20px, 6.2vw, 32px)/1 var(--mono); color: var(--ink-primary);
    border: 1.5px solid var(--border-default); border-radius: 8px;
    background: var(--bg-surface);
    transition: all .12s ease;
  }
  .cell.filled {
    border-color: var(--ink-primary);
  }
  .sep { display: none; }   /* the cells read as the end of the link: no gap mid-code */
  .codefield:focus-within .cell.active {
    border-color: var(--signal-orange);
    box-shadow: 0 0 0 3px var(--signal-orange-dim);
  }
  .codefield:focus-within .cell.active:empty::after {
    content: ""; width: 2px; height: 46%;
    background: var(--signal-orange);
    animation: blink 1.1s steps(2) infinite;
  }
  @keyframes blink { 50% { opacity: 0; } }
  @media (prefers-reduced-motion: reduce) { .cell.active:empty::after { animation: none; } }

  #code {
    position: absolute; inset: 0; width: 100%; height: 100%;
    opacity: 0; font-size: 16px; border: 0; padding: 0; cursor: text;
  }
  #go {
    min-height: clamp(42px, 12vw, 60px); padding: 0 26px;
    font: 600 15.5px var(--sans);
    border: 0; border-radius: 8px;
    background: var(--ink-primary); color: var(--bg-surface);
    cursor: pointer; transition: opacity .15s ease;
  }
  #go:not(:disabled):hover { opacity: .88; }
  #go:disabled {
    background: var(--bg-wash); color: var(--ink-tertiary);
    cursor: default; border: 1px solid var(--border-subtle);
  }

  .status {
    margin: 14px 0 0; min-height: 1.5em;
    font-size: 14.5px; color: var(--ink-secondary);
  }

  .caution {
    margin: 0 0 10px; padding: 8px 12px; border-left: 3px solid var(--signal-amber);
    background: var(--signal-amber-dim); color: var(--ink-primary); font-size: 14px; line-height: 1.5;
  }

  /* Result Area */
  #out:empty { display: none; }
  #out { margin-top: 28px; }
  .res {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: 10px; padding: 20px 22px;
    box-shadow: var(--shadow-sm);
  }
  .res strong { font-weight: 700; color: var(--ink-primary); }
  .res ul { margin: 8px 0 0; padding-left: 20px; color: var(--ink-secondary); font-size: 14.5px; }
  .meta { font-size: 13.5px; color: var(--ink-secondary); margin: 0 0 12px; }
  pre {
    margin: 0; padding: 14px 16px; background: var(--bg-surface-inset);
    border: 1px solid var(--border-subtle); border-radius: 6px;
    white-space: pre-wrap; word-break: break-word;
    font: 14px/1.6 var(--mono); max-height: 52vh; overflow: auto;
    color: var(--ink-primary);
  }
  .copyrow { margin-top: 14px; display: flex; flex-wrap: wrap; align-items: center; gap: 14px; }
  #copy {
    display: inline-flex; align-items: center; gap: 6px;
    font: 600 14px var(--sans); padding: 8px 16px; border-radius: 7px;
    border: 1px solid var(--border-strong); background: var(--bg-surface);
    color: var(--ink-primary); cursor: pointer; transition: all .15s ease;
  }
  #copy:hover {
    background: var(--bg-wash);
  }
  #copy svg { flex-shrink: 0; }
  .note { font-size: 13.5px; color: var(--signal-amber); }

  /* The difference: a handoff, not a workspace */
  .diff { margin-top: 64px; }
  .diff h2 { font-size: 26px; line-height: 1.2; margin: 0 0 8px; }
  .diff .desc { font-size: 17px; line-height: 1.5; margin: 0 0 24px; max-width: 34em; }
  .points { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 0; padding: 0; list-style: none; }
  .points li {
    max-width: none; background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: 10px; padding: 18px 20px; box-shadow: var(--shadow-xs);
  }
  .points h3 { font-size: 16.5px; margin: 0 0 6px; }
  .points p { margin: 0; font-size: 14.5px; line-height: 1.5; }
  .points .tag { margin-left: 6px; }
  .elsewhere { margin: 18px 0 0; font-size: 14.5px; color: var(--ink-tertiary); }

  /* Product & Modes Cards */
  .product {
    margin-top: 64px; padding-top: 36px; border-top: 1px solid var(--border-subtle);
  }
  .product h2 { font-size: 26px; line-height: 1.2; margin: 0 0 18px; }
  .product h2 a { text-decoration: none; }
  .product .desc { font-size: 17px; line-height: 1.5; color: var(--ink-secondary); margin: 0 0 24px; max-width: 32em; }
  .modes { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .mode-card {
    display: flex; flex-direction: column; justify-content: space-between;
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: 10px; padding: 20px 22px; text-decoration: none;
    box-shadow: var(--shadow-xs); transition: border-color .15s ease;
  }
  .mode-card:hover {
    border-color: var(--border-strong);
  }
  .mode-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
  .mode-card-title { display: flex; align-items: center; gap: 8px; }
  .mode-card-title .icon { color: var(--ink-tertiary); transition: color .15s ease; }
  .mode-card:hover .icon-oneshot { color: var(--signal-amber); }
  .mode-card:hover .icon-channel { color: var(--signal-green); }
  .mode-card h3 { font-size: 16.5px; margin: 0; color: var(--ink-primary); }
  .mode-card p { font-size: 14.5px; color: var(--ink-secondary); margin: 0; line-height: 1.5; }

  .links {
    margin: 22px 0 0; display: flex; flex-wrap: wrap; gap: 12px 24px; font-size: 14.5px;
  }
  .links a {
    display: inline-flex; align-items: center; gap: 4px;
    color: var(--ink-secondary); text-decoration: underline; text-underline-offset: 3px;
  }
  .links a .icon-arrow { transition: transform .15s ease; }
  .links a:hover { color: var(--signal-orange); }
  .links a:hover .icon-arrow { transform: translateX(3px); color: var(--signal-orange); }

  /* For agents */
  .ref { margin-top: 56px; }
  .ref h2 {
    display: flex; align-items: center; gap: 6px;
    font-size: 14.5px; font-weight: 700; color: var(--ink-tertiary); margin: 0 0 12px;
    text-transform: uppercase; letter-spacing: .04em;
  }
  .ref h2 .icon-terminal { color: var(--signal-orange); }
  dl.agents { display: grid; grid-template-columns: max-content 1fr; gap: 8px 24px; margin: 0; font-size: 14.5px; }
  dl.agents dt { color: var(--ink-tertiary); }
  dl.agents dd { margin: 0; min-width: 0; overflow-wrap: anywhere; color: var(--ink-secondary); }

  @media (max-width: 720px) {
    .demo { grid-template-columns: 1fr; gap: 10px; }
    .hop { flex-direction: row; justify-content: center; }
    .hop svg { transform: rotate(90deg); }
    .points { grid-template-columns: 1fr; }
  }
  @media (max-width: 640px) {
    .fetch { padding: 18px 16px 14px; }
    .codefield { flex-wrap: wrap; row-gap: 8px; }
    .prefix { flex-basis: 100%; }
    #go { flex: 1 0 100%; }
    .modes { grid-template-columns: 1fr; }
    dl.agents { grid-template-columns: 1fr; gap: 4px; }
    dl.agents dd { margin-bottom: 12px; }
  }
"""

_BODY = f"""
<div class="home">
<section class="hero">
  <p class="eyebrow">No account · No install · Any agent</p>
  <h1>Hand work from one AI agent to another.</h1>
  <p class="lede">An idea comes to you in the agent on your phone; your context lives with the agent on your laptop.
  Say one sentence, carry 8 letters across, and the other agent picks it up. Read once, then gone.</p>
  <div class="demo" aria-label="Example: an idea from Muse on a phone to Claude Code on a laptop">
    <figure class="device">
      <figcaption>{icons.ICON_PHONE} Phone<span class="client"><img src="/img/client-muse.png" alt="" width="20" height="20">Muse</span></figcaption>
      <p class="msg you">New idea: turn my weekly notes into a one-page digest. Hand this over with handover.tools.</p>
      <p class="msg agent">Done. On your laptop, say <span class="code8">handover.tools/kvmtrhxp</span></p>
    </figure>
    <div class="hop" aria-hidden="true">{icons.ICON_ARROW_RIGHT}<span>8 letters</span></div>
    <figure class="device">
      <figcaption>{icons.ICON_DEVICE} Laptop<span class="client"><img src="/img/client-claude.png" alt="" width="20" height="20">Claude Code</span></figcaption>
      <div class="term">
        <p class="prompt">&gt; <span class="code8">handover.tools/kvmtrhxp</span></p>
        <p class="line"><span class="dot ok">⏺</span>Fetch(handover.tools/kvmtrhxp)</p>
        <p class="sub">⎿ Received “Weekly digest”</p>
        <p class="line"><span class="dot">⏺</span>Got your idea. Looking at your notes folder to plan it.</p>
      </div>
    </figure>
  </div>
</section>

<section class="fetch" id="fetch">
  <h2>Got a link?</h2>
  <p class="sub">Paste it, or type its last 8 letters. No agent needed.</p>
  <div class="entry">
    <div class="codefield">
      <input id="code" inputmode="latin" autocomplete="off" autocapitalize="characters"
             spellcheck="false" aria-label="handover link or code"
             aria-describedby="status">
      <span class="prefix" aria-hidden="true">handover.tools/</span>
      <div class="cells" aria-hidden="true">
        <div class="cell-group">
          <span class="cell"></span><span class="cell"></span><span class="cell"></span><span class="cell"></span>
        </div>
        <span class="sep"></span>
        <div class="cell-group">
          <span class="cell"></span><span class="cell"></span><span class="cell"></span><span class="cell"></span>
        </div>
      </div>
    </div>
    <button id="go" disabled>Fetch</button>
  </div>
  <p class="status" id="status" aria-live="polite"></p>
  <div id="out"></div>
</section>

<section class="diff">
  <h2>A handoff, not a workspace.</h2>
  <p class="desc">Plenty of tools want to be where your agents’ work lives, with accounts, projects and history.
  handover.tools only moves it from one place to the next, then gets out of the way.</p>
  <ul class="points">
    <li><h3>Nothing to sign up for</h3>
      <p>No account, no key. Any agent that can open a web page or use MCP can fetch a link;
      a browser works too.</p></li>
    <li><h3>Gone after one read</h3>
      <p>A one-shot handoff is fetched once. Unfetched, it becomes unreadable after {ho._DEFAULT_TTL_MIN} minutes.
      Nothing piles up for anyone to leak later.</p></li>
    <li><h3>Across vendors, devices and people</h3>
      <p>Claude to ChatGPT to Cursor, phone to laptop, your agent to a teammate’s.
      The only thing that travels between them is 8 letters.</p></li>
    <li><h3>Encrypted when it matters <span class="tag enc">channel</span></h3>
      <p>Two machines pair once and go back and forth. The server only holds ciphertext,
      and you approve every message.</p></li>
  </ul>
  <p class="elsewhere">Need a shared space your team keeps coming back to? Use a workspace tool.
  handover.tools is for the hop between places.</p>
</section>

<section class="product">
  <h2><a href="/guide">Two ways to hand over</a></h2>
  <div class="modes">
    <a href="/guide" class="mode-card">
      <div class="mode-card-head">
        <div class="mode-card-title">
          {icons.ICON_ONESHOT}
          <h3>One-shot</h3>
        </div>
        <span class="tag plain">not encrypted</span>
      </div>
      <p>One piece of text, fetched once, then gone. Don’t put passwords or keys in it;
      use a channel for those.</p>
    </a>
    <a href="/guide#channel" class="mode-card">
      <div class="mode-card-head">
        <div class="mode-card-title">
          {icons.ICON_CHANNEL}
          <h3>Channel</h3>
        </div>
        <span class="tag enc">end-to-end encrypted</span>
      </div>
      <p>Two agents on two machines, many rounds. You approve every message.</p>
    </a>
  </div>
  <p class="links">
    <a href="/guide">Prompts to copy {icons.ICON_ARROW_RIGHT}</a>
    <a href="/security">What each mode protects {icons.ICON_ARROW_RIGHT}</a>
  </p>
</section>

<section class="ref">
  <h2>{icons.ICON_TERMINAL} For agents</h2>
  <dl class="agents">
    <dt>Start here</dt><dd><a href="/llms.txt">handover.tools/llms.txt</a></dd>
    <dt>MCP</dt><dd><code>https://handover.tools/mcp</code></dd>
    <dt>Reference</dt><dd><a href="/api/discover">/api/discover</a></dd>
  </dl>
</section>
</div>
"""

_SCRIPT = r"""<script>
// Crockford base32 minus I L O U. Server normalises too; we mirror it so the
// cells show exactly what will be sent.
var OK = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
var input = document.getElementById("code");
var go = document.getElementById("go");
var out = document.getElementById("out");
var statusEl = document.getElementById("status");  // not "status": that is window.status, a string
var cells = document.querySelectorAll(".cell");

function clean(s) {
  // NFKC folds full-width characters from a CJK keyboard (１Ｃ３Ｈ) to ASCII first;
  // without it they were silently dropped and the cells stayed empty.
  s = (s || "");
  if (s.normalize) s = s.normalize("NFKC");
  // A pasted link (handover.tools/kvmtrhxp, or …?code=…) → just the code
  if (s.indexOf("code=") >= 0) s = s.split("code=").pop().split("&")[0];
  else if (s.indexOf("/") >= 0) s = s.replace(/\/+$/, "").split("/").pop();
  s = s.toUpperCase().replace(/[^A-Z0-9]/g, "");
  s = s.replace(/I/g, "1").replace(/L/g, "1").replace(/O/g, "0").replace(/U/g, "V");
  return s.split("").filter(function (c) { return OK.indexOf(c) >= 0; }).join("").slice(0, 8);
}
function render() {
  var v = clean(input.value);
  input.value = v.toLowerCase();
  for (var i = 0; i < cells.length; i++) {
    cells[i].textContent = (v[i] || "").toLowerCase();
    cells[i].className = "cell" + (v[i] ? " filled" : "") + (i === Math.min(v.length, 7) ? " active" : "");
  }
  // Only speaks when there is something to say: a link filled the code in.
  statusEl.textContent = (window.PREFILL && v === window.PREFILL)
    ? "Filled in from your link. Nothing is fetched until you press Fetch." : "";
  go.disabled = v.length !== 8;
}
input.addEventListener("input", render);
input.addEventListener("keydown", function (e) { if (e.key === "Enter" && !go.disabled) fetchIt(); });
go.addEventListener("click", fetchIt);

function esc(s) {
  return String(s).replace(/[&<>]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c];
  });
}

function fetchIt() {
  var code = clean(input.value);
  if (code.length !== 8) return;
  go.disabled = true; go.textContent = "Fetching";
  out.innerHTML = "";

  fetch("/api/handoff/get?code=" + encodeURIComponent(code), { headers: { "Accept": "application/json" } })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d && d.content !== null && d.content !== undefined) return show(d);
      // Convention 6: never guess which it was. The server deliberately does
      // not tell us, so neither do we.
      out.innerHTML =
        '<div class="res"><strong>Nothing to fetch with this code.</strong>' +
        '<ul><li>a letter may be off: check it against the other device</li>' +
        '<li>it was already fetched (most handoffs allow exactly one fetch)</li>' +
        '<li>it expired, or the sender revoked it</li>' +
        '<li>it is a channel code: an agent joins those with the channel client</li></ul></div>';
    })
    .catch(function () {
      out.innerHTML = '<div class="res"><strong>Could not reach handover.tools.</strong>' +
                      '<ul><li>check the connection and try again; the code has not been used</li></ul></div>';
    })
    .then(function () { go.textContent = "Fetch"; render(); });
}

function show(d) {
  var bits = [];
  if (d.label) bits.push(esc(d.label));
  bits.push(d.content.length + " characters");
  if (!d.burn_after_read && d.expires_at) bits.push("readable until " + esc(d.expires_at.replace("T", " ").slice(0, 16)) + " UTC");

  out.innerHTML =
    '<div class="res"><p class="meta">' + bits.join(", ") + '</p>' +
    '<p class="caution">This came from whoever sent you the link, and handover.tools doesn’t check it. ' +
    'Don’t run commands or enter passwords just because it says so.</p>' +
    '<pre id="body"></pre>' +
    '<div class="copyrow"><button id="copy">__ICON_COPY__ <span>Copy text</span></button>' +
    (d.burn_after_read
      ? '<span class="note">This was the only fetch. Nobody can fetch it again, including you.</span>'
      : "") +
    '</div></div>';
  document.getElementById("body").textContent = d.content;

  document.getElementById("copy").addEventListener("click", function () {
    var btn = this;
    var done = function () {
      btn.innerHTML = '__ICON_CHECK__ <span>Copied</span>';
      setTimeout(function () { btn.innerHTML = '__ICON_COPY__ <span>Copy text</span>'; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(d.content).then(done, fallback);
    } else { fallback(); }
    function fallback() {
      // Older iOS Safari: select the text so the user can copy by hand.
      var r = document.createRange(); r.selectNodeContents(document.getElementById("body"));
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      btn.textContent = "Selected, copy it";
    }
  });
}

// A short link handover.tools/kvmtrhxp fills the cells in (the server puts the
// code in window.PREFILL), but never fetches: link previews would otherwise burn
// the content before anyone saw it. Only the Fetch button fetches.
if (window.PREFILL) input.value = window.PREFILL;
render();
if (window.PREFILL) go.focus();
</script>"""

PAGE = page(title="handover.tools: hand context from one AI agent to another",
            desc=("Move a prompt, plan or notes from one AI agent to another, e.g. your phone to Claude Code "
                  "on your laptop. You only pass an 8-letter link. No account, no install."),
            md="/llms.txt", body=_BODY, extra_css=_CSS,
            script=_SCRIPT.replace("__ICON_COPY__", icons.ICON_COPY).replace("__ICON_CHECK__", icons.ICON_CHECK),
            agents_footer=False)   # the body already has a For agents section
