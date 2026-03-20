# X Integration Contract

The X ingestion pipeline accepts either:

- a raw API response object with `data` and optional `includes.users`
- a JSON array of bookmark-like objects
- JSONL where each line is one bookmark-like object

Bookmark-like objects should include enough data to recover:

- `id`
- `text` or `full_text`
- `created_at`
- `author` or `author_id`
- optional entities, metrics, and bookmark timestamp

The sample file under [integrations/x/samples/bookmarks.sample.json](samples/bookmarks.sample.json) is a stable fallback input shape for manual import or browser automation output.
