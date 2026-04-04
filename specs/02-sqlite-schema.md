# SQLite Schema

The target normalized schema. All tables use `TEXT` for UUIDs and ISO 8601 timestamps. Foreign keys should be enforced (`PRAGMA foreign_keys = ON`).

## DDL

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE users (
    uuid                    TEXT PRIMARY KEY,
    full_name               TEXT,
    email_address           TEXT,
    verified_phone_number   TEXT
);

CREATE TABLE projects (
    uuid                TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    is_private          INTEGER NOT NULL DEFAULT 1,  -- BOOLEAN (0/1)
    is_starter_project  INTEGER NOT NULL DEFAULT 0,
    prompt_template     TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    creator_uuid        TEXT REFERENCES users(uuid)
);

CREATE TABLE conversations (
    uuid            TEXT PRIMARY KEY,
    name            TEXT,
    summary         TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    account_uuid    TEXT REFERENCES users(uuid)
);

CREATE TABLE messages (
    uuid                TEXT PRIMARY KEY,
    conversation_uuid   TEXT NOT NULL REFERENCES conversations(uuid),
    sender              TEXT NOT NULL,  -- 'human' | 'assistant'
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    text                TEXT            -- legacy flat-text field; preserved but not primary
);

CREATE TABLE content_blocks (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    message_uuid            TEXT NOT NULL REFERENCES messages(uuid),
    block_index             INTEGER NOT NULL,  -- position within message content[]
    type                    TEXT NOT NULL,     -- 'text' | 'thinking' | 'tool_use' | 'tool_result'
    start_timestamp         TEXT,
    stop_timestamp          TEXT,

    -- type = 'text'
    text                    TEXT,
    citations_json          TEXT,              -- raw JSON array; [] in current exports

    -- type = 'thinking'
    thinking                TEXT,
    summaries_json          TEXT,              -- raw JSON array of {summary: string}
    cut_off                 INTEGER,           -- BOOLEAN
    truncated               INTEGER,           -- BOOLEAN
    signature               TEXT,

    -- type = 'tool_use'
    tool_id                 TEXT,              -- matches tool_result.tool_use_id
    tool_name               TEXT,
    tool_input_json         TEXT,              -- raw JSON object

    -- type = 'tool_result'
    tool_use_id             TEXT,              -- FK → content_blocks.tool_id (logical, not enforced)
    tool_result_content     TEXT               -- string or serialized JSON
);

CREATE TABLE attachments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    message_uuid        TEXT NOT NULL REFERENCES messages(uuid),
    file_name           TEXT,
    file_size           INTEGER,
    file_type           TEXT,
    extracted_content   TEXT
);

CREATE TABLE files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    message_uuid    TEXT NOT NULL REFERENCES messages(uuid),
    file_name       TEXT
);
```

## Indexes

```sql
CREATE INDEX idx_messages_conversation ON messages(conversation_uuid);
CREATE INDEX idx_content_blocks_message ON content_blocks(message_uuid);
CREATE INDEX idx_content_blocks_type ON content_blocks(type);
CREATE INDEX idx_attachments_message ON attachments(message_uuid);
CREATE INDEX idx_files_message ON files(message_uuid);
CREATE INDEX idx_conversations_created ON conversations(created_at);
CREATE INDEX idx_messages_created ON messages(created_at);
```

## Design decisions

**Why store `messages.text`?**
The `text` field is a legacy denormalized copy of message content. It's preserved for compatibility and as a fallback, but `content_blocks` is the authoritative source. Consumers should query `content_blocks` where `type = 'text'` to get actual message text.

**Why not split `content_blocks` into per-type tables?**
The union of fields across all types is small enough that a single table with nullable type-specific columns is more practical than 4 tables with complex joins. The `type` column makes filtering straightforward.

**Why serialize `tool_input_json` as TEXT?**
Tool inputs are tool-specific and variable in shape. Serialized JSON keeps the schema stable while still allowing `json_extract()` queries in SQLite.

**Why no `project_uuid` on conversations?**
The export does not link conversations to projects. There is no foreign key to add.

## Useful queries

```sql
-- Full conversation with all content blocks
SELECT
    c.name,
    m.sender,
    cb.type,
    cb.text,
    cb.thinking,
    cb.tool_name
FROM conversations c
JOIN messages m ON m.conversation_uuid = c.uuid
JOIN content_blocks cb ON cb.message_uuid = m.uuid
WHERE c.uuid = '...'
ORDER BY m.created_at, cb.block_index;

-- All thinking blocks
SELECT m.created_at, cb.thinking
FROM content_blocks cb
JOIN messages m ON m.uuid = cb.message_uuid
WHERE cb.type = 'thinking'
ORDER BY m.created_at;

-- Conversation count by month
SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) AS convos
FROM conversations
GROUP BY month
ORDER BY month;

-- All tools used
SELECT tool_name, COUNT(*) AS uses
FROM content_blocks
WHERE type = 'tool_use'
GROUP BY tool_name
ORDER BY uses DESC;
```
