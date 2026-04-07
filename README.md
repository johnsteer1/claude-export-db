# claude-export-db

CLI tool that converts your [Anthropic data export](https://support.anthropic.com/en/articles/9450526-how-can-i-export-my-claude-ai-data) into queryable formats.

## Why

The official export is a ZIP with three JSON files. This tool loads it into SQLite (or JSON/Parquet/Markdown) with a normalized schema that preserves everything — including `thinking` blocks, tool calls, attachments, and projects — which existing tools miss.

## Install

```bash
uvx claude-export-db
```

## Usage

```bash
# SQLite (default) — outputs brain.db
claude-export-db convert export.zip

# Other formats
claude-export-db convert export.zip -o json
claude-export-db convert export.zip -o jsonl
claude-export-db convert export.zip -o markdown
claude-export-db convert export.zip -o parquet

# Custom output path, exclude thinking blocks
claude-export-db convert export.zip --out ~/brain.db --no-thinking

# Stats without converting
claude-export-db inspect export.zip

# Print SQLite DDL
claude-export-db schema
```

## Schema

Normalized SQLite with full content block support:

```
users · projects · conversations · messages · content_blocks · attachments · files
```

`content_blocks` captures `text`, `thinking`, `tool_use`, and `tool_result` — nothing is dropped.

## Development

```bash
git clone https://github.com/johnsteer1/claude-export-db
cd claude-export-db
uv sync
uv run claude-export-db --help
```

## License

MIT
