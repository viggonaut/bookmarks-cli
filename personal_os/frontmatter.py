from __future__ import annotations

import json
from typing import Any, List


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _dump_lines(value: Any, indent: int = 0) -> List[str]:
    prefix = "  " * indent

    if isinstance(value, dict):
        if not value:
            return [prefix + "{}"]
        lines: List[str] = []
        for key, nested_value in value.items():
            if _is_scalar(nested_value):
                lines.append(f"{prefix}{key}: {_format_scalar(nested_value)}")
            elif isinstance(nested_value, list) and not nested_value:
                lines.append(f"{prefix}{key}: []")
            elif isinstance(nested_value, dict) and not nested_value:
                lines.append(f"{prefix}{key}: {{}}")
            else:
                lines.append(f"{prefix}{key}:")
                lines.extend(_dump_lines(nested_value, indent + 1))
        return lines

    if isinstance(value, list):
        if not value:
            return [prefix + "[]"]
        lines = []
        for item in value:
            if _is_scalar(item):
                lines.append(f"{prefix}- {_format_scalar(item)}")
            else:
                lines.append(f"{prefix}-")
                lines.extend(_dump_lines(item, indent + 1))
        return lines

    return [prefix + _format_scalar(value)]


def render_frontmatter(data: Any) -> str:
    return "---\n" + "\n".join(_dump_lines(data)) + "\n---\n"
