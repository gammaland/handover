"""Metering: every call is recorded from the very first one, at a price of 0 for now (D6).
The billing pipe works end to end and is not a stub: changing a price only changes Tool.cost_micro, not the architecture.
"""
import json, uuid
from datetime import datetime, timezone

_ready = False


async def ensure_schema(env):
    global _ready
    if _ready:
        return
    await env.DB.prepare(
        "CREATE TABLE IF NOT EXISTS calls ("
        " id TEXT PRIMARY KEY, ts TEXT NOT NULL, day TEXT NOT NULL,"
        " tool TEXT NOT NULL, caller TEXT NOT NULL, transport TEXT NOT NULL,"
        " status TEXT NOT NULL, cost_micro INTEGER NOT NULL DEFAULT 0,"
        " duration_ms INTEGER NOT NULL DEFAULT 0, meta TEXT NOT NULL DEFAULT '')"
    ).run()
    await env.DB.prepare(
        "CREATE INDEX IF NOT EXISTS idx_calls_ts ON calls(ts DESC)").run()
    _ready = True


def caller_of(request) -> str:
    """Caller identity: the IP for now. Once there are tokens, switch to the token id; nothing else changes."""
    h = request.headers
    return (h.get("CF-Connecting-IP")
            or (h.get("x-forwarded-for") or "").split(",")[0].strip()
            or "local")


def retention_days(env) -> int:
    v = getattr(env, "IP_RETENTION_DAYS", None)
    return int(v) if v else 30


async def sweep(env):
    """IP retention: call records older than N days have caller blanked, **the rows stay** (tool, time, status and duration
    remain available for statistics). Not hashed for now: within the retention period we want to see real usage per IP (decided 2026-09-29).

    Every other place that stores an IP cleans up on its own: counters after 7 days (guard.sweep); creator in handoffs / channels
    is deleted with the row when it expires or is fetched.
    """
    from datetime import timedelta
    cut = (datetime.now(timezone.utc) - timedelta(days=retention_days(env))).isoformat()
    await env.DB.prepare(
        "UPDATE calls SET caller='' WHERE ts < ?1 AND caller != ''").bind(cut).run()


async def record(env, *, tool, caller, transport, status, cost_micro, duration_ms, meta=None):
    now = datetime.now(timezone.utc).isoformat()
    await env.DB.prepare(
        "INSERT INTO calls (id, ts, day, tool, caller, transport, status,"
        " cost_micro, duration_ms, meta) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10)"
    ).bind(str(uuid.uuid4()), now, now[:10], tool, caller, transport, status,
           int(cost_micro), int(duration_ms),
           (json.dumps(meta, ensure_ascii=False)[:2000] if meta else "")).run()
