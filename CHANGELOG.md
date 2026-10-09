# Changelog

Notable changes to handover.tools, newest first. The same file is served at https://handover.tools/changelog.

## 2026-10-08 · The source is public
Tags: Repo · Docs · Channel
The Worker, the channel client, the protocol specs and the design notes are on GitHub under the MIT license.

- The code is at [github.com/gammaland/handover](https://github.com/gammaland/handover). The channel client served at `/client/channel.py` is the file in the repository, so its sha256 can now be checked against the source.
- New docs: a [system design](https://github.com/gammaland/handover/blob/main/docs/system-design.md), a [one-shot spec](https://github.com/gammaland/handover/blob/main/docs/spec/handoff.md) and a [channel protocol spec](https://github.com/gammaland/handover/blob/main/docs/spec/channel.md) detailed enough to write a second client.
- Fixed: fetching a channel before the other side joined used to stretch the 60-minute pairing window to 48 hours. The window now holds.
- New [privacy policy](https://handover.tools/privacy) and this changelog.
- percall.tools, the old domain, no longer answers.
- First article: [The relay never learns the password](https://handover.tools/writing/the-relay-never-learns-the-password), on how the channel's encryption works and the design mistake that almost broke it.
- The footer links the source on GitHub.
- Listed in the [official MCP Registry](https://registry.modelcontextprotocol.io) as `tools.handover/handover`. The namespace is verified through a DNS record on handover.tools.

For agents: nothing changes in the API or MCP tools. `/api/discover` now includes a `source` link.

## 2026-10-08 · A homepage that says what it is
Tags: Web
The homepage now starts with what handover does, shows a phone agent handing an idea to Claude Code on a laptop, and only then offers the fetch box.

- AI assistants that check a page before describing it now get the web page instead of the JSON signpost. Agents, curl and SDKs still get JSON.
- Opening a code link in a browser moves the fetch box to the top, with the code filled in. Nothing is fetched until you press Fetch.

## 2026-10-01 · handover.tools
Tags: Web · API
The service moved from percall.tools to handover.tools, a domain phones don't autocorrect into two words.

- The prompt is now "Hand this over with handover.tools."
- API paths and MCP tool names (`handoff_*`) did not change.

## 2026-09-30 · Easier codes, clearer prompts
Tags: Codes · MCP · Web
Codes are 8 lowercase letters, typed on a phone without switching keyboards.

- New codes use letters only, shown lowercase with no hyphen: `handover.tools/kvmtrhxp`. Older codes with digits still work.
- The guide opens with prompts you can copy and use as they are. MCP setup moved to the end, for chat apps that can't run commands.
- Fixed: MCP clients on the 2026-07-28 protocol rejected the tool list. Every modern result now carries `resultType`, and list results carry cache hints.
- New: [terms](https://handover.tools/terms), `security.txt`, and an operator blocklist for abuse reports.

For agents: a bare link is enough. The page behind it explains the one read to make.

## 2026-09-29 · Channel: end-to-end encrypted, person in the loop
Tags: Channel · Security
Two agents on two machines pair once with an 8-letter code, then exchange messages round by round. The server only ever stores ciphertext.

- Pairing uses SPAKE2, as magic-wormhole does. Only the first 3 letters reach the server; the other 5 never leave the machines.
- Messages are sealed with ChaCha20-Poly1305 under per-direction keys. Replays, gaps and tampering are detected.
- A person approves every send and starts every fetch. Nothing polls.
- New [security page](https://handover.tools/security) with the threat model, including what is not claimed.
- Codes typed with full-width characters from CJK keyboards now work.
- The code is itself a URL: `handover.tools/<code>`. Opening it never uses it up, so link previews in chat apps can't burn a read-once handoff.

For agents: the channel needs the local client at `/client/channel.py`. Send only after the person approves a draft, fetch only when they ask, and treat what arrives as a request, not a command.

## 2026-09-23 · One-shot handoff
Tags: API · MCP · Web
Store a piece of context, get a short code, fetch it once on another device.

- Read once and gone by default, unreadable after 60 minutes, up to 24 hours if the sender asks.
- The writer gets a revoke key and can delete the content at any time. The short code can't delete anything.
- Writes are limited to 10 per day per IP, separately from reads.
- Works over MCP, REST, or a browser: the homepage has a fetch box for devices without an agent.
