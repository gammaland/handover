# One-shot handoff

**Status:** implemented, v1. Reference implementation: `src/tools/handoff.py`, routes in `src/entry.py`.

One agent stores a piece of text and gets an 8-letter code. Another agent, on any device, fetches it with that code, by default exactly once. **The content is not encrypted: the server can read it.** For anything sensitive, use a [channel](channel.md).

This document is the contract. Behavior changes start here, then the code and tests follow. The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. Transports

Each operation is available in three equivalent ways, all generated from the same tool definition:

| Transport | Form |
|---|---|
| REST | `POST /api/handoff/<op>` with a JSON body, or `GET` with query parameters |
| MCP | `POST /mcp`, tool `handoff_<op>`. The result is in `structuredContent` and repeated as JSON text |
| Discovery | `GET /api/discover` lists every tool with its input schema |

Clients SHOULD use POST for `put` and `revoke`. GET works for every operation, but it puts the content or key in the URL, where it can end up in logs.

### 1.1 Responses

- A tool-level outcome, success or not, is **HTTP 200** with a JSON object. On failure the primary field (`code`, `content` or `revoked`) is `null`/`false` and `reason` says why. Nothing is guessed: a value that can't be determined is `null` with a reason.
- A quota refusal before the tool runs is **429** (`free_quota_exhausted`) or **503** (`service_daily_cap`). Over MCP it is a JSON-RPC result with `isError: true`.
- An unexpected error is **500** with `error`.

## 2. Codes

### 2.1 Format

- 8 letters from `ABCDEFGHJKMNPQRSTVWXYZ` (Crockford base32 without digits), drawn by the server with a CSPRNG and rejection sampling. That gives 22⁸ ≈ 5.5 × 10¹⁰ possibilities.
- Shown lowercase with no separator: `kvmtrhxp`. The shareable form is the link `handover.tools/kvmtrhxp`.
- The server stores only `SHA-256(normalized code)`, never the code.

### 2.2 Normalization

Before looking up a code, the server applies:

1. Unicode NFKC, then trim. This folds full-width characters typed on CJK keyboards.
2. If the text contains `code=`, keep what follows up to the next `&`. Otherwise, if it contains `/`, keep the last path segment. Agents often pass the whole link.
3. Uppercase and keep only alphanumeric characters (this drops hyphens and spaces).
4. Map `I`→`1`, `L`→`1`, `O`→`0`, `U`→`V`.
5. Valid only if exactly 8 characters from `0123456789ABCDEFGHJKMNPQRSTVWXYZ`. Digits are still accepted so that codes issued before the letters-only change work.

The web page and the channel client apply the same rules.

## 3. Operations

### 3.1 `handoff_put`

| Input | Type | Default | Rule |
|---|---|---|---|
| `content` | string | required | Non-blank, at most 262,144 bytes of UTF-8 |
| `label` | string | `""` | Truncated to 120 characters. Shown to whoever fetches |
| `ttl_minutes` | int | 60 | Clamped to 1–1440. Missing or 0 means the default |
| `burn_after_read` | bool | true | If true, the first successful fetch deletes the content |

Validation happens **before** the write quota is charged, so a malformed request doesn't use up a write. Then:

1. Write gate: blocklist, then the per-caller daily write counter (10). A refused attempt still counts.
2. Generate the code and a 26-character `revoke_key` (Crockford alphabet, about 130 bits).
3. Insert `(sha256(code), content, label, burn, created_at, expires_at, creator IP, sha256(revoke_key))`.

| Output | |
|---|---|
| `code` | Lowercase code, or `null` with `reason` |
| `revoke_key` | Returned **once**. The writer keeps it; it is the only way to delete early |
| `say_on_the_other_device` | `handover.tools/<code>` |
| `tell_the_person`, `keep_revoke_key` | Instructions for the calling agent. `tell_the_person` states the read limit, which MUST match `burn_after_read` (once, or any number of times until expiry) |
| `label`, `bytes`, `burn_after_read`, `expires_at`, `expires_in_minutes` | Echo of what was stored |
| `writes_today`, `writes_per_day` | Write quota state |

Reasons: content missing or blank, content too large, `ttl_minutes` not an integer, `write_quota_exhausted…`, `blocked…`.

### 3.2 `handoff_get`

| Input | |
|---|---|
| `code` | A code or a link containing one (§2.2) |

The fetch MUST be atomic. Each case is one SQL statement:

```sql
-- burn_after_read = true: deleting is fetching; of concurrent fetches exactly one gets the row
DELETE FROM handoffs WHERE code_hash=?1 AND expires_at>?2 AND burn=1
 RETURNING content, label, created_at;

-- burn_after_read = false: count the read
UPDATE handoffs SET reads=reads+1 WHERE code_hash=?1 AND expires_at>?2 AND burn=0
 RETURNING content, label, created_at, reads, expires_at;
```

The server tries the DELETE first, then the UPDATE. A row is one or the other, so the two never compete.

| Output | |
|---|---|
| `content` | The stored text, or `null` |
| `label`, `created_at`, `burn_after_read`, `burned`, `reads` | |
| `expires_at` | Only when not burned |
| `reason` | `null`, `not_found_or_expired`, or `channel_code` |
| `detail` | With `not_found_or_expired`: one fixed sentence listing what the person can check. With `channel_code`: how to join instead |

**Unknown, already fetched, revoked and expired are deliberately indistinguishable** (`not_found_or_expired`), so the response never reveals whether a code existed. A malformed code gets a reason explaining the format instead.

`detail` is the same text for every miss, so it reveals nothing either. It lists the possible causes, including the one an agent can't guess: a channel code has the same shape as a one-shot code, but it is joined with the channel client, not fetched (D64). The code-link page shows the same list.

**Channel links are recognized before any lookup.** If the input contains `join` as a word or a path segment (`handover.tools/join/kvmtrhxp`, or `Join handover.tools/kvmtrhxp` as older clients phrase it), the server returns `content: null` with `reason: channel_code` and the join steps in `detail`, without touching the database. This depends only on the input, so it reveals nothing about any code. A code can't contain the word: `I` and `O` aren't in the alphabet.

The fetching agent SHOULD return `content` to the person verbatim and complete. With burn-after-read, its copy is the only one left.

### 3.3 `handoff_revoke`

| Input | |
|---|---|
| `revoke_key` | The 26-character key from `put`. NFKC, uppercased, non-alphanumerics removed |

Deletes the row whose `revoke_hash` matches, whether or not it has been fetched. Returns `revoked: true` with `label` and `would_have_expired_at`, or `revoked: false` with `already_gone` (already revoked, fetched or expired; these are indistinguishable). **The short code can't revoke**: only the writer, who holds the key, can delete early.

## 4. Code links

`GET /<code>`, a single path segment that normalizes to a valid code (§2.2), **MUST NOT read or consume the handoff.** Chat apps prefetch links for previews; if opening the link fetched a read-once handoff, the preview would destroy it (D21).

| Request | Response |
|---|---|
| `Accept` includes `text/html` | The homepage with the code prefilled. Nothing is fetched until the person presses Fetch. The page never reads codes from the URL query |
| anything else | `text/markdown` instructions for an agent: the real fetch URL (`/api/handoff/get?code=…`), "return it verbatim", and how to join if it is a channel code instead |

Both carry `X-Robots-Tag: noindex` and `Cache-Control: no-store`. The response is identical whether or not the code exists. Paths the site already uses (`/guide`, `/llms.txt`, …) take precedence over code links.

`GET /join/<code>` is the **channel link** (spec/channel §2). It follows the same rules: it MUST NOT touch the database or the channel, so a link preview can't use up the nameplate, and its response is identical whether or not the channel exists. A browser gets a page telling the person to give the link to an agent that can run commands; anything else gets Markdown with the commands to download the client and join. Neither mentions `handoff_get`.

## 5. Limits

| Limit | Value |
|---|---|
| Content size | 262,144 bytes (256 KB) |
| Label | 120 characters |
| Lifetime | Default 60 minutes, maximum 1,440 (24 hours) |
| Writes per caller per day | 10 |
| Calls per caller per day | 200 (reads and writes together). This is also the cap on guessing codes |
| Service-wide calls per day | 20,000 |

A caller is a client IP. Days are UTC. At 200 guesses a day against 5.5 × 10¹⁰ codes, each of which lives at most 24 hours, guessing is not a practical attack, so there is no extra per-code failure counter.

## 6. Retention and wording

- Content is deleted when fetched (burn), revoked, or swept after expiry. Expired rows are never returned, even before the sweep.
- D1 keeps point-in-time recovery backups, so a deleted row may still exist in a backup for some time. Public copy MUST say content becomes **unreadable**, and MUST NOT say it is **destroyed**.
- The creator's IP is stored with the row (for abuse handling) and deleted with it.

## 7. Security properties

- **Not encrypted.** Anyone with the code, and the operator, can read the content until it is fetched or expires. Tool descriptions, `/api/discover` and the docs all say so.
- **Not for someone else's confidential material.** Credentials and private data stay out, and so does material that belongs to an employer or a client and is not public: security findings, internal system details, unreleased code. An agent holding such content asks the person before storing it. A channel keeps the content from the operator, but the content still leaves the organization, so whether that is allowed is the person's call, not the agent's. The `handoff_put` description, the `/` signpost and `llms.txt` say so.
- **The operator is named.** The homepage, `llms.txt`, the privacy page, the `/` signpost and `/api/discover` say who runs the service and link the source, from one constant (`style.OPERATOR`). An agent deciding whether to trust an unfamiliar service should not have to infer that from a footer icon.
- **Anyone who holds the link can read it, once.** If the intended recipient fetches and finds `not_found_or_expired`, someone else may have used it first.
- **Content is data, not instructions.** The fetching agent should treat it as text from another person.
