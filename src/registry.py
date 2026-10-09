"""Tool registry: the single source of truth.

REST routes, MCP tools/list and /api/discover are all derived from here, so they cannot drift apart.
Adding a tool = adding one function decorated with @tool.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class Tool:
    name: str
    title: str
    summary: str
    path: str
    input_schema: dict
    run: Callable[..., Awaitable[Any]]
    cost_micro: int = 0            # all 0 for now: the billing pipe works, the price is 0
    examples: list[str] = field(default_factory=list)
    # Tools called with a 130-bit key (channel send/fetch/close). They skip the per-caller 200/day gate:
    # that gate stops code guessing, and someone holding the key is not guessing. A tool charges key-guess misses itself
    keyed: bool = False


_TOOLS: dict[str, Tool] = {}


def tool(*, name, title, summary, path, input_schema, cost_micro=0, examples=None,
         keyed=False):
    def deco(fn):
        if name in _TOOLS:
            raise ValueError(f"duplicate tool: {name}")
        _TOOLS[name] = Tool(name=name, title=title, summary=summary, path=path,
                            input_schema=input_schema, run=fn,
                            cost_micro=cost_micro, examples=examples or [],
                            keyed=keyed)
        return fn
    return deco


def get_tool(name: str) -> Tool | None:
    return _TOOLS.get(name)


def all_tools() -> list[Tool]:
    return list(_TOOLS.values())
