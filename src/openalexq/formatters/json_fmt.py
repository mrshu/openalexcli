"""JSON output formatting."""

from __future__ import annotations

import json
import sys
from typing import Any


def format_json(
    data: dict[str, Any] | list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
    pretty: bool | None = None,
) -> str:
    """
    Format data as JSON.

    Args:
        data: The data to format (single item or list)
        meta: Optional metadata to include
        pretty: Force pretty printing (None = auto-detect based on tty)
    """
    if pretty is None:
        pretty = sys.stdout.isatty()

    output: dict[str, Any] = {}

    if isinstance(data, list):
        output["results"] = data
        output["count"] = len(data)
    else:
        output["result"] = data

    if meta:
        output["meta"] = meta

    if pretty:
        return json.dumps(output, indent=2, ensure_ascii=False)
    else:
        return json.dumps(output, ensure_ascii=False)


def format_error_json(error: dict[str, Any], pretty: bool | None = None) -> str:
    """Format an error as JSON."""
    if pretty is None:
        pretty = sys.stdout.isatty()

    if pretty:
        return json.dumps(error, indent=2, ensure_ascii=False)
    else:
        return json.dumps(error, ensure_ascii=False)
