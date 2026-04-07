"""Token counting with pluggable backends.

PromptMin supports multiple tokenizers so users can measure/optimize for
the model they actually target.

Currently registered:
  - "gpt-4o" / "o200k"  -> tiktoken o200k_base  (GPT-4o, GPT-4.1, o1, o3)  [EXACT]
  - "gpt-4"  / "cl100k" -> tiktoken cl100k_base (GPT-4, GPT-3.5, ada-002)  [EXACT]
  - "claude"            -> tiktoken cl100k_base                            [APPROX]
  - "gemini"            -> tiktoken cl100k_base                            [APPROX]

The APPROX tokenizers use cl100k_base as a proxy because Anthropic and
Google do not publish their tokenizers in a form usable offline without
API calls. Empirically, cl100k_base is within ~5-10% of the real counts
for Claude and Gemini on typical technical prompts, which is good enough
for *relative* measurements (before/after savings) -- which is all
PromptMin needs for its validator. For absolute billing estimates, use
the official SDKs.

Adding a new tokenizer is trivial: register a function that returns
int (token count) under a name. See @register below.
"""
from __future__ import annotations
from typing import Callable
import tiktoken

Counter = Callable[[str], int]

_REGISTRY: dict[str, Counter] = {}
_META: dict[str, dict] = {}
_ENCODERS_CACHE: dict[str, tiktoken.Encoding] = {}

DEFAULT_TOKENIZER = "gpt-4o"


def register(name: str, *, exact: bool, family: str, aliases: tuple[str, ...] = ()):
    """Register a tokenizer counter under a name (and optional aliases)."""
    def deco(fn: Counter) -> Counter:
        _REGISTRY[name] = fn
        _META[name] = {"exact": exact, "family": family, "aliases": list(aliases)}
        for alias in aliases:
            _REGISTRY[alias] = fn
        return fn
    return deco


def _tiktoken_encoder(encoding: str) -> tiktoken.Encoding:
    if encoding not in _ENCODERS_CACHE:
        _ENCODERS_CACHE[encoding] = tiktoken.get_encoding(encoding)
    return _ENCODERS_CACHE[encoding]


@register("gpt-4o", exact=True, family="openai", aliases=("o200k", "gpt-4.1", "o1", "o3"))
def _count_o200k(text: str) -> int:
    return len(_tiktoken_encoder("o200k_base").encode(text))


@register("gpt-4", exact=True, family="openai", aliases=("cl100k", "gpt-3.5", "gpt-4-turbo", "ada-002"))
def _count_cl100k(text: str) -> int:
    return len(_tiktoken_encoder("cl100k_base").encode(text))


@register("claude", exact=False, family="anthropic", aliases=("claude-3", "claude-4", "claude-opus", "claude-sonnet"))
def _count_claude(text: str) -> int:
    # Approximation: Claude's BPE behaves close to cl100k_base on mixed text.
    # For exact counts, use anthropic.Anthropic().messages.count_tokens().
    return len(_tiktoken_encoder("cl100k_base").encode(text))


@register("gemini", exact=False, family="google", aliases=("gemini-1.5", "gemini-2", "gemini-pro"))
def _count_gemini(text: str) -> int:
    # Approximation: Gemini uses SentencePiece; cl100k_base is within ~10%
    # on English/Spanish technical prompts. For exact counts, use
    # google.genai Client().models.count_tokens().
    return len(_tiktoken_encoder("cl100k_base").encode(text))


# --- public API ---------------------------------------------------------


def get_counter(name: str | None = None) -> Counter:
    """Return a counter function by name (or the default)."""
    name = name or DEFAULT_TOKENIZER
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown tokenizer {name!r}. Available: {', '.join(sorted(set(_REGISTRY)))}"
        )
    return _REGISTRY[name]


def available_tokenizers() -> list[dict]:
    """List canonical tokenizers (no alias duplication) with metadata."""
    out = []
    for name, meta in _META.items():
        out.append({
            "name": name,
            "exact": meta["exact"],
            "family": meta["family"],
            "aliases": meta["aliases"],
        })
    return sorted(out, key=lambda r: (r["family"], r["name"]))


def count(text: str, tokenizer: str | None = None) -> int:
    """Count tokens of `text` using the selected tokenizer."""
    return get_counter(tokenizer)(text)


def savings(before: str, after: str, tokenizer: str | None = None) -> dict:
    counter = get_counter(tokenizer)
    b = counter(before)
    a = counter(after)
    pct = 0.0 if b == 0 else (b - a) / b * 100
    return {"before": b, "after": a, "saved": b - a, "pct": round(pct, 1)}
