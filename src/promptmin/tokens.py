"""Token counting using tiktoken (OpenAI BPE, industry reference)."""
from __future__ import annotations
import tiktoken

_ENC = None


def get_encoder(model: str = "cl100k_base"):
    global _ENC
    if _ENC is None:
        _ENC = tiktoken.get_encoding(model)
    return _ENC


def count(text: str) -> int:
    return len(get_encoder().encode(text))


def savings(before: str, after: str) -> dict:
    b = count(before)
    a = count(after)
    pct = 0.0 if b == 0 else (b - a) / b * 100
    return {"before": b, "after": a, "saved": b - a, "pct": round(pct, 1)}
