"""Benchmark PromptMin on a corpus of real prompts.

Corpus format: plain text file, one prompt per line (blank lines ignored).
Or JSONL with {"prompt": "..."} per line.
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass

from .engine import minify
from .tokens import count


@dataclass
class Row:
    idx: int
    lang: str
    before: int
    after: int
    saved: int
    pct: float
    original: str
    minified: str


def load_corpus(path: Path) -> list[str]:
    prompts: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                if "prompt" in obj:
                    prompts.append(obj["prompt"])
                    continue
            except json.JSONDecodeError:
                pass
        prompts.append(line)
    return prompts


def run_benchmark(
    prompts: list[str],
    mode: str = "lite",
    translate: bool = False,
    domains: list[str] | None = None,
) -> list[Row]:
    rows: list[Row] = []
    for i, p in enumerate(prompts):
        res = minify(p, mode=mode, translate=translate, domains=domains)
        b = count(p)
        a = count(res["minified"])
        pct = 0.0 if b == 0 else (b - a) / b * 100
        rows.append(Row(
            idx=i, lang=res["lang"], before=b, after=a,
            saved=b - a, pct=round(pct, 1),
            original=p, minified=res["minified"],
        ))
    return rows


def summarize(rows: list[Row]) -> dict:
    if not rows:
        return {"n": 0}
    total_b = sum(r.before for r in rows)
    total_a = sum(r.after for r in rows)
    saved = total_b - total_a
    pct = 0.0 if total_b == 0 else saved / total_b * 100
    per = [r.pct for r in rows]
    return {
        "n": len(rows),
        "tokens_before": total_b,
        "tokens_after": total_a,
        "saved": saved,
        "pct_total": round(pct, 1),
        "pct_avg": round(sum(per) / len(per), 1),
        "pct_best": round(max(per), 1),
        "pct_worst": round(min(per), 1),
        "regressions": sum(1 for r in rows if r.saved < 0),
    }
