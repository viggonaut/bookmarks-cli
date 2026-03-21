# Agent Retrieval Plan

## Goal

Make X bookmark retrieval feel native inside Codex and Claude sessions, even when the active repo is not `bookmarks-cli`.

Success looks like this:

- the agent knows to check X bookmarks before brainstorming
- the tool is callable without workspace spelunking
- natural-language requests return relevant posts without brittle exact-phrase matching
- results include direct X links and a short explanation of relevance

## Current State

The core retrieval path now exists:

- `search x-bookmarks` for natural-language retrieval
- `query x-bookmarks` for exact field control
- tokenized and weighted text matching
- typo-tolerant matching for near-miss tokens
- source-aware search for requests like `from OpenAI`
- date-bounded retrieval via `--date-from`, `--date-to`, and `--days`
- richer JSON output with `authors`, `matched_fields`, `matched_terms`, `matched_queries`, and `why_relevant`

## Remaining Gaps

### 1. Discoverability is repo-local

The workflow is documented well inside this repo, but agents in other repos may still:

- search for a sibling `bookmarks-cli` checkout
- inspect `.env` files to infer `BOOKMARKS_PATH`
- grep the archive directly instead of using the supported CLI

### 2. Search ranking is still heuristic

The current search path is materially better than exact substring matching, but it still relies on:

- token overlap
- small synonym expansions
- author and date constraints
- weighted field ranking

That means some results can still be noisy for broader conceptual searches.

### 3. Agents still decide when to broaden

The CLI now handles much more internally, but there is still a product decision boundary between:

- strict source search
- broader mention-only search
- file inspection for ambiguous results

That boundary should stay clear in agent guidance.

## Recommended Stack

### 1. Cross-repo instruction snippet

Keep a short shared block in `AGENTS.md` and `CLAUDE.md` across active repos:

- query local X bookmarks before brainstorming
- prefer `python3 -m bookmarks_cli search x-bookmarks --format json`
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

### 4. Better ranking and explanation

The next retrieval improvements should focus on quality rather than basic capability:

- better semantic expansion for product names and adjacent concepts
- stronger penalties for broad partial matches
- short matched excerpts in output
- clearer separation between direct-source hits and mention-only hits

### 5. Keep the higher-level search command as the default

The intended natural-language entrypoint is now:

```bash
python3 -m bookmarks_cli search x-bookmarks --query "AI companions Josh Puckett" --limit 10 --format json
```

Current internal strategy:

1. parse likely people and author terms
2. run weighted text retrieval
3. apply explicit or inferred author/person constraints
4. expand candidate themes and adjacent terms
5. merge and rank results

This removes prompt-specific orchestration from agents.

### 6. Richer agent-facing output

Extend JSON output with fields that help agents explain results:

- `authors`
- `matched_fields`
- `matched_terms`
- `matched_queries`
- `why_relevant`
- short excerpt or top matching sentence

The goal is to let the agent answer directly from CLI output instead of opening many files.

## Implementation Phases

### Phase 1: Workflow hardening

- keep the shared instruction snippet in sync across `AGENTS.md` and `CLAUDE.md`
- prefer JSON output in all agent examples
- add explicit anti-pattern guidance

### Phase 2: Retrieval quality

- improve semantic expansion quality
- add matched excerpts
- separate direct-source hits from mention-only hits more explicitly
- add tests for broader real-world query shapes

### Phase 3: One-shot agent UX

- keep `search x-bookmarks` as the default path in all repo instructions
- optionally package the retrieval workflow as a reusable skill
- add a broader/narrower retry mode if user intent requires it

## Next Concrete Code Changes

If implementing next, the highest-leverage sequence is:

1. add matched excerpts or best matching sentence to JSON output
2. add clearer direct-source vs mention-only markers
3. tighten ranking for broad expansion matches
4. package the retrieval workflow into a reusable skill or shared global instruction
