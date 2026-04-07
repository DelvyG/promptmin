from promptmin.engine import minify, detect_lang
from promptmin.tokens import count, savings


def test_detect_lang_es():
    assert detect_lang("Hola, necesito que desarrolles una función") == "es"


def test_detect_lang_en():
    assert detect_lang("Please build a function for me") == "en"


def test_minify_saves_tokens_en():
    text = "I would like you to please build a function step by step for the database."
    res = minify(text)
    s = savings(text, res["minified"])
    assert s["saved"] > 0, f"expected savings, got {s}"


def test_minify_saves_tokens_es():
    text = "Por favor, me gustaría que desarrolles una función paso a paso para la base de datos."
    res = minify(text)
    s = savings(text, res["minified"])
    assert s["saved"] > 0, f"expected savings, got {s}"


def test_translate_es_to_en_saves():
    text = "Por favor, desarrolla una función para la base de datos paso a paso."
    res = minify(text, translate=True)
    s = savings(text, res["minified"])
    assert s["saved"] > 0


def test_never_increases_tokens():
    """Core guarantee: minify must never produce more tokens than original."""
    samples = [
        "Hello world",
        "x",
        "Implement a REST API with authentication.",
        "Refactor this code please.",
    ]
    for t in samples:
        res = minify(t)
        assert count(res["minified"]) <= count(t), f"regressed on: {t!r}"
