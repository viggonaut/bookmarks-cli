# Processing Layer

V1 keeps processing deliberately lightweight.

## Current steps

1. Clean source text
2. Build a short summary
3. Extract a few key ideas
4. Generate lightweight tags and themes
5. Persist both raw payload and structured Markdown bookmark artifacts

## Current enrichment strategy

The code uses deterministic heuristics so the pipeline works with no external dependencies.

That is good enough for v1 because the harder part is establishing:

- the storage contract
- the source normalization layer
- idempotent sync behavior

## Planned upgrades

- LLM-based summaries and tagging
- richer entity extraction
- embeddings and semantic retrieval
- cross-item rollups for people, themes, and concepts
