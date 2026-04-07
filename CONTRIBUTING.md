# Contributing to PromptMin

Thanks for wanting to help. PromptMin is designed so that **most valuable contributions require zero Python code** — you can add entire dictionaries or languages by editing YAML.

## Quick start

```bash
git clone https://github.com/DelvyG/promptmin.git
cd promptmin
pip install -e ".[dev]"
pytest
```

If `pytest` is green, you're ready.

---

## The 4 types of contributions, ranked by usefulness

### 1. Add phrases to an existing dictionary (easiest)

Open any file in `src/promptmin/dicts/` or `src/promptmin/dicts/domains/` and add entries:

```yaml
"your long phrase here": "shorter version"
```

**Rules:**
- Keys are **case-insensitive** and matched on **word boundaries**.
- Longest keys are matched first, so `"step by step"` beats `"step"`.
- You do **not** need to pre-verify token savings — the engine will skip rules at runtime if they don't actually reduce tokens. But try to pick rules you *believe* will save tokens (shorter output, common abbreviations).
- Keep substitutions **semantically safe**. `"database" -> "DB"` is fine. `"user" -> "u"` is not (breaks meaning in most contexts).

**How to test your rule saves tokens:**

```bash
promptmin count "your long phrase here"
promptmin count "shorter version"
```

If the second number is smaller, your rule will be active.

### 2. Add a new domain dictionary (high impact)

Create a new file: `src/promptmin/dicts/domains/<your_domain>.yaml`

Examples of domains we'd love to see:
- `mobile` — iOS / Android / React Native / Flutter terminology
- `security` — CVE, XSS, CSRF, OWASP, penetration testing
- `gamedev` — ECS, shader, GPU, render loop
- `finance` — P&L, EBITDA, KPI, forecasting
- `blockchain` — smart contract, gas, L2, consensus

Use the existing domain files as templates. Aim for **30–60 high-signal entries** rather than hundreds of marginal ones. Quality beats quantity.

After adding the file, it's automatically picked up — no registration needed:

```bash
promptmin domains          # your new domain appears in the list
promptmin run -d mobile "..."
```

### 3. Add a new language (medium effort)

Create `src/promptmin/dicts/<lang>.yaml` (e.g. `fr.yaml`, `pt.yaml`, `de.yaml`).

Then update the language detector in `src/promptmin/engine.py` (`detect_lang`) with a cheap heuristic for your language. Look at how `es` is detected for reference — just a short list of very common words that rarely appear in other languages.

Optionally add a `<lang>_en.yaml` translation layer if that language benefits from falling back to English technical terms.

Add stopword phrases to the `STOPWORDS` dict in `engine.py` for both `"lite"` and `"aggressive"` modes.

Add tests in `tests/test_engine.py` following the pattern of `test_minify_saves_tokens_es`.

### 4. Improve the engine (advanced)

Before opening a PR that touches `engine.py`, please open an issue first to discuss the approach. Good candidates:

- Light stemming / lemmatization for better Spanish matching (without heavy NLP deps like spaCy).
- Multi-tokenizer support (Anthropic's tokenizer, Google's `tokenizers`).
- Domain auto-detection from prompt content.
- Caching of `tiktoken` encodes during benchmark runs.

---

## Hard rules for all PRs

- ✅ **Zero regressions.** The test `test_never_increases_tokens` must stay green. PromptMin's core promise is that output tokens ≤ input tokens, always.
- ✅ **`pytest` must pass.** Run it locally before pushing.
- ✅ **No heavy dependencies** without prior discussion. We want PromptMin to install in < 5 seconds. `tiktoken`, `typer`, `pyyaml`, `pyperclip` are the bar.
- ✅ **Keep PRs focused.** One domain per PR, one feature per PR. Easier to review, easier to merge.
- ✅ **Document new behavior.** Update `README.md` if you add a user-facing feature.

## Commit style

Short, imperative, prefixed:

```
feat(web): add UX/UI and SPA phrases
fix(engine): stopword strip preserves punctuation
docs: clarify translate mode in README
test: cover domain precedence
```

## Questions?

Open an [issue](https://github.com/DelvyG/promptmin/issues) with the `question` label.
