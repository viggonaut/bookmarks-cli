# Retrieval Workflow

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

Use `search x-bookmarks` by default when the user gives a natural-language request.

Use `query x-bookmarks` when you already know the exact field constraints you want.

The query command supports:

- text search across title, summary, key ideas, body text, author names/handles, and canonical URL
- exact filters over tags
- exact filters over themes
- exact filters over people
- author matching
- explicit date filters via `--date-from`, `--date-to`, and `--days`

The search command adds a higher-level retrieval workflow for natural-language requests:

- exact text search first
- author and person inference when the query names someone
- small semantic expansions for terms like companions, characters, assistants, startups, and memory
- merged ranking across multiple passes
- strict source filtering when the request says "from <account>" or you pass `--author` / `--person`
- typo-tolerant matching for near-miss tokens like `symphoni`

## Output model

For agents, prefer `--format json`.

Search results now include:

- `canonical_url`
- `authors`
- `search_score`
- `matched_fields`
- `matched_terms`
- `matched_queries`
- `why_relevant`

That should usually be enough to answer without opening bookmark files directly.

## Recommended agent workflow

1. Start with `search x-bookmarks --format json`
2. Add `--date-from` / `--date-to` or `--days` if the user mentions a time window
3. Add `--author` and `--person` if the user asks for posts from a specific account
4. Only drop to lower-level `query` calls if you need exact field control
5. Only inspect files directly if the CLI output is still ambiguous

## Regenerating older artifacts

If you improve enrichment heuristics, regenerate Markdown from the raw payload snapshots:

```bash
python3 -m bookmarks_cli rebuild x-bookmarks
```

That rewrites stored Markdown from `_meta/raw/x/` without re-fetching bookmarks from the X API.
