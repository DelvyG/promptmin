"""Minification engine.

Pipeline:
  1. detect language (simple heuristic)
  2. load dict (YAML) for that language
  3. phrase substitution (longest-first, case-insensitive)
  4. stopword strip
  5. whitespace collapse

Every rule application is validated against tiktoken: if a substitution
does NOT reduce tokens, it is skipped. This is the core promise.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Iterable
import yaml

from .tokens import get_counter

DICTS_DIR = Path(__file__).parent / "dicts"
DOMAINS_DIR = DICTS_DIR / "domains"

# Stopword sets. "lite" = safe, always removable filler.
# "aggressive" = also removes soft glue words that may slightly change tone
# but rarely hurt the model's understanding.
STOPWORDS = {
    "lite": {
        "es": {
            "por favor", "podrias", "podrías", "me gustaria", "me gustaría",
            "quisiera", "necesito que", "quiero que",
        },
        "en": {
            "please", "kindly", "i would like to", "i would like you to",
            "could you", "can you", "i want you to", "i need you to",
        },
    },
    "aggressive": {
        "es": {
            "basicamente", "básicamente", "simplemente", "realmente",
            "actualmente", "en realidad", "de hecho", "obviamente",
            "por supuesto", "tal vez", "quizas", "quizás",
        },
        "en": {
            "basically", "simply", "really", "actually", "just",
            "of course", "obviously", "in fact", "maybe", "perhaps",
            "very", "quite", "rather",
        },
    },
}


def detect_lang(text: str) -> str:
    """Cheap heuristic: look for Spanish-only markers."""
    t = f" {text.lower()} "
    es_markers = (" el ", " la ", " los ", " las ", " por ", " que ",
                  " una ", " uno ", " con ", " para ", " ñ", "¿", "¡")
    if any(m in t for m in es_markers):
        return "es"
    return "en"


def load_dict(lang: str) -> dict[str, str]:
    path = DICTS_DIR / f"{lang}.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()}


def available_domains() -> list[str]:
    """List all domain dictionaries available."""
    if not DOMAINS_DIR.exists():
        return []
    return sorted(p.stem for p in DOMAINS_DIR.glob("*.yaml"))


def load_domain(name: str) -> dict[str, str]:
    path = DOMAINS_DIR / f"{name}.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()}


def load_domains(names: Iterable[str]) -> dict[str, str]:
    """Merge multiple domain dictionaries. Later domains win on conflict."""
    merged: dict[str, str] = {}
    for n in names:
        merged.update(load_domain(n.strip()))
    return merged


def _apply_substitutions(
    text: str,
    mapping: dict[str, str],
    counter,
    validate: bool = True,
) -> tuple[str, int]:
    """Apply longest-first, word-boundary, case-insensitive substitutions.
    Returns (new_text, n_applied).
    """
    applied = 0
    # longest keys first so "step by step" beats "step"
    for key in sorted(mapping.keys(), key=len, reverse=True):
        if not key:
            continue
        val = mapping[key]
        pattern = re.compile(r"(?<!\w)" + re.escape(key) + r"(?!\w)", re.IGNORECASE)
        if not pattern.search(text):
            continue
        new_text = pattern.sub(val, text)
        if validate and counter(new_text) >= counter(text):
            continue  # rule didn't actually save tokens -> skip
        text = new_text
        applied += 1
    return text, applied


def _strip_stopwords(text: str, phrases: Iterable[str]) -> str:
    for p in sorted(phrases, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(p) + r"(?!\w)", "", text, flags=re.IGNORECASE)
    return text


def _collapse_ws(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(" \t\n,;:")


def minify(
    text: str,
    mode: str = "lite",
    lang: str | None = None,
    translate: bool = False,
    domains: Iterable[str] | None = None,
    tokenizer: str | None = None,
) -> dict:
    """Minify a prompt.

    mode: "lite"       -> dict + stopwords (safe)
          "aggressive" -> also strip more glue words
    translate: if True and lang=="es", apply ES->EN dict as well.
    domains:   optional list of domain names (e.g. ["web", "backend"]).
               Domain rules are applied FIRST (highest precedence), so that
               e.g. "user experience" -> "UX" beats a generic rule.
    """
    original = text
    lang = lang or detect_lang(text)
    domains = list(domains or [])
    counter = get_counter(tokenizer)

    out = text
    rules_applied = 0

    # 1. domain dictionaries (highest precedence, applied first)
    if domains:
        domain_map = load_domains(domains)
        out, n = _apply_substitutions(out, domain_map, counter)
        rules_applied += n

    # 2. ES->EN phrase-level translation MUST run BEFORE lang dict.
    # Word-level ES->EN fails on modern tokenizers (o200k_base / gpt-4o)
    # because inserting a single English word breaks Spanish BPE merges.
    # Multi-word phrase patterns align BPE merges on both sides.
    # Also: phrases must run before es.yaml because es.yaml mutations like
    # "base de datos" -> "DB" would prevent phrases like "consulte la base
    # de datos" -> "queries the DB" from ever matching.
    if translate and lang == "es":
        es_en_phrases = load_dict("es_en_phrases")
        out, n = _apply_substitutions(out, es_en_phrases, counter)
        rules_applied += n

    # 3. language-specific dict (runs AFTER phrase translation so it handles
    # whatever Spanish is left over)
    mapping = load_dict(lang)
    out, n = _apply_substitutions(out, mapping, counter)
    rules_applied += n

    # 4. word-level ES->EN fallback + English dict cleanup
    if translate and lang == "es":
        es_en = load_dict("es_en")
        out, n = _apply_substitutions(out, es_en, counter)
        rules_applied += n
        out, n = _apply_substitutions(out, load_dict("en"), counter)
        rules_applied += n

    # 3. stopwords (lite always; aggressive adds more)
    stop_lang = "en" if translate and lang == "es" else lang
    out = _strip_stopwords(out, STOPWORDS["lite"].get(stop_lang, set()))
    if mode == "aggressive":
        out = _strip_stopwords(out, STOPWORDS["aggressive"].get(stop_lang, set()))

    # 4. whitespace
    out = _collapse_ws(out)

    return {
        "original": original,
        "minified": out,
        "lang": lang,
        "rules_applied": rules_applied,
        "mode": mode,
        "domains": domains,
        "tokenizer": tokenizer or "gpt-4o",
    }
