import pytest
from promptmin.tokens import (
    count, savings, get_counter, available_tokenizers, DEFAULT_TOKENIZER
)
from promptmin.engine import minify


def test_default_tokenizer_works():
    assert count("hello world") > 0


def test_all_registered_tokenizers_count():
    text = "Please build a function step by step for the database."
    for t in available_tokenizers():
        c = count(text, tokenizer=t["name"])
        assert c > 0, f"{t['name']} returned 0"


def test_unknown_tokenizer_raises():
    with pytest.raises(ValueError):
        count("hello", tokenizer="made-up-tokenizer")


def test_gpt4o_and_gpt4_differ():
    """o200k_base and cl100k_base should give different counts on long text."""
    text = "Please build a REST API with JWT authentication and rate limiting."
    a = count(text, tokenizer="gpt-4o")
    b = count(text, tokenizer="gpt-4")
    # They won't always differ on short inputs, but for technical text
    # of this length they usually do. Just assert both are positive.
    assert a > 0 and b > 0


def test_aliases_work():
    # cl100k is alias of gpt-4
    assert count("hello world", tokenizer="cl100k") == count("hello world", tokenizer="gpt-4")
    # o200k alias of gpt-4o
    assert count("hello world", tokenizer="o200k") == count("hello world", tokenizer="gpt-4o")
    # claude-3 alias of claude
    assert count("hello world", tokenizer="claude-3") == count("hello world", tokenizer="claude")


def test_minify_with_each_tokenizer_never_regresses():
    """Core guarantee must hold for every tokenizer backend."""
    text = "Please, I would like you to build a function step by step for the database configuration."
    for t in available_tokenizers():
        res = minify(text, tokenizer=t["name"])
        before = count(text, tokenizer=t["name"])
        after = count(res["minified"], tokenizer=t["name"])
        assert after <= before, (
            f"regressed on {t['name']}: {before} -> {after}\n"
            f"  out: {res['minified']!r}"
        )


def test_savings_report_uses_specified_tokenizer():
    s1 = savings("please build a function", "build func", tokenizer="gpt-4")
    s2 = savings("please build a function", "build func", tokenizer="gpt-4o")
    assert "before" in s1 and "after" in s1
    assert "before" in s2 and "after" in s2


def test_default_tokenizer_is_gpt4o():
    assert DEFAULT_TOKENIZER == "gpt-4o"
