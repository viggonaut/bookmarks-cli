# Query Workflow

V1 retrieval is local-file-first.

The initial retrieval flow queries stored Markdown artifacts under `BOOKMARKS_PATH`, not the source APIs.

## Why

- avoids repeated API cost
- uses enriched data rather than raw payloads only
- works for humans and agents over the same stored artifacts
- preserves direct links back to the original source via `canonical_url`

## CLI

```bash
python3 -m bookmarks_cli search x-bookmarks --query "codex agents" --limit 5 --format json
python3 -m bookmarks_cli search x-bookmarks --query "gstack" --date-from 2026-03-14 --date-to 2026-03-21 --limit 10 --format json
python3 -m bookmarks_cli search x-bookmarks --query "gstack" --days 7 --limit 10 --format json
python3 -m bookmarks_cli search x-bookmarks --query "symphoni" --author openai --author openaidevs --limit 10 --format json
python3 -m bookmarks_cli query x-bookmarks --text "codex agents" --limit 5
python3 -m bookmarks_cli query x-bookmarks --tag agents --limit 10
python3 -m bookmarks_cli query x-bookmarks --person @danshipper --format json
python3 -m bookmarks_cli query x-bookmarks --theme agents --author dan --limit 5
```

## Retrieval model

The query command currently supports:

- text search across title, summary, key ideas, body text, author names/handles, and canonical URL
- exact filters over tags
- exact filters over themes
- exact filters over people
- author matching

The search command adds a higher-level retrieval workflow for natural-language requests:

- exact text search first
- author and person inference when the query names someone
- small semantic expansions for terms like companions, characters, assistants, startups, and memory
- merged ranking across multiple passes
- strict source filtering when the request says "from <account>" or you pass `--author` / `--person`

## Regenerating older artifacts

If you improve enrichment heuristics, regenerate Markdown from the raw payload snapshots:

```bash
python3 -m bookmarks_cli rebuild x-bookmarks
```

That rewrites stored Markdown from `_meta/raw/x/` without re-fetching bookmarks from the X API.
