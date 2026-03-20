# X Bookmarks

X bookmarks are the first reference implementation of the shared ingestion pipeline.

## Supported modes

- `file`
  - reads a local JSON or JSONL file
  - ideal for exported data or browser automation output
- `api`
  - reads from the X bookmarks API using a user access token from local OAuth state or `X_USER_ACCESS_TOKEN`
- `auto`
  - picks `file` if an input path is available
  - otherwise picks `api` if user auth is available

## Why this shape

X product and API stability is the main risk, not your bookmark volume.

So the pipeline is structured around a normalized bookmark contract:

- API fetchers can emit the contract
- browser automation can emit the same contract later
- manual exports can be imported immediately

That keeps storage and enrichment stable even if capture changes.

This X adapter is also the reference pattern for future sources: capture can vary by platform, but the stored artifact contract should stay stable.

## Fallback plan

Recommended v1 path:

1. Use API mode if it remains reliable
2. Keep file ingest as a first-class path
3. If API reliability degrades, add Playwright automation that writes the same JSON contract used by file mode

The current code already supports step 2 and the downstream half of step 3.

## CLI

```bash
python3 -m bookmarks_cli auth x-login
python3 -m bookmarks_cli backfill x-bookmarks --source file --input /path/to/all-bookmarks.json
python3 -m bookmarks_cli backfill x-bookmarks
python3 -m bookmarks_cli rebuild x-bookmarks
python3 -m bookmarks_cli query x-bookmarks --text "training" --limit 5
python3 -m bookmarks_cli sync x-bookmarks
python3 -m bookmarks_cli sync x-bookmarks --limit 50
python3 -m bookmarks_cli sync x-bookmarks --source file --input /path/to/bookmarks.json
python3 -m bookmarks_cli ingest x-bookmarks --input /path/to/bookmarks.json
```

## Operational split

- `backfill x-bookmarks`
  - onboarding import for your full existing bookmark history
  - if `--limit` is omitted, it attempts to process everything available from the source
  - state is written to `_meta/state/x_bookmarks_backfill.json`
- `sync x-bookmarks`
  - recurring pull for new bookmarks after onboarding
  - fetches newest-first and stops when it reaches the last seen bookmark ID from prior sync state
  - defaults to `X_BOOKMARKS_LIMIT` as a safety cap, but only new items are sent through enrichment
  - state is written to `_meta/state/x_bookmarks.json`
- `rebuild x-bookmarks`
  - rebuilds Markdown artifacts from local raw payload snapshots
  - lets you improve enrichment without paying to fetch the same bookmarks again
- `query x-bookmarks`
  - searches stored Markdown artifacts locally
  - returns titles, summaries, direct X links, and file paths
