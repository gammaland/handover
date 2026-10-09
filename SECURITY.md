# Security policy

## Reporting a vulnerability

Email **security@handover.tools**. Please don't open a public issue for a vulnerability.

Include what you found, how to reproduce it, and what an attacker could do with it. You'll get an acknowledgement within a few days. This is a one-person project with no bug bounty, but every report is read and credited in the fix if you want.

## Scope

In scope:

- The Worker in `src/` as deployed at https://handover.tools
- The channel client `client/channel.py` and the protocol in [docs/spec/channel.md](docs/spec/channel.md)
- Any way a channel's plaintext, password or key could reach the server or a third party
- Any way to read, alter or destroy someone else's handoff without its code or revoke key

Known and documented, so not vulnerabilities:

- One-shot handoffs are **not encrypted**; the operator can read them ([docs/spec/handoff.md §7](docs/spec/handoff.md#7-security-properties))
- The client is downloaded from the same server it talks to; its sha256 is published for checking
- Limits are per IP, so many IPs multiply them ([docs/system-design.md §11](docs/system-design.md#11-known-gaps))
- Anything else listed under "what is not claimed" in [docs/spec/channel.md §10](docs/spec/channel.md#10-security-properties)

Please don't run load tests or automated scanners against the production service: it runs on a free plan with a daily cap shared by everyone.

## Threat model

The public threat model is at https://handover.tools/security.
