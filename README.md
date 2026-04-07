# PromptMin

**Minify LLM prompts to save tokens — without losing meaning.**

[![PyPI version](https://img.shields.io/pypi/v/promptminify.svg)](https://pypi.org/project/promptminify/)
[![PyPI downloads](https://img.shields.io/pypi/dm/promptminify.svg)](https://pypi.org/project/promptminify/)
[![CI](https://github.com/DelvyG/promptmin/actions/workflows/ci.yml/badge.svg)](https://github.com/DelvyG/promptmin/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

LLM APIs charge per token, and non-English prompts (especially Spanish) can use 20–30% more tokens than their English equivalents. **PromptMin** rewrites your prompts into a denser form using curated, domain-aware substitutions, and reports real token savings measured with `tiktoken`.

> **Core guarantee.** Every substitution rule is validated against `tiktoken` at runtime. If a rule does **not** reduce token count, it is skipped. PromptMin never makes your prompt longer.

## Why?

Most "token savers" are naive find-and-replace scripts that don't actually save tokens (because BPE tokenizers don't count characters). PromptMin is different:

- **Mathematically validated.** Rules are only applied when the tokenizer confirms they save tokens.
- **Curated, not massive.** ~400 high-signal rules beat 100,000 random ones.
- **Domain-aware.** Activate dictionaries by context (`web`, `backend`, `ai`…) for aggressive but safe compression.
- **Multi-tokenizer.** Optimize for the model you target: GPT-4o, GPT-4, Claude, Gemini.
- **Bilingual.** First-class Spanish + English, extensible to any language via YAML.
- **Honest benchmarks.** Run `promptmin benchmark` on your own corpus and see real numbers.

## Real numbers

Measured on the included corpus `examples/corpus_domains.txt` (18 mixed EN/ES technical prompts):

**Savings by configuration** (tokenizer: `gpt-4`):

| Configuration | Tokens saved | Avg per prompt | Best |
|---|---|---|---|
| General rules only | 2.2% | 1.9% | 23.1% |
| + domain dictionaries | **23.9%** | 23.2% | 38.5% |
| + domains + translate + aggressive | **25.3%** | 24.5% | 42.3% |

**Savings by tokenizer** (config: lite + all domains):

| Tokenizer | Family | Total saved | Notes |
|---|---|---|---|
| `gpt-4` / `cl100k` | OpenAI | **23.9%** | Exact — used by GPT-4, GPT-3.5 |
| `claude` | Anthropic | 23.9% | Approximate (cl100k_base proxy) |
| `gemini` | Google | 23.9% | Approximate (cl100k_base proxy) |
| `gpt-4o` / `o200k` | OpenAI | **21.7%** | Exact — used by GPT-4o, o1, o3 |

> The newer `gpt-4o` tokenizer (`o200k_base`) is already more efficient on raw text than `cl100k_base`, which is why PromptMin has slightly less margin to optimize on it. This is the honest reality — and exactly why benchmarking matters.

**Zero regressions** across all modes and all tokenizers. The validator guarantees it.

### A note on Spanish prompts and modern tokenizers

If you write prompts in Spanish and target `gpt-4o` (or any modern `o200k_base`-family model), **always use `--translate`**. Without it, savings are modest (~10-15%). With it, savings jump to ~25-40%.

**Why?** Modern BPE tokenizers learn very efficient merges for common Spanish constructs like `"una función"`, `"la base de datos"`, `"por favor"`. Substituting a single word (`"función" → "func"`) inside Spanish text often produces **zero token savings** because the original Spanish merge was already compact. The only reliable way to save tokens on Spanish is to rewrite **larger chunks** into English at once, so BPE merges align on both sides.

This is why PromptMin v0.3+ uses **phrase-level translation patterns** (`dicts/es_en_phrases.yaml`) as the primary strategy for Spanish, applied BEFORE word-level rules. A simple prompt like:

> `"Por favor, desarrolla una función en Python que consulte la base de datos de usuarios y retorne un JSON con los activos"`

goes from 24 → 15 tokens (**37.5% saved**) on `gpt-4o` with `--translate`, vs only 12.5% without.

## Install

```bash
pip install promptminify
```

> On PyPI the package is `promptminify` (because `promptmin` was already taken), but the CLI command and Python import name are both `promptmin`:
>
> ```bash
> promptmin --help
> ```
> ```python
> from promptmin import minify
> ```

### From source (development)

```bash
git clone https://github.com/DelvyG/promptmin.git
cd promptmin
pip install -e ".[dev]"
```

## Usage

### CLI

```bash
# Inline
promptmin run "Please, I would like you to build a function step by step"

# From file / clipboard / stdin
promptmin run --file prompt.txt
promptmin run --clipboard --out-clipboard
cat prompt.txt | promptmin run

# With domain dictionaries
promptmin run -d web,backend "Improve the user experience and add JWT authentication"

# Target a specific model's tokenizer
promptmin run -T claude "..."
promptmin run -T gpt-4o "..."
promptmin run -T gemini "..."

# List all available tokenizers
promptmin tokenizers

# Spanish with automatic EN technical translation
promptmin run -t "Por favor, desarrolla una función paso a paso para la base de datos"

# Aggressive mode (strips more filler)
promptmin run -m aggressive "..."

# List available domain dictionaries
promptmin domains

# Benchmark on a corpus
promptmin benchmark examples/corpus_domains.txt -d web,backend,devops,data,ai

# Just count tokens
promptmin count "hello world"
```

### As a library

```python
from promptmin import minify
from promptmin.tokens import savings

result = minify(
    "Please improve the user experience on mobile responsive devices",
    domains=["web"],
)
print(result["minified"])
print(savings(result["original"], result["minified"]))
# {'before': 11, 'after': 7, 'saved': 4, 'pct': 36.4}
```

## How it works

```
┌─────────────┐
│  Your text  │
└──────┬──────┘
       ▼
┌─────────────────────┐
│ 1. Detect language  │  es / en (cheap heuristic)
└──────┬──────────────┘
       ▼
┌─────────────────────────────────────┐
│ 2. Domain dicts (highest priority)  │  e.g. "user experience" -> "UX"
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────┐
│ 3. Language dict        │  "please" -> "", "configuration" -> "config"
└──────┬──────────────────┘
       ▼
┌───────────────────────────────────┐
│ 4. ES→EN translation (optional)   │  "desarrolla" -> "build"
└──────┬────────────────────────────┘
       ▼
┌─────────────────────┐
│ 5. Stopword strip   │
└──────┬──────────────┘
       ▼
┌─────────────────────┐
│ 6. Whitespace clean │
└──────┬──────────────┘
       ▼
┌──────────────────────────────┐
│  Minified output + stats     │
└──────────────────────────────┘
```

**The validator.** Every step applies rules one at a time. Before accepting a substitution, it calls `tiktoken.encode()` on before/after. If tokens didn't drop, the rule is discarded. This is why PromptMin can't make your prompt worse.

## Dictionary architecture

```
src/promptmin/dicts/
├── en.yaml              General English rules
├── es.yaml              General Spanish rules
├── es_en.yaml           Spanish → English technical translation
└── domains/
    ├── ai.yaml          LLM / RAG / CoT / fine-tuning / embeddings
    ├── backend.yaml     API / JWT / ORM / middleware / queues
    ├── data.yaml        ETL / warehouses / KPIs / schemas
    ├── devops.yaml      CI/CD / Kubernetes / SLO / observability
    └── web.yaml         UX / UI / SPA / PWA / responsive
```

Each file is plain YAML: `"long phrase": "short version"`. No code required to contribute a new domain — drop a YAML file in `dicts/domains/` and it's automatically picked up by `promptmin domains`.

## Roadmap

- [x] **Phase 1** — MVP CLI (EN + ES dicts, tiktoken-validated)
- [x] **Phase 2** — Benchmark on real corpus, `lite` / `aggressive` / `translate` modes
- [x] **Phase 2.5** — Domain dictionaries (`web`, `backend`, `devops`, `data`, `ai`)
- [x] **Phase 3** — Multi-tokenizer support: GPT-4o / GPT-4 / Claude / Gemini
- [x] **Phase 3.5** — Spanish phrase-level translation (`es_en_phrases.yaml`)
- [ ] **Phase 3.6** — Official SDK integration for exact Claude/Gemini counts (optional extras)
- [ ] **Phase 3.6** — More phrase patterns based on real-usage corpora
- [ ] **Phase 4** — VSCode extension ("Minify Selection" + keybinding)
- [ ] **Phase 4** — More domains: `mobile`, `security`, `gamedev`, `finance`
- [ ] **Phase 4** — Domain auto-detection from prompt content

## Contributing

Contributions are very welcome — especially new domain dictionaries and language support. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

The lowest-friction contribution is a **new domain YAML**: no Python, no tests, just curated phrases.

## License

[MIT](LICENSE) © DelvyG
