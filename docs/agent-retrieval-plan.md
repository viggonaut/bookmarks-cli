# Agent Retrieval Plan

## Goal

Make X bookmark retrieval feel native inside Codex and Claude sessions, even when the active repo is not `bookmarks-cli`.

Success looks like this:

- the agent knows to check X bookmarks before brainstorming
- the tool is callable without workspace spelunking
- natural-language requests return relevant posts without brittle exact-phrase matching
- results include direct X links and a short explanation of relevance

## Current Gaps

### 1. Discoverability is repo-local

The workflow is documented well inside this repo, but agents in other repos may still:

- search for a sibling `bookmarks-cli` checkout
- inspect `.env` files to infer `BOOKMARKS_PATH`
- grep the archive directly instead of using the supported CLI

### 2. Query behavior is too literal

The current query path does:

- exact substring matching for `--text`
- exact filters for `--tag`, `--theme`, and `--person`
- author substring matching
- recency sorting only

That makes prompts like `AI companions`, `AI companies`, `AI character apps`, or `something Josh Puckett posted` fragile unless the exact words appear in stored text or enrichment.

### 3. Agents still have to orchestrate retries manually

Today the agent has to decide when to retry with:

- `--author`
- `--person`
- `--theme`
- `--tag`
- `rebuild x-bookmarks`

That creates inconsistent behavior across sessions and tools.

## Recommended Stack

### 1. Cross-repo instruction snippet

Keep a short shared block in `AGENTS.md` and `CLAUDE.md` across active repos:

- query local X bookmarks before brainstorming
- prefer `python3 -m bookmarks_cli query x-bookmarks --format json`
- use `doctor` if availability or archive path is unclear
- only run `sync` when freshness is requested
- run `rebuild` before direct archive inspection
- return `canonical_url` plus a short why-relevant note

This should stay short and be copied from one maintained source.

### 2. Global tool availability

Make `bookmarks_cli` callable from any repo without relying on cwd:

- install the package once in a shared Python environment
- keep `BOOKMARKS_PATH` available in the shell environment
- treat `python3 -m bookmarks_cli doctor` as the first diagnostic step

This removes the need for agents to discover the repo layout just to ask a bookmark question.

### 3. Shared skill or tool integration

A reusable skill or tool should encode the retrieval workflow once for agent environments:

- Codex: install a local skill for X bookmark retrieval
- Claude: add the equivalent global instruction or tool integration

Repo-local markdown should point to the workflow, not carry the full logic everywhere.

### 4. Stronger query semantics

Upgrade `query x-bookmarks` so natural-language requests degrade gracefully:

- tokenize text queries instead of requiring one exact substring
- score title, summary, key ideas, authors, people, themes, and body separately
- boost exact author and handle matches
- support alias and synonym expansion
- expose matched fields in results

Suggested scoring order:

1. exact author and handle matches
2. title, summary, and key ideas
3. themes, tags, and people
4. body text
5. recency as a tiebreaker

### 5. Higher-level search command

Add a command that performs the retry strategy internally, for example:

```bash
python3 -m bookmarks_cli search x-bookmarks --query "AI companions Josh Puckett" --limit 10 --format json
```

Possible internal strategy:

1. parse likely people and author terms
2. run weighted text retrieval
3. retry with extracted author and person filters
4. expand candidate themes and tags
5. merge and rank results

This removes prompt-specific orchestration from agents.

### 6. Richer agent-facing output

Extend JSON output with fields that help agents explain results:

- `matched_fields`
- `matched_terms`
- `why_relevant`
- short excerpt or top matching sentence

The goal is to let the agent answer directly from CLI output instead of opening many files.

## Implementation Phases

### Phase 1: Workflow hardening

- keep the shared instruction snippet in sync across `AGENTS.md` and `CLAUDE.md`
- prefer JSON output in all agent examples
- add explicit anti-pattern guidance

### Phase 2: Retrieval quality

- replace exact substring matching with tokenized scoring
- add author and people weighting
- add matched-field reporting
- add tests for paraphrase-style queries

### Phase 3: One-shot agent UX

- add a higher-level `search x-bookmarks` command
- optionally package the retrieval workflow as a reusable skill

## First Concrete Code Changes

If implementing next, the highest-leverage sequence is:

1. refactor `query_items` to return scored matches plus matched fields
2. update `--format json` payload to include those fields
3. add tests for paraphrase and author-led queries
4. add a `search x-bookmarks` command that wraps the fallback sequence
