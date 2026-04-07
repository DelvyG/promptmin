"""PromptMin CLI."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional
import typer

from .engine import minify
from .tokens import savings

app = typer.Typer(
    add_completion=False,
    help="Minify LLM prompts to save tokens.",
    no_args_is_help=True,
)


def _read_input(text: Optional[str], file: Optional[Path], clipboard: bool) -> str:
    if clipboard:
        import pyperclip
        return pyperclip.paste()
    if file:
        return file.read_text(encoding="utf-8")
    if text:
        return text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise typer.BadParameter("Provide TEXT, --file, --clipboard, or stdin.")


@app.command()
def run(
    text: Optional[str] = typer.Argument(None, help="Prompt text (or use --file/--clipboard/stdin)."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", exists=True, help="Read prompt from file."),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="Read prompt from clipboard."),
    out_clipboard: bool = typer.Option(False, "--out-clipboard", help="Copy result to clipboard."),
    mode: str = typer.Option("lite", "--mode", "-m", help="lite | aggressive"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Force language (es|en)."),
    translate: bool = typer.Option(False, "--translate", "-t", help="Translate ES -> EN technical."),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Comma-separated domains (e.g. web,backend). See `promptmin domains`."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only print minified output."),
):
    """Minify a prompt and report token savings."""
    original = _read_input(text, file, clipboard)
    domains_list = [d.strip() for d in domain.split(",")] if domain else []
    result = minify(original, mode=mode, lang=lang, translate=translate, domains=domains_list)
    stats = savings(original, result["minified"])

    if out_clipboard:
        import pyperclip
        pyperclip.copy(result["minified"])

    if quiet:
        typer.echo(result["minified"])
        return

    typer.secho("--- Minified ---", fg=typer.colors.CYAN, bold=True)
    typer.echo(result["minified"])
    typer.secho("--- Stats ---", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"lang:        {result['lang']}")
    if result.get("domains"):
        typer.echo(f"domains:     {', '.join(result['domains'])}")
    typer.echo(f"rules hit:   {result['rules_applied']}")
    typer.echo(f"tokens:      {stats['before']} -> {stats['after']}")
    color = typer.colors.GREEN if stats["saved"] > 0 else typer.colors.YELLOW
    typer.secho(f"saved:       {stats['saved']} ({stats['pct']}%)", fg=color, bold=True)


@app.command()
def domains():
    """List available domain dictionaries."""
    from .engine import available_domains, load_domain
    names = available_domains()
    if not names:
        typer.echo("(no domains found)")
        return
    typer.secho("Available domains:", fg=typer.colors.CYAN, bold=True)
    for n in names:
        size = len(load_domain(n))
        typer.echo(f"  {n:<12} {size} rules")
    typer.echo("\nUse with: promptmin run --domain web,backend \"...\"")


@app.command()
def benchmark(
    corpus: Path = typer.Argument(..., exists=True, help="Corpus file (one prompt per line, or JSONL)."),
    mode: str = typer.Option("lite", "--mode", "-m", help="lite | aggressive"),
    translate: bool = typer.Option(False, "--translate", "-t"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Comma-separated domains."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show every row."),
):
    """Run PromptMin over a corpus and report honest stats."""
    from .benchmark import load_corpus, run_benchmark, summarize
    prompts = load_corpus(corpus)
    domains_list = [d.strip() for d in domain.split(",")] if domain else []
    rows = run_benchmark(prompts, mode=mode, translate=translate, domains=domains_list)
    summary = summarize(rows)

    if verbose:
        for r in rows:
            typer.secho(f"[{r.idx:03d}] {r.lang} {r.before}->{r.after} ({r.pct:+.1f}%)", fg=typer.colors.CYAN)
            typer.echo(f"  IN : {r.original}")
            typer.echo(f"  OUT: {r.minified}")

    typer.secho("\n=== Benchmark summary ===", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"prompts:         {summary['n']}")
    typer.echo(f"mode:            {mode}{' +translate' if translate else ''}")
    typer.echo(f"tokens total:    {summary['tokens_before']} -> {summary['tokens_after']}")
    color = typer.colors.GREEN if summary["saved"] > 0 else typer.colors.YELLOW
    typer.secho(f"saved total:     {summary['saved']} ({summary['pct_total']}%)", fg=color, bold=True)
    typer.echo(f"avg / prompt:    {summary['pct_avg']}%")
    typer.echo(f"best / worst:    {summary['pct_best']}% / {summary['pct_worst']}%")
    typer.echo(f"regressions:     {summary['regressions']}")


@app.command()
def count(
    text: Optional[str] = typer.Argument(None),
    file: Optional[Path] = typer.Option(None, "--file", "-f", exists=True),
):
    """Just count tokens of a text."""
    from .tokens import count as _count
    content = _read_input(text, file, False)
    typer.echo(_count(content))


if __name__ == "__main__":
    app()
