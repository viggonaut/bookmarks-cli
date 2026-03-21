# CLAUDE.md

## Purpose

This repo powers a bookmark capture, sync, and query CLI.

The primary active use case is X bookmarks:

- historical onboarding via `backfill x-bookmarks`
- incremental sync via `sync x-bookmarks`
- local retrieval over stored artifacts via `query x-bookmarks`

The durable bookmark archive lives outside the repo at `BOOKMARKS_PATH` (`INFLUENCE_PATH` still works as a legacy fallback).

## CLI Rule

For agent execution, prefer the module entrypoint:

```bash
python3 -m bookmarks_cli ...
```

Do not assume `bookmarks-cli` is on `PATH` in every runtime.

`bookmarks-cli ...` is a convenience entrypoint for interactive shells when the user's local PATH has been configured correctly.

## Default Retrieval Workflow

When the user asks for:

- writing input
- content ideas
- research context
- examples
- worldview/theme synthesis
- "show me relevant X bookmarks"

query the local influence store before brainstorming from scratch.

If `python3 -m bookmarks_cli ...` is unavailable or the archive path is unclear, run:

```bash
python3 -m bookmarks_cli doctor
```

Do not search sibling repos, inspect `.env` files, or manually scan `BOOKMARKS_PATH` before trying the supported CLI workflow.

Default first step:

```bash
python3 -m bookmarks_cli search x-bookmarks --query "<topic>" --limit 10 --format json
```

If the request includes a time window like "from last week" or "from March 14 through March 21, 2026", translate that into explicit date flags:

```bash
python3 -m bookmarks_cli search x-bookmarks --query "<topic>" --date-from YYYY-MM-DD --date-to YYYY-MM-DD --limit 10 --format json
python3 -m bookmarks_cli search x-bookmarks --query "<topic>" --days 7 --limit 10 --format json
```

If the query is broad or the result quality is mixed, follow with narrower passes:

```bash
python3 -m bookmarks_cli query x-bookmarks --author "<name-or-handle>" --limit 10 --format json
python3 -m bookmarks_cli query x-bookmarks --person "@handle" --limit 10 --format json
python3 -m bookmarks_cli query x-bookmarks --theme "<theme>" --limit 10 --format json
python3 -m bookmarks_cli query x-bookmarks --tag "<tag>" --limit 10 --format json
```

If those passes still fail and the request depends on retrieval quality, use:

```bash
python3 -m bookmarks_cli rebuild x-bookmarks
```

Then repeat the query workflow before any manual file inspection.

## Output Expectations

When returning relevant X bookmarks, prefer:

1. direct X links from `canonical_url`
2. short explanation of why each bookmark is relevant
3. concise synthesis of recurring ideas across the results

When helpful, include:

- title
- summary
- tags/themes
- matched person or author
- file path to the stored artifact

## Freshness Rule

If the user wants the latest bookmarks, or asks to refresh, pull, or sync first, run:

```bash
python3 -m bookmarks_cli sync x-bookmarks --source api
```

Then run the query workflow.

Do not run sync by default for every writing or research request. Query local artifacts first unless freshness is explicitly important.

## Rebuild Rule

If retrieval quality seems limited by old enrichment, regenerate Markdown from local raw payloads without re-fetching from X:

```bash
python3 -m bookmarks_cli rebuild x-bookmarks
```

Repeat the query workflow after rebuild before falling back to direct file inspection.

## Example

For a prompt like:

> I want to write a new article and post on X around <topic>. Please show me X bookmarks that are relevant for this.

default workflow:

1. query local X bookmarks with the topic
2. return the most relevant direct X links
3. summarize patterns across the bookmarks
4. optionally propose angles for the article/X post based on the retrieved material

## Anti-Patterns

Avoid these behaviors unless the supported CLI workflow has already failed:

- scanning the bookmark archive directly with `find`, `grep`, or `rg`
- searching sibling repos to discover bookmark storage or config
- brainstorming from scratch before checking local X bookmarks
- returning bookmark file paths without the direct X link from `canonical_url`
