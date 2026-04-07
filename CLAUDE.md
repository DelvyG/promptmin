# PromptMin — Context for Claude

This file exists so that any future Claude session can ramp up on this project in under a minute. Read it first, then dive into code.

## What this project is (in one paragraph)

PromptMin is a CLI and Python library that minifies LLM prompts to save tokens. It applies curated phrase substitutions from YAML dictionaries (general + domain-specific) and validates every rule against a real tokenizer (tiktoken) before accepting it. The core promise is **"the output will never have more tokens than the input"** — enforced at runtime, not trusted. Install name on PyPI is `promptminify` (because `promptmin` was taken); CLI command and Python import remain `promptmin`. Repo: https://github.com/DelvyG/promptmin. PyPI: https://pypi.org/project/promptminify/.

## Current status (as of v0.2.1)

- **Published on PyPI** as `promptminify` via Trusted Publishing (OIDC), no tokens stored as secrets.
- **CI green** on GitHub Actions across Ubuntu/macOS/Windows × Python 3.10/3.11/3.12/3.13.
- **20 tests passing** (engine + domains + tokens).
- **Measured savings**: 21.7% with gpt-4o tokenizer, 23.9% with gpt-4/cl100k, up to 25.3% with `aggressive --translate` on the bundled corpus. Zero regressions across all tokenizers.
- **Released**: `v0.2.0` (feature release), `v0.2.1` (PyPI rename + metadata).

## Architecture in 30 seconds

```
src/promptmin/
├── cli.py          # Typer CLI. Commands: run, benchmark, domains, tokenizers, count
├── engine.py       # minify() pipeline. Detect lang → domain dicts → lang dict → ES/EN translate → stopwords → ws collapse
├── tokens.py       # Pluggable tokenizer registry (@register). gpt-4o/gpt-4/claude/gemini
├── benchmark.py    # Load corpus (txt or JSONL), run_benchmark(), summarize()
└── dicts/
    ├── en.yaml, es.yaml, es_en.yaml    # General dictionaries
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

## Known gotchas and workarounds

- **Git token doesn't have `workflow` scope.** Cannot push changes to `.github/workflows/*.yml` from Claude's bash. Workaround: write the file locally, then ask the user to paste it via GitHub web UI. This is why `ci.yml` and `publish.yml` were added manually via the browser.
- **Windows console cp encoding.** `promptmin run` in Windows terminal may show `�` for accented characters in output. The underlying text is correct UTF-8, it's just the display. Don't "fix" by stripping accents.
- **`"on":` in YAML.** GitHub rejected `on:` as YAML 1.1 parses it as boolean in some parsers. We use `"on":` quoted. Don't change back.
- **Spanish conjugation gap.** `es_en.yaml` has `"desarrolla": "build"` but not `"desarrolles"`, `"desarrollen"`, etc. The dict misses ~50% of real Spanish prompts because of this. Two fixes: (a) manually add common conjugations to YAML, (b) implement light stemming (planned for v0.3). Don't add spaCy for this — too heavy.

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
✅ Publishing   PyPI (promptminify) + GitHub CI + releases
⬜ Phase 3.5    Light ES stemming (pure Python, ~50 lines, no deps)
⬜ Phase 3.5    Official SDK integration for EXACT Claude/Gemini counts as optional extras
                (pip install 'promptminify[claude]' → uses anthropic SDK for count_tokens)
⬜ Phase 4      VSCode extension (TypeScript, calls CLI via child_process,
                keybinding "Minify Selection" that replaces text in place)
⬜ Phase 4      More domains: mobile, security, gamedev, finance, blockchain
⬜ Phase 4      Domain auto-detection from prompt content
⬜ Ongoing      Grow dicts from real usage logs (see below)
```

## What to do in the next session (suggested order)

1. **Ask the user what they want**. They may have new ideas or priorities. Don't assume.

2. **If the user says "continue"**, the highest-leverage next step is Camino D (light ES stemming). Pure Python, 1-2 hours, raises Spanish savings by ~5-10 points. Implementation sketch:
   - New file `src/promptmin/stemming.py` with a `normalize_es(text)` function.
   - Strip common Spanish verb endings: `-es`, `-en`, `-an`, `-as`, `-ar`, `-er`, `-ir`, `-ado`, `-ido`, `-amos`, `-emos`, `-imos`.
   - Build an inverse map: when a stemmed form matches a dict key, resolve to the original.
   - Wire it into `_apply_substitutions` as an alternate match path.
   - Tests in `tests/test_stemming.py`.
   - Bump to v0.2.2 or v0.3.0 and release.

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
