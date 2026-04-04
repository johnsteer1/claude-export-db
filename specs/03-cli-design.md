# CLI Design

Built with [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) for output formatting.

The entrypoint is `claude-export-db` (configured in `pyproject.toml` as `claude_export_db.cli:app`).

## Commands

### `convert`

Parse the ZIP and write to the specified output format.

```
claude-export-db convert <zip_path> [OPTIONS]
```

**Arguments:**

| Arg | Required | Description |
|---|---|---|
| `zip_path` | yes | Path to the Anthropic export ZIP file |

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--output` | `-o` | `sqlite` | Output format: `sqlite`, `json`, `jsonl`, `markdown`, `parquet` |
| `--out` | | auto | Output path. Defaults: `brain.db` (sqlite), `export.json` (json), `export.jsonl` (jsonl), `./export/` (markdown), `export.parquet` (parquet) |
| `--overwrite` | | false | Overwrite existing output file/directory |
| `--no-thinking` | | false | Exclude `thinking` content blocks from output |
| `--quiet` | `-q` | false | Suppress progress output |

**Examples:**

```bash
# SQLite (default)
claude-export-db convert export.zip

# Specify output path
claude-export-db convert export.zip --out ~/brain.db

# JSON, pretty-printed
claude-export-db convert export.zip -o json --out export.json

# JSONL, one conversation per line
claude-export-db convert export.zip -o jsonl

# Markdown, one file per conversation
claude-export-db convert export.zip -o markdown --out ./conversations/

# Without thinking blocks
claude-export-db convert export.zip --no-thinking
```

**Progress output (Rich):**
The command should print a progress summary during conversion, e.g.:

```
Parsing export.zip...
  ✓ users.json       1 user
  ✓ projects.json    3 projects
  ✓ conversations.json  198 conversations, 1166 messages

Writing brain.db...
  ✓ Done in 0.4s
```

---

### `inspect`

Print stats about the export without converting it.

```
claude-export-db inspect <zip_path>
```

**Output:**

```
Export: export.zip (6.3 MB)

  Users         1
  Projects      3
  Conversations 198
  Messages      1,166
    human       589
    assistant   577

  Content blocks
    text        1,279
    tool_use      174
    tool_result   173
    thinking      118

  Date range    2024-07-20 → 2026-04-03
  Attachments   12 files across 8 messages
```

No options needed. Fails if the ZIP is invalid or missing expected files.

---

### `schema`

Print the SQLite DDL to stdout. Useful for reference or piping into another tool.

```
claude-export-db schema
```

No arguments. Always prints the full DDL for the SQLite output format.

---

## UX conventions

- Use Rich for all console output (tables, progress, errors)
- Errors print to stderr; data output (e.g. `schema`) prints to stdout
- Exit code 0 on success, 1 on any error
- Never print a Python traceback to the user — catch all expected errors and print a clean message
- If `--out` path already exists and `--overwrite` is not set, exit with a clear error: `Output path 'brain.db' already exists. Use --overwrite to replace it.`
- For `markdown` output, if `--out` directory does not exist, create it automatically
- All file paths accept both relative and absolute paths

## Module layout

```
src/claude_export_db/
    __init__.py         # __version__ only
    cli.py              # Typer app, all command definitions
    parser.py           # ZIP reading, JSON parsing, validation
    models.py           # Dataclasses/TypedDicts for all data structures
    writers/
        __init__.py
        sqlite.py       # SQLite writer
        json_.py        # JSON + JSONL writer
        markdown.py     # Markdown writer
        parquet.py      # Parquet writer (optional, behind import guard)
```

The `parser.py` module should be independent of output format — it returns Python dataclasses that any writer can consume. Writers receive the parsed data and handle their own I/O.
