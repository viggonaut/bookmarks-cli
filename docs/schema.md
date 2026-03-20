# Influence Item Schema

Each stored influence item is a Markdown file with YAML frontmatter.

## Shared frontmatter fields

- `schema_version`
- `item_id`
- `source_type`
- `content_kind`
- `capture_kind`
- `title`
- `canonical_url`
- `source_created_at`
- `captured_at`
- `processed_at`
- `authors`
- `language`
- `tags`
- `themes`
- `people`
- `entities`
- `summary`
- `key_ideas`
- `raw_text_hash`
- `embedding`
- `storage`
- `source_metadata`

## Field intent

- Shared fields stay consistent across X, podcasts, and articles
- `canonical_url` is a required direct link back to the original source item and should always be usable by humans and agents to jump back into the source system
- `source_metadata` holds source-specific details without breaking the common contract
- `embedding` is present now so vector indexing can be added later without a schema break
- `storage` gives agents enough context to find raw payloads and related artifacts

## Example

```markdown
---
schema_version: "1.0"
item_id: "x:1899900000000000001"
source_type: "x"
content_kind: "post"
capture_kind: "bookmark"
title: "@coachx: Good training systems come from boring consistency, not heroic..."
canonical_url: "https://x.com/coachx/status/1899900000000000001"
source_created_at: "2026-03-18T08:45:00Z"
captured_at: "2026-03-20T11:15:00Z"
processed_at: "2026-03-20T11:15:04Z"
authors:
  -
    id: "42"
    name: "Coach Example"
    handle: "coachx"
    url: "https://x.com/coachx"
language: "en"
tags:
  - "bookmark"
  - "training"
  - "x"
themes:
  - "training"
people:
  - "@coachx"
entities: []
summary: "Good training systems come from boring consistency, not heroic motivation."
key_ideas:
  - "Good training systems come from boring consistency, not heroic motivation."
raw_text_hash: "a477..."
embedding:
  status: "not_indexed"
  vector_store_id: null
storage:
  markdown_path: "x/2026/03/18/1899900000000000001.md"
  raw_payload_path: "_meta/raw/x/2026/03/18/1899900000000000001.json"
source_metadata:
  platform: "x"
  external_id: "1899900000000000001"
  author_id: "42"
  author_handle: "coachx"
  conversation_id: "1899900000000000001"
  bookmarked_at: "2026-03-20T11:15:00Z"
  hashtags:
    - "training"
  mentions: []
  urls: []
  public_metrics:
    like_count: 12
    repost_count: 2
    reply_count: 1
    quote_count: 0
---
# @coachx: Good training systems come from boring consistency, not heroic...
```

See [schemas/influence-item.schema.json](../schemas/influence-item.schema.json) for the machine-readable shape.
