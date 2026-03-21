from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import json
import re

from bookmarks_cli.storage import parse_timestamp


TOKEN_RE = re.compile(r"[a-z0-9@._-]+")
STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "around",
    "as",
    "at",
    "bookmark",
    "bookmarks",
    "for",
    "from",
    "i",
    "is",
    "latest",
    "me",
    "my",
    "of",
    "on",
    "ones",
    "or",
    "please",
    "post",
    "posts",
    "relevant",
    "show",
    "something",
    "that",
    "the",
    "these",
    "this",
    "to",
    "tweet",
    "tweets",
    "which",
    "with",
    "write",
    "writing",
    "x",
}
FIELD_WEIGHTS = {
    "authors": 5.0,
    "title": 4.5,
    "summary": 4.0,
    "key_ideas": 4.0,
    "themes": 3.5,
    "tags": 3.0,
    "people": 3.0,
    "body": 1.0,
    "canonical_url": 0.5,
}
CO_OCCURRENCE_BONUS = {
    "authors": 2.0,
    "title": 1.5,
    "summary": 1.5,
    "key_ideas": 1.25,
    "themes": 1.0,
    "tags": 1.0,
    "people": 1.0,
    "body": 0.5,
    "canonical_url": 0.25,
}
FIELD_ORDER = tuple(FIELD_WEIGHTS.keys())
TERM_EXPANSIONS = {
    "assistant": ["agents", "companion", "companions"],
    "assistants": ["agents", "assistant", "companions"],
    "character": ["companion", "companions", "memory", "persona"],
    "characters": ["companion", "companions", "memory", "persona"],
    "companion": ["companions", "character", "characters", "agents", "memory", "persona"],
    "companions": ["companion", "character", "characters", "agents", "memory", "persona"],
    "companies": ["company", "startup", "startups", "business", "businesses"],
    "company": ["companies", "startup", "startups", "business", "businesses"],
    "memory": ["agent", "agents", "companion", "companions", "character", "characters"],
    "persona": ["companion", "companions", "character", "characters"],
    "startup": ["company", "companies", "business", "businesses"],
    "startups": ["company", "companies", "business", "businesses"],
}


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
    search_score: float = 0.0
    matched_fields: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)
    matched_queries: List[str] = field(default_factory=list)

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


def parse_date_bound(raw_value: Optional[str], *, end_of_day: bool) -> Optional[datetime]:
    cleaned = (raw_value or "").strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z") or "T" in cleaned:
        return parse_timestamp(cleaned)
    parsed_date = datetime.fromisoformat(cleaned)
    if end_of_day:
        return parsed_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
    return parsed_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def _author_blob(item: QueryResult) -> str:
    authors = item.frontmatter.get("authors", [])
    author_parts = []
    for author in authors:
        if isinstance(author, dict):
            author_parts.extend([str(author.get("name", "")), str(author.get("handle", ""))])
    return " ".join(author_parts)


def _normalize_token(token: str) -> Set[str]:
    normalized = token.lower().strip().strip("._-")
    if not normalized:
        return set()

    variants = {normalized}
    base = normalized[1:] if normalized.startswith("@") else normalized
    if base:
        variants.add(base)

    if len(base) > 4 and base.endswith("ies"):
        variants.add(base[:-3] + "y")
    elif len(base) > 4 and base.endswith("s") and not base.endswith("ss"):
        variants.add(base[:-1])

    if normalized.startswith("@"):
        for variant in list(variants):
            if variant and not variant.startswith("@"):
                variants.add(variant)

    return {variant for variant in variants if variant}


def _tokenize(text: str, *, drop_stopwords: bool) -> List[str]:
    seen = set()
    tokens: List[str] = []
    for raw_token in TOKEN_RE.findall((text or "").lower()):
        for token in sorted(_normalize_token(raw_token)):
            bare = token.lstrip("@")
            if len(bare) < 2:
                continue
            if drop_stopwords and (token in STOPWORDS or bare in STOPWORDS):
                continue
            if token in seen:
                continue
            seen.add(token)
            tokens.append(token)
    return tokens


def _field_texts(item: QueryResult) -> Dict[str, str]:
    return {
        "authors": _author_blob(item),
        "title": item.title,
        "summary": item.summary,
        "key_ideas": " ".join(str(part) for part in item.frontmatter.get("key_ideas", [])),
        "themes": " ".join(str(part) for part in item.frontmatter.get("themes", [])),
        "tags": " ".join(str(part) for part in item.frontmatter.get("tags", [])),
        "people": " ".join(str(part) for part in item.frontmatter.get("people", [])),
        "body": item.body,
        "canonical_url": str(item.canonical_url or ""),
    }


def _ordered_unique(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def _resolve_date_window(
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    days: Optional[int] = None,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    start = parse_date_bound(date_from, end_of_day=False)
    end = parse_date_bound(date_to, end_of_day=True)
    if days is not None and days > 0:
        now = datetime.now(timezone.utc)
        derived_start = now - timedelta(days=days)
        if start is None or derived_start > start:
            start = derived_start
        if end is None:
            end = now
    return start, end


def _within_date_window(
    item: QueryResult,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    days: Optional[int] = None,
) -> bool:
    window_start, window_end = _resolve_date_window(date_from=date_from, date_to=date_to, days=days)
    if window_start is None and window_end is None:
        return True
    if not item.source_created_at:
        return False
    created_at = parse_timestamp(item.source_created_at)
    if window_start is not None and created_at < window_start:
        return False
    if window_end is not None and created_at > window_end:
        return False
    return True


def _score_text_query(item: QueryResult, text_query: str) -> Optional[QueryResult]:
    query_terms = _tokenize(text_query, drop_stopwords=True)
    if not query_terms:
        return None

    field_texts = _field_texts(item)
    field_tokens = {
        field_name: set(_tokenize(field_text, drop_stopwords=False))
        for field_name, field_text in field_texts.items()
    }

    matched_by_field: Dict[str, Set[str]] = {}
    matched_terms: Set[str] = set()
    score = 0.0

    for term in query_terms:
        best_field = None
        best_weight = 0.0
        for field_name, tokens in field_tokens.items():
            if term not in tokens:
                continue
            weight = FIELD_WEIGHTS[field_name]
            if weight > best_weight:
                best_field = field_name
                best_weight = weight
        if best_field:
            matched_terms.add(term)
            matched_by_field.setdefault(best_field, set()).add(term)
            score += best_weight

    if not matched_terms:
        return None

    for field_name, terms in matched_by_field.items():
        if len(terms) > 1:
            score += (len(terms) - 1) * CO_OCCURRENCE_BONUS[field_name]

    min_terms = 1 if len(query_terms) <= 2 else 2
    if len(matched_terms) < min_terms:
        return None

    ordered_fields = [
        field_name
        for field_name in FIELD_ORDER
        if field_name in matched_by_field
    ]
    ordered_terms = [term for term in query_terms if term in matched_terms]
    return replace(
        item,
        search_score=score,
        matched_fields=ordered_fields,
        matched_terms=ordered_terms,
        matched_queries=[text_query],
    )


def _author_candidates(items: Iterable[QueryResult]) -> List[Tuple[str, List[str], str, List[str]]]:
    candidates: List[Tuple[str, List[str], str, List[str]]] = []
    seen = set()
    for item in items:
        for author in item.frontmatter.get("authors", []):
            if not isinstance(author, dict):
                continue
            name = str(author.get("name", "")).strip()
            handle = str(author.get("handle", "")).strip()
            if not name and not handle:
                continue
            key = (name.lower(), handle.lower())
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                (
                    name,
                    _tokenize(name, drop_stopwords=True),
                    handle,
                    _tokenize(handle, drop_stopwords=True),
                )
            )
    return candidates


def _infer_author_query(items: Iterable[QueryResult], raw_query: str) -> Optional[str]:
    query_terms = set(_tokenize(raw_query, drop_stopwords=True))
    best_score = 0
    best_value: Optional[str] = None

    for name, name_tokens, handle, handle_tokens in _author_candidates(items):
        if handle_tokens and all(token in query_terms for token in handle_tokens):
            score = 10 + len(handle_tokens)
            if score > best_score:
                best_score = score
                best_value = handle or name
        if len(name_tokens) >= 2 and all(token in query_terms for token in name_tokens):
            score = 8 + len(name_tokens)
            if score > best_score:
                best_score = score
                best_value = name or handle

    return best_value


def _extract_explicit_people(raw_query: str) -> List[str]:
    handles = []
    for raw_token in TOKEN_RE.findall(raw_query):
        if raw_token.startswith("@"):
            handles.append(raw_token.lower().strip().strip("._-"))
    return _ordered_unique(handles)


def _topic_text(raw_query: str, author_query: Optional[str], people: List[str]) -> str:
    remove_terms = set()
    if author_query:
        remove_terms.update(_tokenize(author_query, drop_stopwords=True))
    for person in people:
        remove_terms.update(_normalize_token(person))

    remaining_terms = [term for term in _tokenize(raw_query, drop_stopwords=True) if term not in remove_terms]
    return " ".join(_ordered_unique(remaining_terms))


def _expanded_text_queries(text_query: str) -> List[str]:
    terms = _tokenize(text_query, drop_stopwords=True)
    expanded_queries: List[str] = []
    for index, term in enumerate(terms):
        expansions = TERM_EXPANSIONS.get(term, [])
        if not expansions:
            continue
        anchors = [anchor for offset, anchor in enumerate(terms) if offset != index]
        for expansion in expansions:
            candidate_terms = anchors + [expansion]
            expanded_queries.append(" ".join(_ordered_unique(candidate_terms)))
    return _ordered_unique(expanded_queries)


def _merge_query_results(existing: QueryResult, incoming: QueryResult, score_delta: float) -> QueryResult:
    combined_fields = [field_name for field_name in FIELD_ORDER if field_name in set(existing.matched_fields + incoming.matched_fields)]
    combined_terms = _ordered_unique(existing.matched_terms + incoming.matched_terms)
    combined_queries = _ordered_unique(existing.matched_queries + incoming.matched_queries)
    return replace(
        existing,
        search_score=existing.search_score + score_delta,
        matched_fields=combined_fields,
        matched_terms=combined_terms,
        matched_queries=combined_queries,
    )


def search_items(
    items: Iterable[QueryResult],
    *,
    query: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    days: Optional[int] = None,
    limit: int = 10,
) -> List[QueryResult]:
    items_list = [
        item
        for item in items
        if _within_date_window(item, date_from=date_from, date_to=date_to, days=days)
    ]
    raw_query = (query or "").strip()
    if not raw_query:
        return []

    explicit_people = _extract_explicit_people(raw_query)
    inferred_author = _infer_author_query(items_list, raw_query)
    focused_topic = _topic_text(raw_query, inferred_author, explicit_people)

    plans: List[Tuple[str, Dict[str, Any], float]] = []
    seen_plan_keys = set()

    def add_plan(label: str, *, text: Optional[str], author: Optional[str] = None, people: Optional[List[str]] = None, weight: float) -> None:
        normalized_text = (text or "").strip()
        normalized_people = tuple((people or []))
        if not normalized_text:
            return
        key = (normalized_text, author or "", normalized_people)
        if key in seen_plan_keys:
            return
        seen_plan_keys.add(key)
        plans.append(
            (
                label,
                {
                    "text": normalized_text,
                    "author": author,
                    "people": list(normalized_people) or None,
                },
                weight,
            )
        )

    add_plan("exact", text=raw_query, weight=1.5)
    if focused_topic:
        add_plan("focused", text=focused_topic, weight=1.2)
    if explicit_people and focused_topic:
        add_plan("person", text=focused_topic, people=explicit_people, weight=1.6)
    if inferred_author and focused_topic:
        add_plan("author", text=focused_topic, author=inferred_author, weight=1.8)

    expansion_source = focused_topic or raw_query
    for expanded_text in _expanded_text_queries(expansion_source):
        add_plan("expanded", text=expanded_text, weight=0.9)
        if explicit_people:
            add_plan("expanded-person", text=expanded_text, people=explicit_people, weight=1.1)
        if inferred_author:
            add_plan("expanded-author", text=expanded_text, author=inferred_author, weight=1.2)

    merged: Dict[Path, QueryResult] = {}
    per_plan_limit = max(limit * 3, 20)
    for label, kwargs, weight in plans:
        plan_terms = _tokenize(str(kwargs.get("text") or ""), drop_stopwords=True)
        plan_term_count = max(len(plan_terms), 1)
        results = query_items(items_list, limit=per_plan_limit, **kwargs)
        for result in results:
            coverage = max(len(result.matched_terms), 1) / plan_term_count
            weighted_score = max(result.search_score, 1.0) * weight * coverage
            result_with_label = replace(
                result,
                matched_queries=_ordered_unique(result.matched_queries + [label]),
            )
            existing = merged.get(result.path)
            if existing is None:
                merged[result.path] = replace(result_with_label, search_score=weighted_score)
            else:
                merged[result.path] = _merge_query_results(existing, result_with_label, weighted_score)

    ranked = sorted(
        merged.values(),
        key=lambda item: (
            item.search_score,
            parse_timestamp(item.source_created_at) if item.source_created_at else parse_timestamp("1970-01-01T00:00:00Z"),
        ),
        reverse=True,
    )
    return ranked[:limit]


def query_items(
    items: Iterable[QueryResult],
    *,
    text: Optional[str] = None,
    tags: Optional[List[str]] = None,
    themes: Optional[List[str]] = None,
    people: Optional[List[str]] = None,
    author: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    days: Optional[int] = None,
    limit: int = 10,
) -> List[QueryResult]:
    tags = [tag.lower() for tag in (tags or [])]
    themes = [theme.lower() for theme in (themes or [])]
    people = [person.lower() for person in (people or [])]
    text_query = (text or "").strip().lower()
    author_query = (author or "").strip().lower()

    matched: List[QueryResult] = []
    for item in items:
        if not _within_date_window(item, date_from=date_from, date_to=date_to, days=days):
            continue
        frontmatter = item.frontmatter
        item_tags = [str(tag).lower() for tag in frontmatter.get("tags", [])]
        item_themes = [str(theme).lower() for theme in frontmatter.get("themes", [])]
        item_people = [str(person).lower() for person in frontmatter.get("people", [])]
        author_blob = _author_blob(item).lower()

        if tags and not all(tag in item_tags for tag in tags):
            continue
        if themes and not all(theme in item_themes for theme in themes):
            continue
        if people and not all(person in item_people for person in people):
            continue
        if author_query and author_query not in author_blob:
            continue
        if text_query:
            scored_item = _score_text_query(item, text_query)
            if not scored_item:
                continue
            matched.append(scored_item)
            continue
        matched.append(replace(item))

    matched.sort(
        key=lambda item: (
            item.search_score,
            parse_timestamp(item.source_created_at) if item.source_created_at else parse_timestamp("1970-01-01T00:00:00Z")
        ),
        reverse=True,
    )
    return matched[:limit]
