"""Tolerant JSON extraction from LLM output.

Models wrap JSON in prose or ```json fences. `extract_json` finds the first
balanced {...} object and parses it, raising ValueError if none is valid.
"""

from __future__ import annotations

import json
from typing import Any


def extract_json(text: str) -> Any:
    """Return the first valid JSON object embedded in `text`."""
    if not text:
        raise ValueError("empty LLM output, no JSON")

    # Fast path: the whole string is JSON.
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Scan for the first balanced {...} block.
    start = stripped.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(stripped)):
            ch = stripped[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = stripped[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break  # move to next '{'
        start = stripped.find("{", start + 1)

    raise ValueError("no valid JSON object found in LLM output")
