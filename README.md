# handover.tools

[![test](https://github.com/gammaland/handover/actions/workflows/test.yml/badge.svg)](https://github.com/gammaland/handover/actions/workflows/test.yml)

**One agent writes it, another agent reads it. You only carry an 8-letter link between them.**

[handover.tools](https://handover.tools) moves a piece of work from one AI agent to another: across devices, across vendors, or to another person. Brainstorm with the agent on your phone, then say "hand this over with handover.tools". Paste the link it gives you (`handover.tools/kvmtrhxp`) into Claude Code on your laptop, and that agent picks the work up where your documents already are.

> Bring the idea to your context, not your context to the idea.

There is no account and nothing to install. Any agent that can open a web page can use it.

## Two modes

| | One-shot | Channel |
|---|---|---|
| Use it for | Handing over one piece of text | Several rounds between two agents |
| Encryption | **None.** The server can read it, so don't put secrets in it | **End-to-end** (SPAKE2 + ChaCha20-Poly1305). The server only ever stores ciphertext |
| Lifetime | Gone after the first read, or after 60 minutes (24 h max) | Until either side closes it |
| What the agent needs | Can open a URL, or has MCP | Can run a Python script (`uv run`) |
| Who decides | The person carries the link | The person approves every send and starts every fetch |

### One-shot

```bash
curl -X POST https://handover.tools/api/handoff/put \
     -H 'Content-Type: application/json' \
     -d '{"content":"...","label":"notes"}'          # → {"code":"kvmtrhxp", "revoke_key":"...", ...}
curl "https://handover.tools/api/handoff/get?code=kvmtrhxp"
```

Opening `handover.tools/<code>` doesn't use up the code. That URL returns instructions, and the actual read is a second request. Link previews in Slack or iMessage therefore don't burn the content before the recipient sees it.

### Channel

```bash
curl -so ~/.handoff/channel.py --create-dirs https://handover.tools/client/channel.py
uv run ~/.handoff/channel.py open --name study --brief "..."   # machine A: prints a code
uv run ~/.handoff/channel.py join kvmtrhxp --name study        # machine B
uv run ~/.handoff/channel.py send --name study --kind question --file q.md
uv run ~/.handoff/channel.py fetch --name study
```

The 8 letters are a 3-letter **nameplate**, which the server sees and uses to find the channel, plus a 5-letter **password** that is generated on machine A and never uploaded. The password goes into SPAKE2, the same construction magic-wormhole uses. The server never learns the password, so it cannot impersonate either side. `/client/channel.py` is served from [`client/channel.py`](client/channel.py), and its sha256 is published at [`/api/discover`](https://handover.tools/api/discover), so you can check that the client you downloaded matches this repository.

The threat model, including what we *don't* claim, is at [handover.tools/security](https://handover.tools/security).

## For agents

- MCP endpoint: `https://handover.tools/mcp`. It serves both the `2026-07-28` (modern) and `2025-11-25` and earlier (legacy) protocol eras.
- Plain text instructions: [`/llms.txt`](https://handover.tools/llms.txt), [`/guide.md`](https://handover.tools/guide.md), [`/security.md`](https://handover.tools/security.md)
- Full REST schema: [`/api/discover`](https://handover.tools/api/discover)

## How it's built

- **Cloudflare Python Workers + D1.** One Worker, no other infrastructure. The routes, the MCP `tools/list` and `/api/discover` are all derived from a single tool registry (`src/registry.py`), so they can't drift apart.
- **Limits are layered:** 10 writes and 200 calls per caller per day, plus a global daily cap. The site runs on the Workers Free plan, which makes $0 the hard spending ceiling.
- **Fonts are self-hosted** and embedded in the Worker, so no visitor IP goes to a third party. Caller IPs are erased after 30 days.

```
src/
  entry.py        routing, MCP (dual-era), content negotiation
  registry.py     @tool decorator — one source for REST, MCP and discover
  tools/handoff.py, tools/channel.py   the two tools
  guard.py        quotas and the operator blocklist
  meter.py        per-call metering
  page.py, docs.py, style.py   the website and docs pages
client/channel.py   the local E2EE client, run on the user's machine
tests/              end-to-end, channel and quota test suites
scripts/            dev, deploy, repository checks, operator tools
```

## Documentation

| Document | What it covers |
|---|---|
| [docs/system-design.md](docs/system-design.md) | Architecture: components, request pipeline, data model, flows, trust boundaries, limits and capacity, failure modes, known gaps |
| [docs/spec/handoff.md](docs/spec/handoff.md) | The one-shot contract: operations, code format and normalization, atomicity, code links, limits |
| [docs/spec/channel.md](docs/spec/channel.md) | The channel protocol: pairing, SPAKE2 parameters, key schedule, wire format, receiver rules, server API, lifecycle. Detailed enough to write a second client |
| [docs/decisions.md](docs/decisions.md) | Why it is built this way: what was tried, what was rejected, and what broke |
| [CHANGELOG.md](CHANGELOG.md) | What changed, newest first. Also at [handover.tools/changelog](https://handover.tools/changelog) |

The specs are the contract. A behavior change starts in the spec, then the code and tests follow.

## Run it locally

Requires Node ≥ 22 and Python 3.12.

```bash
npm install
scripts/dev.sh      # generates src/client_src.py + src/fonts_src.py, then runs wrangler dev on :8787
tests/e2e.sh        # end-to-end tests against the local server
tests/channel.sh    # two isolated clients: pairing, tampering, replay
tests/quota.sh      # quota gates (local only: edits counters directly)
scripts/check.sh    # repository rules: English only, every Dxx reference resolves
```

CI runs the check and the three suites on every push.

## Deploy your own

1. `npx wrangler d1 create <name>`, then put the name and id into `wrangler.toml`.
2. Change the `routes` pattern to your domain.
3. `CLOUDFLARE_API_TOKEN=… scripts/deploy.sh`

Tables are created on the first request. `scripts/block.sh` has the operator tools for abuse reports: block writes from an IP or a range, look up or delete a handoff by its link.

## Contributing and security

Issues and pull requests are welcome. [AGENTS.md](AGENTS.md) has the working rules, for people and coding agents alike: a change in behavior starts with the spec in `docs/spec/`, then the code and the tests. Report vulnerabilities privately: see [SECURITY.md](SECURITY.md).

## License

MIT. Fonts: Atkinson Hyperlegible, SIL OFL 1.1 (see `assets/fonts/LICENSE.txt`).
