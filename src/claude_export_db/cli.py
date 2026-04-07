from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from claude_export_db.parser import ExportError, parse_export
from claude_export_db.writers.json_ import write_json, write_jsonl
from claude_export_db.writers.markdown import write_markdown
from claude_export_db.writers.sqlite import get_schema_ddl, write_sqlite

app = typer.Typer(
    name="claude-export-db",
    help="Convert Anthropic Claude data exports into queryable databases and structured formats.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)

OUTPUT_FORMATS = ("sqlite", "json", "jsonl", "markdown", "parquet")

DEFAULT_PATHS: dict[str, str] = {
    "sqlite": "brain.db",
    "json": "export.json",
    "jsonl": "export.jsonl",
    "markdown": "./export/",
    "parquet": "export.parquet",
}


def _human_size(nbytes: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}" if unit != "B" else f"{nbytes} {unit}"
        nbytes /= 1024  # type: ignore[assignment]
    return f"{nbytes:.1f} TB"


@app.command()
def convert(
    zip_path: Annotated[
        Path, typer.Argument(help="Path to the Claude export ZIP file")
    ],
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output format: sqlite, json, jsonl, markdown, parquet",
        ),
    ] = "sqlite",
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Output path (auto-determined if not set)"),
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite existing output")
    ] = False,
    no_thinking: Annotated[
        bool, typer.Option("--no-thinking", help="Exclude thinking blocks")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Suppress progress output")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed warnings")
    ] = False,
) -> None:
    """Parse a Claude export ZIP and write it to the specified format."""
    if output not in OUTPUT_FORMATS:
        err_console.print(
            f"[red]Error:[/red] Unknown format '{output}'. Choose from: {', '.join(OUTPUT_FORMATS)}"
        )
        raise typer.Exit(code=1)

    # Determine output path
    output_path = out if out is not None else Path(DEFAULT_PATHS[output])

    # Check for existing output
    if output_path.exists() and not overwrite:
        err_console.print(
            f"[red]Error:[/red] Output already exists: {output_path}\n"
            f"  Use --overwrite to replace it."
        )
        raise typer.Exit(code=1)

    try:
        if not quiet:
            console.print(f"Parsing {zip_path.name}...")

        data = parse_export(zip_path, verbose=verbose)

        if not quiet:
            n_messages = sum(len(c.messages) for c in data.conversations)
            console.print(
                f"  [green]\u2713[/green] users.json       {len(data.users)} user(s)"
            )
            console.print(
                f"  [green]\u2713[/green] projects.json    {len(data.projects)} project(s)"
            )
            console.print(
                f"  [green]\u2713[/green] conversations.json  "
                f"{len(data.conversations)} conversations, {n_messages} messages"
            )

        if not quiet:
            console.print(f"Writing {output_path}...")

        if output == "sqlite":
            write_sqlite(data, output_path, no_thinking=no_thinking)
        elif output == "json":
            write_json(data, output_path, no_thinking=no_thinking)
        elif output == "jsonl":
            write_jsonl(data, output_path, no_thinking=no_thinking)
        elif output == "markdown":
            write_markdown(data, output_path, no_thinking=no_thinking)
        elif output == "parquet":
            from claude_export_db.writers.parquet import write_parquet

            write_parquet(data, output_path, no_thinking=no_thinking)

        if not quiet:
            console.print("  [green]\u2713[/green] Done")

        if data.warning_count > 0:
            console.print(f"Completed with {data.warning_count} warnings.")

    except ExportError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from None
    except KeyboardInterrupt:
        err_console.print("\n[yellow]Interrupted.[/yellow]")
        raise typer.Exit(code=1) from None


@app.command()
def inspect(
    zip_path: Annotated[
        Path, typer.Argument(help="Path to the Claude export ZIP file")
    ],
) -> None:
    """Parse a Claude export ZIP and print summary statistics."""
    try:
        data = parse_export(zip_path, verbose=False)
    except ExportError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from None
    except KeyboardInterrupt:
        err_console.print("\n[yellow]Interrupted.[/yellow]")
        raise typer.Exit(code=1) from None

    # Gather stats
    file_size = os.path.getsize(zip_path)
    n_users = len(data.users)
    n_projects = len(data.projects)
    n_conversations = len(data.conversations)

    all_messages = [m for c in data.conversations for m in c.messages]
    n_messages = len(all_messages)
    n_human = sum(1 for m in all_messages if m.sender == "human")
    n_assistant = sum(1 for m in all_messages if m.sender == "assistant")

    # Content block counts
    block_counts: dict[str, int] = {}
    for m in all_messages:
        for cb in m.content_blocks:
            block_counts[cb.type] = block_counts.get(cb.type, 0) + 1

    # Date range
    timestamps = [c.created_at for c in data.conversations if c.created_at]
    if timestamps:
        earliest = min(timestamps)[:10]
        latest = max(timestamps)[:10]
    else:
        earliest = "N/A"
        latest = "N/A"

    # Attachments
    attachment_messages = 0
    total_attachments = 0
    for m in all_messages:
        if m.attachments:
            attachment_messages += 1
            total_attachments += len(m.attachments)

    # Print
    console.print()
    console.print(f"[bold]Export:[/bold] {zip_path.name} ({_human_size(file_size)})")
    console.print()
    console.print(f"  Users         {n_users}")
    console.print(f"  Projects      {n_projects}")
    console.print(f"  Conversations {n_conversations}")
    console.print(f"  Messages      {n_messages}")
    console.print(f"    human       {n_human}")
    console.print(f"    assistant   {n_assistant}")
    console.print()
    console.print("  Content blocks")
    for btype in ("text", "tool_use", "tool_result", "thinking"):
        count = block_counts.get(btype, 0)
        console.print(f"    {btype:12s}  {count}")
    # Show any other block types
    for btype, count in sorted(block_counts.items()):
        if btype not in ("text", "tool_use", "tool_result", "thinking"):
            console.print(f"    {btype:12s}  {count}")
    console.print()
    console.print(f"  Date range    {earliest} \u2192 {latest}")
    console.print(
        f"  Attachments   {total_attachments} files across {attachment_messages} messages"
    )
    console.print()


@app.command()
def schema() -> None:
    """Print the SQLite schema DDL to stdout."""
    print(get_schema_ddl())
