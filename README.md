# bookmarks-cli

Local-first CLI for capturing and querying saved content in portable Markdown.

## Current workflow

X bookmarks are the first implemented source.

The current end-to-end workflow for X is:

1. Authenticate your X account locally with OAuth 2.0 PKCE
2. Run a one-time onboarding backfill of your existing bookmarks
3. Run incremental sync later to pull only newly bookmarked posts
4. Store each bookmarked post as a Markdown artifact with:
   - structured frontmatter
   - direct X post URL via `canonical_url`
   - raw payload snapshot
   - metadata that agents can parse and use

## Current implementation

- Structured saved-content artifacts stored as Markdown with YAML frontmatter
- Configurable output path via `BOOKMARKS_PATH` (`INFLUENCE_PATH` still works as a legacy fallback)
- Idempotent storage layout under your configured data path
- X bookmarks as the first implemented capture adapter
- One-time onboarding backfill plus incremental sync for X bookmarks
- Both API-based and file-based X ingest paths
- A shared artifact contract designed for additional saved-content sources later

## Repo layout

- `docs/` architecture, schema, and integration notes
- `integrations/` source-specific examples and contracts
- `processing/` bookmark-processing notes
- `prompts/` future LLM enrichment prompts
- `schemas/` machine-readable schema definitions
- `scripts/` thin local entrypoints
- `bookmarks_cli/` Python implementation
- `tests/` stdlib test coverage

## Data layout

By default the system writes outside the repo:

```text
~/bookmarks-data/
  x/
  _meta/
    raw/
    state/
```

Future sources can add sibling folders later. V1 only requires `x/` plus `_meta/`.

## Capture support model

- Use official APIs when they are available and reliable
- Keep file and export ingest as first-class fallback paths
- Let browser automation target the same normalized contract when an API is limited or unstable
- Keep the storage, enrichment, and query layers stable even if capture changes

## Quick start

1. Copy `.env.example` to `.env` and set `BOOKMARKS_PATH`.
2. Add your X app client ID to `.env`.
3. Initialize the output structure:

```bash
python3 -m bookmarks_cli init
```

4. Check configuration:

```bash
python3 -m bookmarks_cli doctor
```

5. Authenticate X API access:

```bash
python3 -m bookmarks_cli auth x-login
```

6. Run the one-time onboarding import for your existing X bookmarks:

```bash
python3 -m bookmarks_cli backfill x-bookmarks
```

7. Run incremental sync later to pull only new bookmarks:

```bash
python3 -m bookmarks_cli sync x-bookmarks
```

8. Optional: ingest bookmarks from a local JSON file instead of the API:

```bash
python3 -m bookmarks_cli ingest x-bookmarks --input integrations/x/samples/bookmarks.sample.json
```

9. Query stored X bookmarks locally:

```bash
python3 -m bookmarks_cli query x-bookmarks --text "codex agents" --limit 5
```

If `X_BOOKMARKS_INPUT_PATH` is set, `sync x-bookmarks` uses file mode. Otherwise the default is API mode.

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
python3 -m bookmarks_cli init
python3 -m bookmarks_cli doctor
python3 -m bookmarks_cli auth x-login
python3 -m bookmarks_cli auth x-status
python3 -m bookmarks_cli backfill x-bookmarks
python3 -m bookmarks_cli sync x-bookmarks
python3 -m bookmarks_cli rebuild x-bookmarks
python3 -m bookmarks_cli query x-bookmarks --text "agents" --limit 5
python3 -m bookmarks_cli sync x-bookmarks --source file --input path/to/bookmarks.json
python3 -m bookmarks_cli ingest x-bookmarks --input path/to/bookmarks.json
```

## Current design choices

- Capture first, classify later
- Markdown is the shared memory layer
- Obsidian is an optional interface, not a dependency
- Repo code and bookmark data stay separate
- Capture adapters are source-specific; the artifact contract is source-agnostic
- X bookmark ingestion is the current reference implementation for that contract, so API and browser/file fallback paths can share the same pipeline
- Every stored bookmark artifact must preserve a direct source link so agents can send you back to the original content

## CLI entrypoints

For humans in an interactive shell, `bookmarks-cli` is the friendly command.

For agents and automated runtimes, the canonical entrypoint is:

```bash
python3 -m bookmarks_cli sync x-bookmarks
```

Interactive-shell alternatives:

```bash
bookmarks-cli sync x-bookmarks
bash scripts/bookmarks-cli sync x-bookmarks
```

The `bookmarks-cli` command is also defined in [pyproject.toml](pyproject.toml). Installing it globally depends on your local Python packaging setup.

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
