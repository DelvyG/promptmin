# PromptMin — Context for Claude

This file exists so that any future Claude session can ramp up on this project in under a minute. Read it first, then dive into code.

## What this project is (in one paragraph)

PromptMin is a CLI and Python library that minifies LLM prompts to save tokens. It applies curated phrase substitutions from YAML dictionaries (general + domain-specific) and validates every rule against a real tokenizer (tiktoken) before accepting it. The core promise is **"the output will never have more tokens than the input"** — enforced at runtime, not trusted. Install name on PyPI is `promptminify` (because `promptmin` was taken); CLI command and Python import remain `promptmin`. Repo: https://github.com/DelvyG/promptmin. PyPI: https://pypi.org/project/promptminify/.

## Current status (as of v0.3.0)

- **Published on PyPI** as `promptminify` via Trusted Publishing (OIDC), no tokens stored as secrets.
- **CI green** on GitHub Actions across Ubuntu/macOS/Windows × Python 3.10/3.11/3.12/3.13.
- **24 tests passing** (engine + domains + tokens + phrase translation).
- **Measured savings**: 21.7% with gpt-4o tokenizer, 23.9% with gpt-4/cl100k, up to 25.3% with `aggressive --translate` on the bundled corpus. Zero regressions across all tokenizers.
- **On Spanish prompts targeting gpt-4o, `--translate` is essential**: it raises savings from ~12% to ~37% on real-world technical prompts, thanks to the phrase-level translation strategy introduced in v0.3.0.
- **Released**: `v0.2.0` (feature release), `v0.2.1` (PyPI rename + metadata), `v0.3.0` (Spanish phrase translation).

## Architecture in 30 seconds

```
src/promptmin/
├── cli.py          # Typer CLI. Commands: run, benchmark, domains, tokenizers, count
├── engine.py       # minify() pipeline. Detect lang → domain dicts → lang dict → ES/EN translate → stopwords → ws collapse
├── tokens.py       # Pluggable tokenizer registry (@register). gpt-4o/gpt-4/claude/gemini
├── benchmark.py    # Load corpus (txt or JSONL), run_benchmark(), summarize()
└── dicts/
    ├── en.yaml, es.yaml                   # General word/short-phrase dicts
    ├── es_en.yaml                         # Word-level ES->EN (rarely fires on gpt-4o)
    ├── es_en_phrases.yaml                 # Phrase-level ES->EN (the REAL workhorse for ES)
    └── domains/
        ├── ai.yaml, backend.yaml,       # Domain-specific (activated with -d flag)
        ├── data.yaml, devops.yaml,
        └── web.yaml

tests/              # 20 tests: test_engine.py, test_domains.py, test_tokens.py
examples/           # Sample corpora for benchmarking
.github/workflows/  # ci.yml (tests) + publish.yml (PyPI via OIDC)
```

## Design decisions (and the WHY behind them)

These matter because they've been deliberated. Do not silently revert them.

1. **Curated dicts, not massive ones.** The instinct is to add 100k rules. The truth is the top ~200 frequent phrases give 80% of savings, the rest adds latency and conflict risk. Keep dicts lean. Target: 30-60 high-signal entries per domain.

2. **tiktoken validator is non-negotiable.** Every substitution is applied one-at-a-time and the resulting token count is compared against the original. If it doesn't save, the rule is skipped. This is *the* guarantee of the project. Never bypass it.

3. **Longest-match first, word boundaries.** `"step by step"` beats `"step"`, and `"database"` in `"databases"` does NOT match. This prevents surprises.

4. **PyPI name ≠ import name.** `promptminify` is the install name; `promptmin` is the import and CLI name. Like pillow/PIL. Documented in README.

5. **Trusted Publishing over API tokens.** `publish.yml` uses OIDC. This means zero secrets in the repo, and the only way to publish is from a tagged commit on the `DelvyG/promptmin` repo via the `publish.yml` workflow in the `pypi` environment. Configured once on pypi.org/manage/account/publishing/.

6. **Claude/Gemini tokenizers are APPROXIMATE.** They use cl100k_base as a proxy because Anthropic/Google don't publish offline tokenizers. This is fine for PromptMin's use case (relative before/after comparison). For exact billing estimates, users should use official SDKs. Documented clearly in `tokens.py` and README.

7. **GPT-4o is the default tokenizer.** It's the current flagship OpenAI model and uses o200k_base. Note that savings are slightly lower on gpt-4o (21.7%) than gpt-4/cl100k (23.9%) because o200k is already more efficient on raw text — there's less margin to squeeze. This is reported honestly in the README.

8. **Phrase-level translation is the Spanish strategy, not word-level.** The word-level ES→EN dict (`es_en.yaml`) exists for legacy and edge cases, but almost never fires on `gpt-4o`. Inserting a single English word into Spanish text breaks BPE merges and often nets zero savings. The real work happens in `es_en_phrases.yaml`, which rewrites multi-word chunks so BPE merges align on both sides. This is why `minify()` applies phrases BEFORE `es.yaml` when `translate=True` — because `es.yaml` would mutate `"base de datos" → "DB"` too early and prevent phrases like `"consulte la base de datos" → "queries the DB"` from ever matching. Order matters.

## Known gotchas and workarounds

- **Git token doesn't have `workflow` scope.** Cannot push changes to `.github/workflows/*.yml` from Claude's bash. Workaround: write the file locally, then ask the user to paste it via GitHub web UI. This is why `ci.yml` and `publish.yml` were added manually via the browser.
- **Windows console cp encoding.** `promptmin run` in Windows terminal may show `�` for accented characters in output. The underlying text is correct UTF-8, it's just the display. Don't "fix" by stripping accents.
- **`"on":` in YAML.** GitHub rejected `on:` as YAML 1.1 parses it as boolean in some parsers. We use `"on":` quoted. Don't change back.
- **Spanish conjugation gap (largely solved in v0.3.0).** Previously `es_en.yaml` had `"desarrolla": "build"` but not `"desarrolles"`, and word-level ES→EN often produced 0 savings on gpt-4o anyway. v0.3.0 sidesteps the whole problem by using phrase-level patterns that bake conjugations into full structures (`"por favor, desarrolla una"`, `"necesito que desarrolles"`, etc.). If you need more coverage, ADD PHRASES to `es_en_phrases.yaml`, don't add more word-level entries to `es_en.yaml`.

## How things connect

- `engine.minify()` is the one function everything else wraps. CLI, library API, and benchmark all call it.
- The validator inside `_apply_substitutions` is what makes the guarantees hold. Don't add code paths that skip it.
- New tokenizers = new `@register` decorator in `tokens.py`. Zero changes anywhere else.
- New domains = new YAML file in `dicts/domains/`. Auto-discovered by `available_domains()`. Zero Python changes.
- New languages = new YAML in `dicts/` + update `detect_lang()` in `engine.py` + stopwords in `engine.STOPWORDS`.

## Roadmap

```
✅ Phase 1      MVP CLI (engine + EN/ES dicts + tiktoken validator)
✅ Phase 2      Benchmark + lite/aggressive/translate modes
✅ Phase 2.5    Domain dictionaries (ai, backend, data, devops, web)
✅ Phase 3      Multi-tokenizer (gpt-4o, gpt-4, claude, gemini)
✅ Phase 3.5    Spanish phrase-level translation (es_en_phrases.yaml) — the
                fix for the "word-level fails on gpt-4o" problem discovered
                through real user testing.
✅ Publishing   PyPI (promptminify) + GitHub CI + releases
⬜ Phase 3.6    Official SDK integration for EXACT Claude/Gemini counts as
                optional extras (pip install 'promptminify[claude]')
⬜ Phase 3.6    Grow es_en_phrases.yaml from real-usage corpora (users run
                their own prompts, log which patterns are missing)
⬜ Phase 4      VSCode extension (TypeScript, calls CLI via child_process,
                keybinding "Minify Selection" that replaces text in place)
⬜ Phase 4      More domains: mobile, security, gamedev, finance, blockchain
⬜ Phase 4      Domain auto-detection from prompt content
```

## What to do in the next session (suggested order)

1. **Ask the user what they want**. They may have new ideas or priorities. Don't assume.

2. **If the user says "continue"**, the highest-leverage next step is growing `es_en_phrases.yaml` organically. The user should run PromptMin on their real Spanish prompts (with `--translate -T gpt-4o`) and identify which common patterns are missing. Every new phrase pattern is validated by the engine, so you can't make things worse — only better. The test `test_user_real_prompt_saves_significantly_on_gpt4o` should keep passing.

3. **If the user wants the VSCode extension**, create a *separate repo* `promptmin-vscode`. Don't pollute this repo with TS code. The extension should call `promptmin` via child_process, so it requires `pip install promptminify` as a prerequisite. Keybinding: `Ctrl+Shift+M` for "Minify Selection".

4. **If the user wants to grow the project organically**, suggest: run `promptmin run` on their real prompts for a few days, keep a `NOTES.md` of rules that are missing, then batch them into YAML PRs. This is the sustainable growth path.

## Commands cheat sheet

```bash
# Development
pip install -e ".[dev]"
pytest -q

# Build and verify for PyPI
python -m build
python -m twine check dist/*

# Release flow (fully automated after tag push)
# 1. Bump version in pyproject.toml AND src/promptmin/__init__.py
# 2. Commit
# 3. git tag -a vX.Y.Z -m "..."
# 4. git push && git push origin vX.Y.Z
# → ci.yml runs tests, publish.yml runs on tag and ships to PyPI via OIDC

# Smoke test the CLI
promptmin --help
promptmin domains
promptmin tokenizers
promptmin run -d web,backend "Please improve the UX and add JWT authentication"
promptmin benchmark examples/corpus_domains.txt -d web,backend,devops,data,ai -T gpt-4o
```

## Files the user may point you to

- `README.md` — user-facing, audience is developers evaluating the tool
- `CONTRIBUTING.md` — how community adds dicts, domains, languages
- `pyproject.toml` — PyPI metadata, dependencies, entry point
- `.github/workflows/ci.yml` — tests matrix
- `.github/workflows/publish.yml` — OIDC release to PyPI

## Things NOT to do

- Don't add heavy NLP dependencies (spaCy, nltk, transformers). The bar is: tiktoken, typer, pyyaml, pyperclip. Anything new requires justification.
- Don't silently change the default tokenizer. It's gpt-4o for a reason.
- Don't bypass the token validator. Every rule must be checked.
- Don't add 100+ rules to a YAML file without measuring their impact. Bloat without benefit is a regression in disguise.
- Don't create new workflow files from Claude's bash — push will fail on scope. Hand the content to the user to paste via web.
- Don't rename the PyPI package away from `promptminify`. It's taken everywhere now.
