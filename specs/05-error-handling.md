# Error Handling

All errors should print a clean message to stderr and exit with code 1. No raw Python tracebacks should reach the user.

## Input validation

### ZIP file

| Condition | Error message |
|---|---|
| Path does not exist | `File not found: {path}` |
| Not a valid ZIP | `Not a valid ZIP file: {path}` |
| Missing `conversations.json` | `Invalid export: conversations.json not found in ZIP` |
| Missing `users.json` | `Invalid export: users.json not found in ZIP` |
| Missing `projects.json` | `Invalid export: projects.json not found in ZIP` |
| ZIP is password-protected | `ZIP file is password-protected — cannot read` |

### JSON parsing

| Condition | Behavior |
|---|---|
| `conversations.json` is not valid JSON | Fatal error: `Failed to parse conversations.json: {detail}` |
| `users.json` is not valid JSON | Fatal error: `Failed to parse users.json: {detail}` |
| `projects.json` is not valid JSON | Fatal error: `Failed to parse projects.json: {detail}` |
| Top-level is not an array | Fatal error: `Unexpected format in {filename}: expected array, got {type}` |

### Per-record validation

The parser should be tolerant of missing optional fields but strict about required ones.

**Required fields** (missing → skip record + print warning):

| Record | Required fields |
|---|---|
| conversation | `uuid`, `created_at`, `chat_messages` |
| message | `uuid`, `sender`, `created_at` |
| content_block | `type` |

**Optional fields** (missing → use `None` / empty):

Everything else. If `content` is missing on a message, fall back to the legacy `text` field and synthesize a single `text`-type content block.

**Unknown content block type:**
Log a warning and store the raw block as JSON in a `raw_json` column (add this column to `content_blocks` if needed). Do not silently discard.

```
Warning: unknown content block type 'image' in message {uuid} — storing raw
```

## Output validation

| Condition | Error message |
|---|---|
| Output path exists, `--overwrite` not set | `Output path '{path}' already exists. Use --overwrite to replace it.` |
| Cannot write to output path (permissions) | `Cannot write to '{path}': permission denied` |
| Disk full during write | `Write failed: no space left on device` |
| `parquet` output but `pyarrow` not installed | `Parquet output requires pyarrow.\n  Install it with: uv add pyarrow` |

## SQLite-specific

- If an INSERT fails due to a duplicate UUID, log the UUID and skip the record (do not abort the full import).
- If `PRAGMA foreign_keys = ON` and a FK violation occurs, log the offending record and continue — do not abort. This can happen if a message references a conversation UUID that was skipped due to earlier validation failure.

## Warning vs. fatal

**Fatal (exit 1):** Can't read the ZIP, can't parse a top-level JSON file, can't write to the output path.

**Warning (continue):** Individual records missing required fields, unknown content block types, duplicate UUIDs, FK violations. Warnings print to stderr in amber using Rich: `⚠ {message}`.

At the end of a successful run with warnings, print a summary:

```
Completed with 3 warnings. Run with --verbose to see details.
```

## `--verbose` flag

When passed to `convert`, print each warning inline as it occurs rather than buffering them. Also prints per-table row counts after import.
