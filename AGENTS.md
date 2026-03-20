# AGENTS.md

## Purpose

This repo powers a personal influence pipeline.

The primary active use case is X bookmarks:

- historical onboarding via `backfill x-bookmarks`
- incremental sync via `sync x-bookmarks`
- local retrieval over stored artifacts via `query x-bookmarks`

The durable memory layer lives outside the repo at `INFLUENCE_PATH`.

## CLI Rule

For agent execution, prefer the module entrypoint:

```bash
python3 -m personal_os ...
```

Do not assume `personal-os` is on `PATH` in every runtime.

`personal-os ...` is a convenience entrypoint for interactive shells when the user's local PATH has been configured correctly.

## Default Retrieval Workflow

When the user asks for:

- writing input
- content ideas
- research context
- examples
- worldview/theme synthesis
- "show me relevant X bookmarks"

agents should query the local influence store before brainstorming from scratch.

Default first step:

```bash
python3 -m personal_os query x-bookmarks --text "<topic>" --limit 10
```

If the query is broad or the result quality is mixed, follow with narrower passes:

```bash
python3 -m personal_os query x-bookmarks --tag "<tag>" --limit 10
python3 -m personal_os query x-bookmarks --theme "<theme>" --limit 10
python3 -m personal_os query x-bookmarks --person "@handle" --limit 10
python3 -m personal_os query x-bookmarks --author "<name-or-handle>" --limit 10
```

## Output Expectations

When returning relevant X bookmarks, prefer:

1. direct X links from `canonical_url`
2. short explanation of why each bookmark is relevant
3. concise synthesis of recurring ideas across the results

When helpful, include:

- title
- summary
- tags/themes
- file path to the stored artifact

## Freshness Rule

If the user wants the latest bookmarks, or asks to refresh/pull/sync first, run:

```bash
python3 -m personal_os sync x-bookmarks --source api
```

Then run the query workflow.

Do not run sync by default for every writing or research request. Query local artifacts first unless freshness is explicitly important.

## Rebuild Rule

If retrieval quality seems limited by old enrichment, regenerate Markdown from local raw payloads without re-fetching from X:

```bash
python3 -m personal_os rebuild x-bookmarks
```

## Example

For a prompt like:

> I want to write a new article and post on X around <topic>. Please show me X bookmarks that are relevant for this.

default workflow:

1. query local X bookmarks with the topic
2. return the most relevant direct X links
3. summarize patterns across the bookmarks
4. optionally propose angles for the article/X post based on the retrieved material
