# Output Formats

## SQLite (primary)

See [02-sqlite-schema.md](02-sqlite-schema.md) for the full schema.

The writer should:
1. Create the output `.db` file
2. Execute `PRAGMA foreign_keys = ON`
3. Create all tables and indexes
4. Insert rows in dependency order: `users` → `projects` → `conversations` → `messages` → `content_blocks` → `attachments` → `files`
5. Use a single transaction for the full import (fast, atomic)

Use Python's built-in `sqlite3` module — no ORM needed.

---

## JSON

A single JSON file. Structure mirrors the normalized SQLite schema as a top-level object with each table as a key:

```json
{
  "users": [ { "uuid": "...", "full_name": "...", ... } ],
  "projects": [ { ... } ],
  "conversations": [
    {
      "uuid": "...",
      "name": "...",
      "messages": [
        {
          "uuid": "...",
          "sender": "human",
          "content_blocks": [ { "type": "text", "text": "..." } ],
          "attachments": [],
          "files": []
        }
      ]
    }
  ]
}
```

Conversations embed their messages; messages embed their content blocks, attachments, and files. This nested structure is more useful for LLM ingestion than the flat relational form.

Write with `json.dump(..., ensure_ascii=False, indent=2)` by default. `indent=None` for compact output (not currently a CLI flag, but keep it easy to add).

---

## JSONL

One JSON object per line. Each line is a complete conversation with embedded messages (same nested structure as the JSON format, but per conversation).

```jsonl
{"uuid": "...", "name": "...", "messages": [...]}
{"uuid": "...", "name": "...", "messages": [...]}
```

Useful for streaming, vector DB ingestion, and LLM batch processing. No trailing newline issues — standard JSONL.

---

## Markdown

One `.md` file per conversation, written to a directory. Filename format:

```
{YYYY-MM-DD}_{slugified-conversation-name}.md
```

Example: `2024-07-30_python-script-evaluate-file-sizes.md`

Slug rules: lowercase, replace spaces and special chars with `-`, collapse multiple `-`, max 80 chars.

If two conversations produce the same slug+date, append `_2`, `_3`, etc.

### File format

```markdown
# Python Script to Evaluate Total File Size

**Date:** 2024-07-30
**Updated:** 2024-08-01
**Messages:** 6

---

**Human** · 2024-07-30 16:06

You are assuming the role as a python automation expert...

---

**Assistant** · 2024-07-30 16:06

Here is the Python script...

```python
import os
...
```

---

**Assistant** · 2024-07-30 16:06 · _thinking_

> The user wants a script that...

---
```

Content block rendering rules:
- `text` blocks: render as-is (already Markdown in most cases)
- `thinking` blocks: render as a blockquote prefixed with `_thinking_` label — only if `--no-thinking` is not set
- `tool_use` blocks: render as a fenced code block with the tool name as a label
- `tool_result` blocks: render as a fenced code block labeled `output`
- Multiple content blocks in one message are rendered sequentially with no separator

---

## Parquet

Flat columnar export. Requires `pyarrow` — should be a soft dependency with a helpful error if not installed:

```
Parquet output requires pyarrow. Install it with:
  uv add pyarrow
  # or: pip install pyarrow
```

Write one Parquet file with a flattened `messages` table that includes key conversation fields as columns (denormalized for analytics convenience):

| Column | Source |
|---|---|
| `conversation_uuid` | conversations.uuid |
| `conversation_name` | conversations.name |
| `conversation_created_at` | conversations.created_at |
| `message_uuid` | messages.uuid |
| `sender` | messages.sender |
| `message_created_at` | messages.created_at |
| `text` | concatenated text from `text`-type content blocks |
| `has_thinking` | bool — whether message has any thinking blocks |
| `has_tool_use` | bool |
| `attachment_count` | int |

This format is intentionally denormalized for use with pandas/polars/DuckDB.
