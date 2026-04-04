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
claude-export-db convert export.zip --output sqlite --out brain.db
claude-export-db convert export.zip --output json --out brain.json
claude-export-db convert export.zip --output markdown --out ./docs
```

## Schema

The SQLite output uses a normalized schema:

```
users · projects · conversations · messages · content_blocks · attachments
```

`content_blocks` captures all message content types: `text`, `thinking`, `tool_use`, `tool_result`.

## Development

```bash
git clone https://github.com/johnsteer1/claude-export-db
cd claude-export-db
uv sync
uv run claude-export-db --help
```

## License

MIT
