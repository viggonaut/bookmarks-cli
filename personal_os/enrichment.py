from __future__ import annotations

import html
from typing import Iterable, List
from urllib.parse import urlparse
import re


KEYWORD_THEMES = {
    "training": "training",
    "fitness": "training",
    "health": "health",
    "sleep": "health",
    "ai": "ai",
    "agent": "agents",
    "agents": "agents",
    "workflow": "workflows",
    "workflows": "workflows",
    "systems": "systems",
    "writing": "writing",
    "memory": "memory",
    "product": "product",
    "business": "business",
}

ENTITY_STOPWORDS = {
    "A",
    "An",
    "And",
    "As",
    "At",
    "But",
    "By",
    "For",
    "From",
    "Here",
    "If",
    "In",
    "Into",
    "The",
    "This",
    "That",
    "These",
    "Those",
    "It",
    "Its",
    "Last",
    "More",
    "Our",
    "So",
    "Their",
    "Then",
    "There",
    "They",
    "We",
    "When",
    "Where",
    "Why",
    "Good",
    "Small",
    "Agents",
    "Design",
    "You",
    "I",
}

MIXED_CASE_ENTITY_PATTERN = re.compile(r"\b(?:[A-Z]{2,}[A-Za-z0-9]+|[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*)\b")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9&+'._-]*")


def unique(items: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def clean_text(text: str) -> str:
    unescaped = html.unescape(text or "")
    normalized = unescaped.replace("\u00a0", " ").replace("\u200b", "")
    return re.sub(r"\s+", " ", normalized.strip())


def split_sentences(text: str) -> List[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def summarize_text(text: str, max_chars: int = 220) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return ""
    summary = sentences[0]
    if len(summary) <= max_chars:
        return summary
    return summary[: max_chars - 3].rstrip() + "..."


def extract_key_ideas(text: str, max_items: int = 3) -> List[str]:
    ideas = split_sentences(text)
    return ideas[:max_items]


def extract_hashtags(text: str) -> List[str]:
    return unique(match.lower() for match in re.findall(r"#([A-Za-z0-9_]+)", text or ""))


def extract_mentions(text: str) -> List[str]:
    return unique(match.lower() for match in re.findall(r"@([A-Za-z0-9_]+)", text or ""))


def extract_themes(text: str) -> List[str]:
    lowered = (text or "").lower()
    themes = []
    for keyword, theme in KEYWORD_THEMES.items():
        pattern = r"\b{keyword}\b".format(keyword=re.escape(keyword))
        if re.search(pattern, lowered):
            themes.append(theme)
    return unique(themes)


def extract_tags(text: str, hashtags: Iterable[str], urls: Iterable[str]) -> List[str]:
    tags = ["x", "bookmark"]
    tags.extend(tag.lower() for tag in hashtags)
    tags.extend(extract_themes(text))
    for url in urls:
        host = urlparse(url).netloc.lower().replace("www.", "")
        if host:
            tags.append(host)
    return unique(tags)


def extract_entities(text: str) -> List[str]:
    entities = []
    cleaned = clean_text(text)

    for match in MIXED_CASE_ENTITY_PATTERN.findall(cleaned):
        if match in ENTITY_STOPWORDS:
            continue
        entities.append(match)

    for sentence in split_sentences(cleaned):
        tokens = TOKEN_PATTERN.findall(sentence)
        index = 0
        while index < len(tokens):
            token = tokens[index]
            is_titlecase = token[:1].isupper() and any(char.islower() for char in token[1:])
            if not is_titlecase:
                index += 1
                continue

            phrase_tokens = [token]
            next_index = index + 1
            while next_index < len(tokens):
                next_token = tokens[next_index]
                next_is_titlecase = next_token[:1].isupper() and any(char.islower() for char in next_token[1:])
                if not next_is_titlecase:
                    break
                phrase_tokens.append(next_token)
                next_index += 1

            candidate = " ".join(phrase_tokens)
            if any(part in ENTITY_STOPWORDS for part in phrase_tokens):
                index = next_index
                continue
            if len(candidate) <= 2:
                index = next_index
                continue

            entities.append(candidate)
            index = next_index

    return unique(entities)[:5]


def build_title(handle: str, text: str, max_chars: int = 80) -> str:
    prefix = "@{handle}: ".format(handle=handle) if handle else "X post: "
    cleaned = clean_text(text)
    if not cleaned:
        return prefix + "Untitled"
    if len(prefix) + len(cleaned) <= max_chars:
        return prefix + cleaned
    return prefix + cleaned[: max_chars - len(prefix) - 3].rstrip() + "..."
