from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from rich.console import Console

from claude_export_db.models import ExportData

logger = logging.getLogger(__name__)
console = Console(stderr=True)

SCHEMA_DDL = """\
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
    is_private          INTEGER NOT NULL DEFAULT 1,
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
    sender              TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    text                TEXT
);

CREATE TABLE content_blocks (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    message_uuid            TEXT NOT NULL REFERENCES messages(uuid),
    block_index             INTEGER NOT NULL,
    type                    TEXT NOT NULL,
    start_timestamp         TEXT,
    stop_timestamp          TEXT,
    text                    TEXT,
    citations_json          TEXT,
    thinking                TEXT,
    summaries_json          TEXT,
    cut_off                 INTEGER,
    truncated               INTEGER,
    signature               TEXT,
    tool_id                 TEXT,
    tool_name               TEXT,
    tool_input_json         TEXT,
    tool_use_id             TEXT,
    tool_result_content     TEXT,
    raw_json                TEXT
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

CREATE INDEX idx_messages_conversation ON messages(conversation_uuid);
CREATE INDEX idx_content_blocks_message ON content_blocks(message_uuid);
CREATE INDEX idx_content_blocks_type ON content_blocks(type);
CREATE INDEX idx_attachments_message ON attachments(message_uuid);
CREATE INDEX idx_files_message ON files(message_uuid);
CREATE INDEX idx_conversations_created ON conversations(created_at);
CREATE INDEX idx_messages_created ON messages(created_at);
"""


def _bool_to_int(value: bool | None) -> int | None:
    """Convert a Python bool to an SQLite-friendly 0/1 integer."""
    if value is None:
        return None
    return int(value)


def get_schema_ddl() -> str:
    """Return the full SQLite DDL as a string."""
    return SCHEMA_DDL


def write_sqlite(
    data: ExportData, output_path: Path, *, no_thinking: bool = False
) -> None:
    """Write parsed export data to a SQLite database at *output_path*."""
    # 1. Remove existing file (caller handles overwrite confirmation).
    if output_path.exists():
        output_path.unlink()

    # 2. Connect.
    conn = sqlite3.connect(str(output_path))
    try:
        cur = conn.cursor()

        # 3. Enable foreign keys.
        cur.execute("PRAGMA foreign_keys = ON")

        # 4. Create schema.
        cur.executescript(SCHEMA_DDL)

        # 5. Insert data in dependency order inside a single transaction.
        conn.execute("BEGIN")

        # --- users ---
        user_rows = [
            (u.uuid, u.full_name, u.email_address, u.verified_phone_number)
            for u in data.users
        ]
        _insert_many(
            cur,
            "INSERT INTO users (uuid, full_name, email_address, verified_phone_number) "
            "VALUES (?, ?, ?, ?)",
            user_rows,
            label="user",
        )

        # --- projects ---
        project_rows = [
            (
                p.uuid,
                p.name,
                p.description,
                _bool_to_int(p.is_private),
                _bool_to_int(p.is_starter_project),
                p.prompt_template,
                p.created_at,
                p.updated_at,
                p.creator_uuid,
            )
            for p in data.projects
        ]
        _insert_many(
            cur,
            "INSERT INTO projects "
            "(uuid, name, description, is_private, is_starter_project, "
            "prompt_template, created_at, updated_at, creator_uuid) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            project_rows,
            label="project",
        )

        # --- conversations & nested messages ---
        conv_rows = [
            (c.uuid, c.name, c.summary, c.created_at, c.updated_at, c.account_uuid)
            for c in data.conversations
        ]
        _insert_many(
            cur,
            "INSERT INTO conversations "
            "(uuid, name, summary, created_at, updated_at, account_uuid) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            conv_rows,
            label="conversation",
        )

        # --- messages ---
        msg_rows: list[tuple[str, str, str, str, str, str | None]] = []
        for conv in data.conversations:
            for msg in conv.messages:
                msg_rows.append(
                    (
                        msg.uuid,
                        conv.uuid,
                        msg.sender,
                        msg.created_at,
                        msg.updated_at,
                        msg.text,
                    )
                )
        _insert_many(
            cur,
            "INSERT INTO messages "
            "(uuid, conversation_uuid, sender, created_at, updated_at, text) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            msg_rows,
            label="message",
        )

        # --- content_blocks ---
        block_rows: list[tuple[object, ...]] = []
        for conv in data.conversations:
            for msg in conv.messages:
                for blk in msg.content_blocks:
                    if no_thinking and blk.type == "thinking":
                        continue
                    block_rows.append(
                        (
                            msg.uuid,
                            blk.block_index,
                            blk.type,
                            blk.start_timestamp,
                            blk.stop_timestamp,
                            blk.text,
                            blk.citations_json,
                            blk.thinking,
                            blk.summaries_json,
                            _bool_to_int(blk.cut_off),
                            _bool_to_int(blk.truncated),
                            blk.signature,
                            blk.tool_id,
                            blk.tool_name,
                            blk.tool_input_json,
                            blk.tool_use_id,
                            blk.tool_result_content,
                            blk.raw_json,
                        )
                    )
        cur.executemany(
            "INSERT INTO content_blocks "
            "(message_uuid, block_index, type, start_timestamp, stop_timestamp, "
            "text, citations_json, thinking, summaries_json, cut_off, truncated, "
            "signature, tool_id, tool_name, tool_input_json, tool_use_id, "
            "tool_result_content, raw_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            block_rows,
        )

        # --- attachments ---
        att_rows: list[tuple[str, str | None, int | None, str | None, str | None]] = []
        for conv in data.conversations:
            for msg in conv.messages:
                for att in msg.attachments:
                    att_rows.append(
                        (
                            msg.uuid,
                            att.file_name,
                            att.file_size,
                            att.file_type,
                            att.extracted_content,
                        )
                    )
        cur.executemany(
            "INSERT INTO attachments "
            "(message_uuid, file_name, file_size, file_type, extracted_content) "
            "VALUES (?, ?, ?, ?, ?)",
            att_rows,
        )

        # --- files ---
        file_rows: list[tuple[str, str | None]] = []
        for conv in data.conversations:
            for msg in conv.messages:
                for f in msg.files:
                    file_rows.append((msg.uuid, f.file_name))
        cur.executemany(
            "INSERT INTO files (message_uuid, file_name) VALUES (?, ?)",
            file_rows,
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _insert_many(
    cur: sqlite3.Cursor,
    sql: str,
    rows: list[tuple[object, ...]],
    *,
    label: str,
) -> None:
    """Insert rows one-by-one so duplicate-UUID failures can be logged and skipped."""
    for row in rows:
        try:
            cur.execute(sql, row)
        except sqlite3.IntegrityError as exc:
            console.print(
                f"[yellow]Warning:[/yellow] skipping duplicate {label}: {exc}"
            )
