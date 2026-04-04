# Testing

## Setup

Tests live in `tests/`. Run with:

```bash
uv run pytest
uv run pytest -v              # verbose
uv run pytest --cov           # with coverage
```

## Fixtures

Create a `tests/conftest.py` with reusable fixtures.

### `sample_zip` fixture

Build a minimal in-memory ZIP for testing without requiring the real export file:

```python
import io
import json
import zipfile
import pytest

SAMPLE_USERS = [{"uuid": "user-1", "full_name": "Test User", "email_address": "test@example.com", "verified_phone_number": None}]
SAMPLE_PROJECTS = []
SAMPLE_CONVERSATIONS = [
    {
        "uuid": "conv-1",
        "name": "Test Conversation",
        "summary": "",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:01:00Z",
        "account": {"uuid": "user-1"},
        "chat_messages": [
            {
                "uuid": "msg-1",
                "text": "Hello",
                "sender": "human",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "content": [
                    {"type": "text", "text": "Hello", "citations": [], "start_timestamp": "2024-01-01T00:00:00Z", "stop_timestamp": "2024-01-01T00:00:01Z", "flags": None, "alternative_display_type": None}
                ],
                "attachments": [],
                "files": []
            },
            {
                "uuid": "msg-2",
                "text": "Hi there",
                "sender": "assistant",
                "created_at": "2024-01-01T00:00:05Z",
                "updated_at": "2024-01-01T00:00:05Z",
                "content": [
                    {"type": "thinking", "thinking": "User said hello", "summaries": [{"summary": "greeting"}], "cut_off": False, "truncated": False, "signature": "abc123", "start_timestamp": "2024-01-01T00:00:04Z", "stop_timestamp": "2024-01-01T00:00:05Z", "flags": None, "alternative_display_type": None},
                    {"type": "text", "text": "Hi there", "citations": [], "start_timestamp": "2024-01-01T00:00:05Z", "stop_timestamp": "2024-01-01T00:00:06Z", "flags": None, "alternative_display_type": None}
                ],
                "attachments": [],
                "files": []
            }
        ]
    }
]

@pytest.fixture
def sample_zip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("users.json", json.dumps(SAMPLE_USERS))
        zf.writestr("projects.json", json.dumps(SAMPLE_PROJECTS))
        zf.writestr("conversations.json", json.dumps(SAMPLE_CONVERSATIONS))
    buf.seek(0)
    path = tmp_path / "test-export.zip"
    path.write_bytes(buf.read())
    return path
```

## Test cases

### Parser (`tests/test_parser.py`)

- `test_parse_valid_zip` — parses the sample ZIP without error; returns expected counts
- `test_parse_missing_conversations_json` — raises appropriate error
- `test_parse_missing_users_json` — raises appropriate error
- `test_parse_not_a_zip` — raises appropriate error when given a non-ZIP file
- `test_parse_content_blocks_text` — text blocks parsed with correct fields
- `test_parse_content_blocks_thinking` — thinking blocks parsed with `thinking`, `cut_off`, `truncated`, `signature`
- `test_parse_content_blocks_tool_use` — `tool_id`, `tool_name`, `tool_input_json` populated
- `test_parse_content_blocks_tool_result` — `tool_use_id`, `tool_result_content` populated
- `test_parse_message_missing_content_falls_back_to_text` — if `content` key absent, synthesize from `text`
- `test_parse_unknown_content_block_type` — warns but does not raise
- `test_parse_attachments` — attachment fields populated correctly
- `test_parse_empty_projects` — empty `projects.json` array handled without error

### SQLite writer (`tests/test_writer_sqlite.py`)

- `test_sqlite_creates_all_tables` — verify schema matches expected DDL
- `test_sqlite_row_counts` — after import, each table has expected row counts
- `test_sqlite_conversation_roundtrip` — query a conversation back; name/uuid/created_at match
- `test_sqlite_content_block_order` — `block_index` is sequential within a message
- `test_sqlite_thinking_block_fields` — `thinking`, `summaries_json`, `signature` columns populated
- `test_sqlite_no_thinking_flag` — thinking blocks excluded when `--no-thinking` passed
- `test_sqlite_foreign_keys_enforced` — verify FK pragma is on
- `test_sqlite_overwrite_flag` — errors if output exists and `--overwrite` not set; succeeds with flag

### JSON writer (`tests/test_writer_json.py`)

- `test_json_valid_output` — output is parseable JSON
- `test_json_nested_structure` — conversations contain messages contain content_blocks
- `test_jsonl_one_line_per_conversation` — output has N lines for N conversations
- `test_jsonl_each_line_valid_json` — each line parses independently

### Markdown writer (`tests/test_writer_markdown.py`)

- `test_markdown_creates_directory` — output directory is created if absent
- `test_markdown_file_per_conversation` — one file per conversation
- `test_markdown_filename_format` — `YYYY-MM-DD_slug.md`
- `test_markdown_slug_collision` — duplicate slugs get `_2` suffix
- `test_markdown_thinking_included_by_default` — thinking rendered as blockquote
- `test_markdown_no_thinking_flag` — thinking omitted when flag set

### CLI integration (`tests/test_cli.py`)

Use `typer.testing.CliRunner` for all CLI tests.

- `test_convert_default_output` — `convert sample.zip` creates `brain.db`
- `test_convert_output_formats` — each `-o` value produces expected file/directory
- `test_inspect_output` — `inspect` prints expected stats
- `test_schema_output` — `schema` prints DDL to stdout
- `test_error_nonexistent_zip` — exits 1 with clean message
- `test_error_output_exists_no_overwrite` — exits 1 with clean message
- `test_error_output_exists_with_overwrite` — succeeds

## Coverage target

Aim for 80%+ overall. The parser and SQLite writer should have 90%+ coverage as they are the core logic.
