# personal-os

Personal influence pipeline for capturing X bookmarks and other external content into agent-usable Markdown.

`personal-os` is the code and automation layer for a personal influence pipeline. It captures external content, enriches it into agent-usable structure, and writes portable Markdown artifacts into a separate data directory, typically `~/personal-influence/`.

## Main use case right now

V1 is centered on X bookmarks.

The current end-to-end workflow is:

1. Authenticate your X account locally with OAuth 2.0 PKCE
2. Run a one-time onboarding backfill of your existing bookmarks
3. Run incremental sync later to pull only newly bookmarked posts
4. Store each bookmarked post as a Markdown artifact with:
   - structured frontmatter
   - direct X post URL via `canonical_url`
   - raw payload snapshot
   - metadata that agents can parse and use

## V1 scope

- Structured influence artifacts stored as Markdown with YAML frontmatter
- Configurable output path via `INFLUENCE_PATH`
- Idempotent storage layout under `~/personal-influence/`
- First ingestion path for X bookmarks
- One-time onboarding backfill plus incremental sync for X bookmarks
- Both API-based and file-based X ingest paths
- Clear extension points for podcasts, articles, embeddings, and richer enrichment

## Repo layout

- `docs/` architecture, schema, and integration notes
- `integrations/` source-specific examples and contracts
- `processing/` processing-layer notes
- `prompts/` future LLM enrichment prompts
- `schemas/` machine-readable schema definitions
- `scripts/` thin local entrypoints
- `personal_os/` Python implementation
- `tests/` stdlib test coverage

## Data layout

By default the system writes outside the repo:

```text
~/personal-influence/
  x/
  podcasts/
  articles/
  concepts/
  people/
  themes/
  daily/
  _meta/
    raw/
    state/
```

## Quick start

1. Copy `.env.example` to `.env` and set `INFLUENCE_PATH`.
2. Add your X app client ID to `.env`.
3. Initialize the output structure:

```bash
python3 -m personal_os init
```

4. Check configuration:

```bash
python3 -m personal_os doctor
```

5. Authenticate X API access:

```bash
python3 -m personal_os auth x-login
```

6. Run the one-time onboarding import for your existing X bookmarks:

```bash
python3 -m personal_os backfill x-bookmarks
```

7. Run incremental sync later to pull only new bookmarks:

```bash
python3 -m personal_os sync x-bookmarks
```

8. Optional: ingest bookmarks from a local JSON file instead of the API:

```bash
python3 -m personal_os ingest x-bookmarks --input integrations/x/samples/bookmarks.sample.json
```

9. Query stored X bookmarks locally:

```bash
python3 -m personal_os query x-bookmarks --text "codex agents" --limit 5
```

If `X_BOOKMARKS_INPUT_PATH` is set, `sync x-bookmarks` uses file mode. If local X OAuth state is available, it uses API mode.

## X Bookmark Flow

Use this operational split:

- `backfill x-bookmarks`
  - one-time onboarding import for all existing bookmarks
- `sync x-bookmarks`
  - incremental pull for newly bookmarked posts
- `ingest x-bookmarks`
  - manual file import into the same storage contract

The X storage contract is:

- one Markdown file per bookmarked post under `x/YYYY/MM/DD/<post_id>.md`
- one raw payload snapshot under `_meta/raw/x/YYYY/MM/DD/<post_id>.json`
- direct source link stored as `canonical_url`
- sync state under `_meta/state/`
- local query over stored artifacts via `query x-bookmarks`

## Core commands

```bash
python3 -m personal_os init
python3 -m personal_os doctor
python3 -m personal_os auth x-login
python3 -m personal_os auth x-status
python3 -m personal_os backfill x-bookmarks
python3 -m personal_os sync x-bookmarks
python3 -m personal_os rebuild x-bookmarks
python3 -m personal_os query x-bookmarks --text "agents" --limit 5
python3 -m personal_os sync x-bookmarks --source file --input path/to/bookmarks.json
python3 -m personal_os ingest x-bookmarks --input path/to/bookmarks.json
```

## Current design choices

- Capture first, classify later
- Markdown is the shared memory layer
- Obsidian is an optional interface, not a dependency
- Repo code and personal influence data stay separate
- X bookmark ingestion is built around a stable normalized contract so API and browser/file fallback paths can share the same pipeline
- Every stored influence item must preserve a direct source link so agents can send you back to the original content

## CLI entrypoints

For humans in an interactive shell, `personal-os` is the friendly command.

For agents and automated runtimes, the canonical entrypoint is:

```bash
python3 -m personal_os sync x-bookmarks
```

Interactive-shell alternatives:

```bash
personal-os sync x-bookmarks
bash scripts/personal-os sync x-bookmarks
```

The `personal-os` command is also defined in [pyproject.toml](pyproject.toml). Installing it globally depends on your local Python packaging setup.

If you install it with:

```bash
python3 -m pip install --user .
```

you may also need to add your Python user bin directory to `PATH`, for example:

```bash
export PATH="$(python3 -m site --user-base)/bin:$PATH"
```

See:

- [docs/architecture.md](docs/architecture.md)
- [docs/schema.md](docs/schema.md)
- [docs/x-auth.md](docs/x-auth.md)
- [docs/x-bookmarks.md](docs/x-bookmarks.md)
- [docs/query.md](docs/query.md)
