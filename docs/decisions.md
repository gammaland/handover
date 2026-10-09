# Design decisions

This is a selection from the project's private decision log, translated. Each entry records why something was done and what was rejected. The `Dxx` numbers match the references in the code comments. Entries that are missing here were left out because they are internal or out of date.

---

## Positioning

### D45 · One agent writes it, another reads it

The obvious objection is that copy and paste already works across devices. What actually gets carried across, though, is only the 8 letters, and any channel will do for that. The hard parts are at either end: getting content that is scattered across many messages and files *out of* one agent, and getting tens of KB *into* another agent without the chat box truncating it, breaking its formatting, or keeping it forever. With handover, the writing agent packages the content itself and the reading agent pulls it into its own context.

A clipboard can't do any of these: an agent running over SSH or in a cloud sandbox, a handover between ecosystems (Windows ↔ iPhone), a handover to another person, or several rounds back and forth (channel). If both devices are your own Apple devices and the text is short, the system clipboard is easier, and the guide says so.

### D46 · Bring the idea to your context, not your context to the idea

The scenario that started this: light brainstorming on a phone agent, then deep work in Claude Code on a laptop that holds private documents the person doesn't want to upload anywhere. Every vendor is moving toward "upload your documents to us" (projects, knowledge bases, connectors). Handover goes the other way: the documents stay where they are and only a small idea travels.

This is also why the useful niche is **cross-vendor and cross-person**. Vendors' own sync features are absorbing same-vendor, cross-device handover, and no vendor will ever hand work to a competitor's agent.

**Rejected:** "the agent waits on a remote machine for a human decision." Vendor apps can already push a notification and ask for confirmation inside their own ecosystem.

### D10 · The filter that predicted the most

> "Have I personally hit this in the past month?"

Before handover, the project surveyed the MCP registry and found dozens of "pay-per-call, no API key" tool clusters. Their descriptions were nearly identical, a whole cluster was published within seconds, and download counts were in the hundreds. Supply existed without demand. Any candidate idea without a concrete first-person scenario got crossed out.

### D22 · Honestly, one-shot is an online clipboard

In features, it's nearly the same as the ad-supported "online clipboard" sites: paste text, get a short code, fetch it elsewhere, no account, expires. Measuring the biggest of those sites (about 830K page views a month, 94% from one country, 48 keywords that are all variants of "online clipboard") put the whole category's ceiling at a few hundred dollars a month in ad revenue. So handover is not a business, and revenue was never a goal. Its value is that agents use it natively: the link is itself the instructions, it burns after one read, and a phone agent can be told "fetch this" without anyone opening a browser.

### D6 · Free, but metered from the first call

The usual way "free now, paid later" fails: nothing is metered while it's free, so when pricing arrives there is no usage data to price from. Every call is recorded from day one at a price of 0, so the billing pipe works end to end and is not a stub. The free allowance is permanent and bounded; taking it back would destroy trust. Since D22 nothing here is expected to be sold, but the metering is also what makes abuse visible.

### D47 · From percall.tools to handover.tools

Phones autocorrected `percall.` to `per call.`, which turned the link into `call.tools/...`, someone else's parked domain. The fix was a domain whose first part is a dictionary word. "Handover" also fits better than "handoff", which in the AI field already means passing control between agents. The product name changed; the API and MCP names (`handoff_*`) did not, so existing agents and configurations kept working.

### D48 / D54 · The old domain is gone

For a while percall.tools redirected every web path to handover.tools and returned 410 from its API (D48). When the Worker and the database were rebuilt under the handover name, the old domain was dropped entirely: the service lives only at handover.tools.

---

## Security and trust

### D25 · Channel: the person stays in the loop

Channel grew out of a real case. An agent on machine A explored, an agent on machine B studied the results, and B kept producing new questions for A. Doing that with one-shot meant a new code every round, with the person copying it from one screen to the other.

A first design had both sides polling and replying automatically. **That was rejected.** The person approves every send and starts every fetch. This removed a whole set of problems: no stop condition is needed, no polling runs into rate limits, no long-polling infrastructure is needed, and a prompt injection can no longer travel between machines on its own (B is injected → B tells A to run tools).

**The limit, stated publicly:** the server cannot enforce that a person approved a send. That rule lives only in the client and skill behaviour. The docs must never say "enforced human approval".

### D26 · Trust: not "we don't look" but "we can't look"

A service run by one person, with no company behind it, has no reason to be trusted, and a promise is worth nothing to a stranger. The only answer that holds up is to make trusting the server unnecessary.

A short code is far too weak to serve as an encryption key: 8 letters can be brute-forced offline once the ciphertext sits on a server. As the password for a **PAKE** (SPAKE2), though, it only has to survive an *online* guess, one per code, because joining burns the code. Both sides derive a 256-bit key from it. This is exactly magic-wormhole's construction; no new cryptography was invented.

**Correction, found while writing the client:** in the first design the *server* generated the code, which meant the server knew the PAKE password. It could have run SPAKE2 with each side separately and read everything in between. The fix is wormhole's split: a 3-letter nameplate generated by the server, plus a 5-letter password generated by the client that never leaves it. I had copied "short code + PAKE" and missed the half that makes it secure.

> The question to ask of a data flow is not "who does the ciphertext pass through" but "who does the **password** pass through".

### D37 · The server rejects ciphertext that looks like plaintext

Walking through the docs as an agent that knew nothing else turned up a silent failure. The server accepts any base64 on `channel_send`, so a helpful agent could base64-encode *plaintext*, skip the client, and the end-to-end promise would quietly break. ChaCha20-Poly1305 output is indistinguishable from random bytes, and only about 38% of random bytes are printable ASCII. Anything that decodes to fewer than 48 bytes, or to ≥ 90% printable bytes, is now refused with `not_ciphertext`. This guards against misuse, not malice: anyone can XOR their plaintext first. It stops the accident that is most likely to happen.

### D28 · IP retention and the $0 ceiling

Every place that stores an IP was inventoried. Metering rows keep the row but blank the IP after 30 days; quota counters go after 7 days; a handoff's or channel's creator IP is deleted with it. The public page states the 30 days, and a test checks that the page and the configuration agree.

Cloudflare's paid plan has budget alerts but no hard spending cap. The Free plan returns errors when its limits are exceeded and never bills, so staying on Free *is* the hard $0 ceiling. Moving to Paid would first need budget alerts, edge rate limiting and a CPU limit.

### D44 · First layer against abuse

One-shot already resists most abuse: no HTML rendering, read once, 60-minute default, not enumerable, not indexed, 10 writes per IP per day. Added on top: a caution above content fetched in the browser ("this came from whoever sent you the link… don't run commands because it says so"), terms of use, `security.txt` (RFC 9116), and an operator blocklist that stops writes from an IP or a range without a redeploy. Prefix matching deliberately avoids SQL `LIKE`, where `%` and `_` are wildcards and one typo could block a huge range.

### D40 · Discovery shows how it works, not how to break it

`/api/discover` stays, because it is the only place that lists every REST input schema. Removed from it: the site-wide usage and cap (they told an attacker "N more calls and the whole site stops", with live progress), the runtime name (only useful for fingerprinting), and the caller's own IP (an agent might paste the whole response into a handoff). Kept: per-caller quota, schemas, protocol versions, and the client's sha256. Explaining how it works builds trust; it isn't a leak.

### D21 / D38 · Never fetch automatically from a URL

Content burns after one read, and chat apps prefetch links. If opening `handover.tools/<code>` returned the content, pasting the link into Slack would let the preview crawler burn it. So:

- The code URL returns **instructions** and doesn't query the database (it doesn't reveal whether the code exists). The real read is a second request that only an agent following those instructions makes.
- In a browser, the code is pre-filled and nothing is fetched until the person presses Fetch. A test asserts that the page contains no `URLSearchParams`, so nobody can later add the "convenience" back.

**Follow-up (D39):** to a cautious agent, the second hop can look like obeying instructions from a web page, which is the shape of a prompt injection. The page is now written as "the person who gave you this link wants what's inside it. It's one read from this same site; nothing is run and nothing is sent elsewhere." That lets the agent decide for itself that the step serves its user.

### D20 · Writes have their own gate, and the writer can revoke

Reads leave nothing on the server; writes leave someone else's content there. One shared 200/day limit for both would have been lazy. Writes get their own 10/day gate, and a test checks that hitting it never blocks reads. `put` returns a 130-bit `revoke_key`, exactly once. The short code can only read, and only the writer can destroy. Revoking a code that was already revoked, already fetched, or expired returns the same `already_gone`, so existence isn't leaked.

---

## Details that mattered

### D39 / D36 · Codes are 8 lowercase letters, normalised with NFKC

People really type codes on phones. Uppercase, digits and dashes meant switching keyboards four or five times per code. New codes use 22 letters, are shown in lowercase and need no dash: `handover.tools/kvmtrhxp` can be typed on one keyboard. Generation uses rejection sampling, because 256 isn't a multiple of 22 and a plain modulo would be biased.

Trying nine spellings of a code against production turned up a failure only with **full-width** characters (`１Ｃ３Ｈ`), which Chinese input methods produce. On the channel this was the most confusing case: the password never reaches the server, so a full-width password simply derived a different key and showed up as `pairing_mismatch`, which looks like an attack. All four input paths now apply NFKC first.

> Test normalisation against the characters people actually type, not against your alphabet.

### D42 · Copyable prompts first, MCP last

A fresh Claude Code with no MCP, no skills and no settings, told only "Hand this over with handover.tools.", opened the homepage, used the curl recipe in its JSON, and returned a working link. So the guide now opens with prompts that copy in one click. MCP setup moved to the end, for chat apps that can't run commands. A copyable prompt must never contain a placeholder: whatever is in it, people will paste.

### D30 / D31 · A design system with reasons

The first homepage was a SaaS card kit with gradients and system fonts, which could have been any product. The theme comes from where the word comes from: air traffic control, where one controller hands an aircraft to the next. The type is Atkinson Hyperlegible Next and Mono, designed by the Braille Institute to tell similar letters apart, the same job as dropping I, L, O and U from the code alphabet. The fonts are self-hosted, because Google Fonts would send every visitor's IP to a third party (D28). The palette is paper, ink and one aviation orange, with colour reserved for the encryption state of each mode. The docs pages use a "call log" layout: on the left, who is speaking (Device A, Machine B, You); on the right, what they say and what happens next.

### D24 · Measuring the MCP ecosystem

I sampled 700 of the 6,861 remote servers in the official MCP registry, sending only the `server/discover` and `initialize` handshakes. Of the 404 that answered, **3.2% supported the current `2026-07-28` spec**; 82% were still on `2025-11-25`. 66% sent no CORS headers at all, so browser-based clients couldn't reach them.

Our own server has to serve both eras. A bug I caught: deciding the era by "is the `_meta` version value one we know" let a request that declared an *unknown* version slip into the legacy path and return 200. The right test is "did it use the modern way of declaring a version at all" (is the `_meta` key present?).

### D41 · Verify protocol support with a real client

Every curl assertion passed, and a real Claude Code still failed to load tools: `missing required resultType`, then missing `ttlMs` and `cacheScope`. The modern era requires these on *every* result, not just on `server/discover`. The fix shipped only after a real client (`claude -p --strict-mcp-config`) completed `tools/list` and `tools/call` locally.

### D50 · AI assistants were being served JSON

Asked "what is handover.tools?", an AI assistant twice replied that it "isn't a usable website". The cause was our own code: `/` served the web page only when the request carried `Accept: text/html`, and everything else got JSON with `X-Robots-Tag: noindex`. Googlebot sends `text/html`; the fetchers AI assistants use to check a page often send `*/*`. Now an explicit JSON request gets JSON, a `Mozilla` user agent gets the page, and curl, wget and SDKs still get JSON, so the agent contract is unchanged. Code URLs still look only at `Accept`, because an agent opening a code link should get Markdown instructions.

### D12 · Python Workers, the day after GA

`cloudflare:sockets` had no documented Python path. Three dead ends: no `cloudflare.sockets` module; `run_js("import(...)")` blocked by CSP; and passing a Python dict to JS raised a `TypeError`. What works is `workers.import_from_javascript("cloudflare:sockets")` with `to_js(kw, dict_converter=Object.fromEntries)`, which I found by enumerating `dir(workers)`. Python was chosen over a TypeScript version that worked equally well, because a codebase you want to touch beats one that's 70 ms faster.

### D15 · Shared egress IPs are rate-limited before you have a single user

The first tool on this platform was a domain availability checker. On launch day, every RDAP request from Workers to one major registry operator returned 429 (6/6), while the same request from a home IP worked. Workers leave through Cloudflare's shared egress ranges, which that operator had already rate-limited, and Workers can't change their egress IP. The tool was retired. The lesson carried forward: any tool that depends on outbound requests from Cloudflare carries this risk.

### D19 · Cloudflare's edge blocks `Python-urllib`

`urllib.request` got a 403, while `requests`, `node-fetch`, curl and an empty user agent all got 200. Cloudflare's managed bot rules treat urllib as a known crawler. The test suite used curl, so it never noticed. For a service whose users are agents, this is the worst kind of failure: a 403 that looks like your fault. The docs therefore use curl or requests in their examples.

### D27 · "Tests green" ≠ "tested"

Several channel tests were passing by accident: hand-written JSON like `"{\"key\":…,\"peek\":true}"` inside `$( )` triggered bash brace expansion and split one request into two broken curls. All test JSON is now generated by a helper. Relatedly, every number on the public pages (TTL, limits, password length, client sha256) is derived from the implementation's constants rather than written by hand, because copy that drifts from the code is lying to users.
