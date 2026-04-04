# claude-export-db — Project Overview

## What this is

A CLI tool that converts the Anthropic account data export (a ZIP file downloadable from your [privacy settings](https://claude.ai/settings/privacy)) into queryable, structured formats.

The primary output is a normalized SQLite database. Secondary outputs are JSON, JSONL, Markdown, and Parquet.

## Origin & motivation

When you export your data from Anthropic, you get a ZIP with three JSON files:

```
users.json
projects.json
conversations.json
```

The only existing tool that targets this format — `claude-to-sqlite` by Simon Willison (Oct 2024) — is stale and has critical gaps against the current export schema:

- Ignores `content[]` blocks entirely (only reads the legacy flat `text` field)
- Drops all `thinking` blocks (extended reasoning content)
- Drops `tool_use` and `tool_result` blocks
- Ignores `projects.json` and `users.json`
- Stores attachments as opaque JSON blobs rather than normalized rows

This project was built specifically against an export downloaded **April 2026** and treats the `content[]` array as the source of truth.

## Goals

- Parse all three JSON files from the ZIP without extracting to disk
- Produce a fully normalized SQLite schema that preserves every field
- Support multiple output formats via a single `convert` command
- Surface useful stats via an `inspect` command (no conversion needed)
- Be installable with `uvx claude-export-db` — zero setup
- Fail loudly with clear error messages; never silently drop data

## Non-goals

- Building a UI or viewer (use [datasette](https://datasette.io/) on the SQLite output)
- Syncing live with the Claude API
- Supporting Claude Code's local JSONL format (`~/.claude/projects/`) — that's a different format entirely
- Inferring or enriching data beyond what's in the export
- Supporting exports older than mid-2024 (pre-`content[]` schema)
