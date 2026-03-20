from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json

from personal_os.storage import parse_timestamp


def split_frontmatter(markdown_text: str) -> Tuple[Dict[str, Any], str]:
    if not markdown_text.startswith("---\n"):
        return {}, markdown_text

    end_marker = "\n---\n"
    end_index = markdown_text.find(end_marker, 4)
    if end_index == -1:
        return {}, markdown_text

    raw_frontmatter = markdown_text[4:end_index]
    body = markdown_text[end_index + len(end_marker) :]
    return parse_frontmatter(raw_frontmatter), body


def _indent_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_scalar(raw_value: str) -> Any:
    value = raw_value.strip()
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith('"') or value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _parse_block(lines: List[str], index: int, indent: int) -> Tuple[Any, int]:
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        return {}, index

    if _indent_spaces(lines[index]) == indent and lines[index].lstrip().startswith("-"):
        return _parse_sequence(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines: List[str], index: int, indent: int) -> Tuple[Dict[str, Any], int]:
    result: Dict[str, Any] = {}

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        current_indent = _indent_spaces(line)
        if current_indent < indent:
            break
        if current_indent != indent:
            break

        stripped = line[indent:]
        if stripped.startswith("-"):
            break

        key, separator, remainder = stripped.partition(":")
        if not separator:
            index += 1
            continue

        remainder = remainder[1:] if remainder.startswith(" ") else remainder
        if remainder == "":
            value, index = _parse_block(lines, index + 1, indent + 2)
        else:
            value = _parse_scalar(remainder)
            index += 1
        result[key] = value

    return result, index


def _parse_sequence(lines: List[str], index: int, indent: int) -> Tuple[List[Any], int]:
    result: List[Any] = []

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        current_indent = _indent_spaces(line)
        if current_indent < indent:
            break
        if current_indent != indent or not line[indent:].startswith("-"):
            break

        stripped = line[indent + 1 :]
        stripped = stripped[1:] if stripped.startswith(" ") else stripped

        if stripped == "":
            value, index = _parse_block(lines, index + 1, indent + 2)
        else:
            value = _parse_scalar(stripped)
            index += 1
        result.append(value)

    return result, index


def parse_frontmatter(raw_frontmatter: str) -> Dict[str, Any]:
    lines = raw_frontmatter.splitlines()
    if not lines:
        return {}
    parsed, _ = _parse_block(lines, 0, 0)
    if isinstance(parsed, dict):
        return parsed
    return {}


@dataclass
class QueryResult:
    path: Path
    frontmatter: Dict[str, Any]
    body: str

    @property
    def title(self) -> str:
        return str(self.frontmatter.get("title", self.path.stem))

    @property
    def canonical_url(self) -> Optional[str]:
        value = self.frontmatter.get("canonical_url")
        return str(value) if value else None

    @property
    def summary(self) -> str:
        return str(self.frontmatter.get("summary", ""))

    @property
    def source_created_at(self) -> str:
        return str(self.frontmatter.get("source_created_at", ""))


def iter_markdown_items(root: Path) -> Iterable[QueryResult]:
    if not root.exists():
        return []

    results: List[QueryResult] = []
    for path in sorted(root.rglob("*.md")):
        markdown_text = path.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(markdown_text)
        results.append(QueryResult(path=path, frontmatter=frontmatter, body=body))
    return results


def _text_haystack(item: QueryResult) -> str:
    authors = item.frontmatter.get("authors", [])
    author_parts = []
    for author in authors:
        if isinstance(author, dict):
            author_parts.extend([str(author.get("name", "")), str(author.get("handle", ""))])

    key_ideas = item.frontmatter.get("key_ideas", [])
    return " ".join(
        [
            item.title,
            item.summary,
            " ".join(str(part) for part in key_ideas),
            item.body,
            " ".join(author_parts),
            str(item.canonical_url or ""),
        ]
    ).lower()


def query_items(
    items: Iterable[QueryResult],
    *,
    text: Optional[str] = None,
    tags: Optional[List[str]] = None,
    themes: Optional[List[str]] = None,
    people: Optional[List[str]] = None,
    author: Optional[str] = None,
    limit: int = 10,
) -> List[QueryResult]:
    tags = [tag.lower() for tag in (tags or [])]
    themes = [theme.lower() for theme in (themes or [])]
    people = [person.lower() for person in (people or [])]
    text_query = (text or "").strip().lower()
    author_query = (author or "").strip().lower()

    matched: List[QueryResult] = []
    for item in items:
        frontmatter = item.frontmatter
        item_tags = [str(tag).lower() for tag in frontmatter.get("tags", [])]
        item_themes = [str(theme).lower() for theme in frontmatter.get("themes", [])]
        item_people = [str(person).lower() for person in frontmatter.get("people", [])]
        authors = frontmatter.get("authors", [])
        author_blob = " ".join(
            " ".join([str(author.get("name", "")), str(author.get("handle", ""))])
            for author in authors
            if isinstance(author, dict)
        ).lower()

        if tags and not all(tag in item_tags for tag in tags):
            continue
        if themes and not all(theme in item_themes for theme in themes):
            continue
        if people and not all(person in item_people for person in people):
            continue
        if author_query and author_query not in author_blob:
            continue
        if text_query and text_query not in _text_haystack(item):
            continue
        matched.append(item)

    matched.sort(
        key=lambda item: (
            parse_timestamp(item.source_created_at) if item.source_created_at else parse_timestamp("1970-01-01T00:00:00Z")
        ),
        reverse=True,
    )
    return matched[:limit]
