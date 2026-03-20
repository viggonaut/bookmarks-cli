# Architecture

`bookmarks-cli` is the automation layer around a local archive directory. The configured external path from `BOOKMARKS_PATH` is the durable store for saved-content artifacts.

## System boundaries

- `bookmarks-cli`
  - source integrations
  - normalization
  - enrichment
  - schemas
  - prompts
  - CLI entrypoints
- archive directory
  - generated Markdown artifacts
  - raw source payload snapshots
  - sync state
  - future derived artifacts like embeddings or indexes

## Processing model

The pipeline is intentionally linear in v1 and is meant to stay stable across sources:

1. Capture
2. Normalize
3. Enrich
4. Persist

X bookmarks are the first implemented adapter, so the current concrete flow is:

1. Fetch bookmarks from either an API response or a local file
2. Determine the diff against local sync state
3. Normalize each new bookmark into a stable internal shape
4. Produce lightweight enrichment
5. Write:
   - Markdown artifact under `x/YYYY/MM/DD/<id>.md`
   - raw payload snapshot under `_meta/raw/x/YYYY/MM/DD/<id>.json`
   - sync state under `_meta/state/x_bookmarks.json`
   - onboarding backfill state under `_meta/state/x_bookmarks_backfill.json`
6. Query stored Markdown locally for retrieval

## Design constraints

- Capture must stay low-friction
- Capture adapters can vary by source without changing the stored artifact contract
- Foldering in source apps is not the main retrieval model
- Stored bookmark artifacts must be readable by both humans and agents
- The storage shape must survive interface changes
- Enrichment can get smarter later without changing the artifact contract

## Why Markdown plus frontmatter

- Easy to inspect and edit
- Works with Obsidian, editors, git, and retrieval/indexing tools
- Keeps the raw human-visible representation and machine-parseable metadata together
- Supports a future mix of metadata filters, tags, and embeddings across sources
