"""Tests for Spanish phrase-level translation (Phase 3.5).

These tests protect against regressions in the phrase-first strategy that
was added to fix the "word-level substitution fails on gpt-4o" problem.
"""
from promptmin.engine import minify, load_dict
from promptmin.tokens import count


def test_phrases_dict_loads():
    phrases = load_dict("es_en_phrases")
    assert len(phrases) > 50, "es_en_phrases should have substantial content"


def test_user_real_prompt_saves_significantly_on_gpt4o():
    """The exact prompt that exposed the phrase-level strategy need.

    Before phrase strategy: 12.5% savings on gpt-4o.
    After phrase strategy: should be ~35-40%.
    """
    prompt = (
        "Por favor, desarrolla una función en Python que consulte la base "
        "de datos de usuarios y retorne un JSON con los activos"
    )
    res = minify(prompt, translate=True, tokenizer="gpt-4o")
    before = count(prompt, "gpt-4o")
    after = count(res["minified"], "gpt-4o")
    savings_pct = (before - after) / before * 100
    assert savings_pct >= 30.0, (
        f"expected >=30% savings on this prompt, got {savings_pct:.1f}%\n"
        f"  out: {res['minified']!r}"
    )


def test_phrase_runs_before_es_dict():
    """es.yaml would mutate 'base de datos'->'DB' before phrases could match
    'consulte la base de datos'. Phrases must run first."""
    prompt = "consulte la base de datos de productos"
    res = minify(prompt, translate=True, tokenizer="gpt-4o")
    # The output should contain 'queries' (from phrase) not 'DB' alone
    assert "queries" in res["minified"].lower() or "query" in res["minified"].lower()


def test_phrases_dont_regress_on_any_tokenizer():
    prompts = [
        "Por favor, desarrolla una función que consulte la base de datos",
        "Necesito que implementes un endpoint que retorne un JSON",
        "Me gustaría que revises este código paso a paso",
    ]
    from promptmin.tokens import available_tokenizers
    for t in available_tokenizers():
        for p in prompts:
            res = minify(p, translate=True, tokenizer=t["name"])
            assert count(res["minified"], t["name"]) <= count(p, t["name"]), (
                f"regressed on {t['name']} with {p!r}"
            )
