"""Layered quotas (docs/system-design.md §7). The gates, outermost first:

    1. global daily cap        - keeps the service inside the Cloudflare D1 free write allowance
    2. per caller per day      - stops a single abuser
    3. per-caller daily writes - **an order of magnitude tighter than 2**. A write leaves someone else's content here;
          a read doesn't. So writes get their own gate, 10/day by default (D20)

Everything lives in one counters table; UPSERT...RETURNING increments atomically, with no race.

Why not COUNT(*): D1 bills by rows read, and COUNT scans every matching row,
so a single caller accumulates N^2/2 row reads. 200 calls/day x 100 people = 2M rows a day, 40% of the free allowance.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

_ready = False
COUNTER_DAYS = 7      # quota counters (keyed by caller IP) are deleted after this many days


@dataclass
class Limits:
    caller_daily: int
    write_daily: int
    global_daily: int


def limits_of(env) -> Limits:
    def g(k, d):
        v = getattr(env, k, None)
        return int(v) if v else d
    return Limits(g("FREE_CALLS_PER_DAY", 200), g("WRITE_CALLS_PER_DAY", 10),
                  g("GLOBAL_DAILY_CALLS", 20000))


def day_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def ensure_schema(env):
    global _ready
    if _ready:
        return
    await env.DB.prepare(
        "CREATE TABLE IF NOT EXISTS counters ("
        " scope TEXT NOT NULL, window TEXT NOT NULL,"
        " n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (scope, window))"
    ).run()
    # Operator blocklist (D44): blocks writes only. Edited with scripts/block.sh, no redeploy needed
    await env.DB.prepare(
        "CREATE TABLE IF NOT EXISTS blocks ("
        " prefix TEXT PRIMARY KEY, reason TEXT, created_at INTEGER NOT NULL)"
    ).run()
    _ready = True


async def blocked(env, caller: str) -> bool:
    """A prefix equal to the whole IP blocks exactly; one ending in '.' or ':' blocks that range ('203.0.113.', '2001:db8:').
    No LIKE: % and _ are wildcards, and one wrong character could block a huge range."""
    row = await env.DB.prepare(
        "SELECT 1 AS hit FROM blocks WHERE prefix = ?1 OR (substr(prefix, -1) IN ('.', ':')"
        " AND substr(?1, 1, length(prefix)) = prefix) LIMIT 1"
    ).bind(caller).first()
    return bool(row)


async def _bump(env, scope: str, window: str) -> int:
    row = await env.DB.prepare(
        "INSERT INTO counters (scope, window, n) VALUES (?1, ?2, 1)"
        " ON CONFLICT(scope, window) DO UPDATE SET n = n + 1 RETURNING n"
    ).bind(scope, window).first()
    return int(row.n) if row else 1


async def _peek(env, scope: str, window: str) -> int:
    row = await env.DB.prepare(
        "SELECT n FROM counters WHERE scope=?1 AND window=?2"
    ).bind(scope, window).first()
    return int(row.n) if row else 0


async def admit(env, caller: str) -> dict:
    """Entry gate. Increment first, then check: atomic, so concurrent requests can't all slip through.
    The global gate comes before the caller gate: the account's safety outranks one user's experience."""
    L = limits_of(env)
    day = day_key()
    g = await _bump(env, "global", day)
    c = await _bump(env, f"caller:{caller}", day)

    if g > L.global_daily:
        return {"ok": False, "status": 503, "body": {
            "error": "service_daily_cap", "resets": "UTC 00:00",
            "hint": ("Service-wide daily cap reached. This is a protective circuit breaker "
                     "for the service as a whole, not a limit on you specifically.")}}
    if c > L.caller_daily:
        return {"ok": False, "status": 429, "body": {
            "error": "free_quota_exhausted", "free_per_day": L.caller_daily,
            "used": c, "resets": "UTC 00:00"}}
    return {"ok": True, "caller_n": c, "global_n": g}


async def admit_keyed(env, caller: str) -> dict:
    """Entry gate for key-holding calls (channel send/fetch/close).

    Only the global gate applies, and the caller counter is **not incremented**: a legitimate key holder shouldn't be stopped at 200 a day.
    But if this caller has already used up its 200 (usually misses from fake keys, see charge_miss),
    it is still blocked: otherwise guessing keys would be unlimited free D1 load.
    """
    L = limits_of(env)
    day = day_key()
    g = await _bump(env, "global", day)
    if g > L.global_daily:
        return {"ok": False, "status": 503, "body": {
            "error": "service_daily_cap", "resets": "UTC 00:00",
            "hint": ("Service-wide daily cap reached. This is a protective circuit breaker "
                     "for the service as a whole, not a limit on you specifically.")}}
    c = await _peek(env, f"caller:{caller}", day)
    if c >= L.caller_daily:
        return {"ok": False, "status": 429, "body": {
            "error": "free_quota_exhausted", "free_per_day": L.caller_daily,
            "used": c, "resets": "UTC 00:00"}}
    return {"ok": True, "global_n": g}


async def charge_miss(env, caller: str):
    """A key-holding call matched no channel: charge it to the caller's daily quota."""
    await _bump(env, f"caller:{caller}", day_key())


async def take_scope(env, scope: str, limit: int) -> dict:
    """A daily counter for any scope (e.g. operations on one channel). Increment first, then check."""
    n = await _bump(env, scope, day_key())
    return {"ok": n <= limit, "used": n, "limit": limit}


async def take_write(env, caller: str) -> dict:
    """Write gate. Anything that leaves content in our database must pass it first.
    Increment first, then check, and failed attempts count too; otherwise the limit means nothing."""
    L = limits_of(env)
    if await blocked(env, caller):
        return {"ok": False, "used": 0, "limit": L.write_daily,
                "reason": ("blocked: writes from this network are blocked after abuse reports. "
                           "If this is a mistake, write to abuse@handover.tools.")}
    n = await _bump(env, f"write:{caller}", day_key())
    if n > L.write_daily:
        return {"ok": False, "used": n, "limit": L.write_daily,
                "reason": (f"write_quota_exhausted: {L.write_daily} writes per day per caller. "
                           "Reads are not affected. Resets at UTC 00:00.")}
    return {"ok": True, "used": n, "limit": L.write_daily}


async def usage_snapshot(env, caller: str) -> dict:
    L = limits_of(env)
    day = day_key()
    c = await _peek(env, f"caller:{caller}", day)
    w = await _peek(env, f"write:{caller}", day)
    # No site-wide usage or site-wide cap here (D40): that would tell an attacker "N more calls and the whole site stops", with live progress.
    # No caller IP either: an agent may paste the whole response into a handoff.
    return {
        "you": {"used_today": c, "free_per_day": L.caller_daily,
                "remaining": max(0, L.caller_daily - c),
                "writes_today": w, "writes_per_day": L.write_daily,
                "writes_remaining": max(0, L.write_daily - w)},
        "resets": "UTC 00:00",
    }


async def sweep(env):
    """Lazy cleanup: day buckets live COUNTER_DAYS days."""
    import time
    cut_day = datetime.fromtimestamp(time.time() - COUNTER_DAYS * 86400, timezone.utc).strftime("%Y-%m-%d")
    await env.DB.prepare("DELETE FROM counters WHERE window < ?1").bind(cut_day).run()
