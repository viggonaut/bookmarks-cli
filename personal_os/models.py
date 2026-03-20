from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from personal_os.frontmatter import render_frontmatter


@dataclass
class Author:
    name: str
    handle: Optional[str] = None
    id: Optional[str] = None
    url: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "id": self.id,
            "name": self.name,
            "handle": self.handle,
            "url": self.url,
        }


@dataclass
class InfluenceItem:
    item_id: str
    source_type: str
    content_kind: str
    capture_kind: str
    title: str
    canonical_url: str
    source_created_at: str
    captured_at: str
    processed_at: str
    authors: List[Author]
    language: Optional[str]
    tags: List[str]
    themes: List[str]
    people: List[str]
    entities: List[str]
    summary: str
    key_ideas: List[str]
    raw_text_hash: str
    body_text: str
    source_metadata: Dict[str, Any]
    storage: Dict[str, str] = field(default_factory=dict)
    schema_version: str = "1.0"
    embedding: Dict[str, Optional[str]] = field(
        default_factory=lambda: {"status": "not_indexed", "vector_store_id": None}
    )

    def frontmatter(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "item_id": self.item_id,
            "source_type": self.source_type,
            "content_kind": self.content_kind,
            "capture_kind": self.capture_kind,
            "title": self.title,
            "canonical_url": self.canonical_url,
            "source_created_at": self.source_created_at,
            "captured_at": self.captured_at,
            "processed_at": self.processed_at,
            "authors": [author.as_dict() for author in self.authors],
            "language": self.language,
            "tags": self.tags,
            "themes": self.themes,
            "people": self.people,
            "entities": self.entities,
            "summary": self.summary,
            "key_ideas": self.key_ideas,
            "raw_text_hash": self.raw_text_hash,
            "embedding": self.embedding,
            "storage": self.storage,
            "source_metadata": self.source_metadata,
        }

    def to_markdown(self) -> str:
        lines = [
            render_frontmatter(self.frontmatter()).rstrip(),
            "",
            f"# {self.title}",
            "",
            "## Summary",
            self.summary or "No summary available.",
            "",
            "## Key Ideas",
        ]

        if self.key_ideas:
            lines.extend(f"- {idea}" for idea in self.key_ideas)
        else:
            lines.append("- No key ideas extracted.")

        lines.extend(
            [
                "",
                "## Source Text",
                self.body_text or "No source text available.",
                "",
                "## Source",
                f"- URL: {self.canonical_url}",
                f"- Captured at: {self.captured_at}",
                f"- Source created at: {self.source_created_at}",
            ]
        )

        return "\n".join(lines).strip() + "\n"
