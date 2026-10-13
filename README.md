# proj-llama-parse

A table-extraction pipeline that pulls **every table** out of a 68-page PDF
financial report using the **LlamaParse v2 API** (LlamaIndex) and saves
**one CSV per table**, named with its source page for full traceability.

---

## Overview

**The problem.** Financial reports mix long prose with dozens of tables.
Extracting those tables by hand is slow and error-prone; naive text dump
(`pdftotext`) breaks column structure and loses the table/text boundary.

**The solution.** A small, modular Python pipeline that:

1. Sends the PDF to LlamaParse v2 and requests the `items` view — a typed
   tree of every page element (text, headings, tables, images);
2. Filters strictly for `type == "table"` items with valid CSV content;
3. Writes **one CSV per table** as `tabelas/tabela_pNNN_NN.csv`
   (e.g. `tabela_p065_03.csv` = page 65, third table on that page).

**Verified result.** A full run over `resultado.pdf` (68 pages) produced
**45 CSV files across 32 pages**, with values spot-checked line-by-line
against the source document.

---

## Key Highlights

- **Clean separation of concerns** — all network I/O lives in a single module
  (`parser_llama.py`); business rules (`tabelas.py`) are pure functions.
- **20 offline unit tests** — run in ~0.03s with zero API credits; the
  pipeline receives its parse function via dependency injection, so tests
  inject a fake and never touch the network.
- **Structured logging** — progress on the console (`INFO`) and a full
  debug trail with tracebacks in `extrator.log` (`DEBUG`).
- **Secrets never touch the code** — the API key is read from `.env`
  (gitignored, `chmod 600`), validated on startup, and never printed.
- **Fail fast, fail loud** — configuration is validated before any API call;
  the process returns exit code `0` on success and `1` on any failure.
- **Cost-aware parsing** — `tier="agentic"` (AI models) combined with the
  cost optimizer routes simple pages to cheaper processing and spends
  premium credits only on complex, table-heavy pages.
- **Migrated to Parse v2** — the discontinued v1 API (`llama-parse` package)
  was replaced by the official `llama-cloud` SDK v2; the change is isolated
  to one module.

---

## Architecture

```
main.py                        ← entry point: small on purpose (exit codes 0/1)
└── extrator/
    ├── config.py              ← loads .env, validates key/tier/PDF/output folder
    ├── logging_config.py      ← logger: console (INFO) + file (DEBUG)
    ├── parser_llama.py        ← ONLY module that talks to the network (API v2)
    ├── tabelas.py             ← pure logic: filter, name and save tables
    └── pipeline.py            ← orchestration: API → filter → CSVs → summary
└── tests/                     ← 20 offline tests (pytest)
```

| Module               | Responsibility                              | Network access |
| -------------------- | ------------------------------------------- | -------------- |
| `config.py`          | Load `.env`, validate key, tier, PDF, paths | No             |
| `logging_config.py`  | Console + file logging setup                | No             |
| `parser_llama.py`    | Upload PDF, run parse job, return raw JSON  | **Yes**        |
| `tabelas.py`         | Filter tables, name files, write CSVs       | No             |
| `pipeline.py`        | Orchestrate the whole flow                  | No (injectable)|

### Data flow

```
resultado.pdf
      │
      ▼
LlamaParse v2  ── expand=["items"] ──►  raw JSON (pages → items)
      │
      ▼
extrair_tabelas()  ── filter type=="table" + csv  ──►  Tabela objects
      │
      ▼
salvar_tabela()  ──►  tabelas/tabela_p065_03.csv  (one file per table)
```

---

## Tech Stack

| Tool           | Version    | Why                                   |
| -------------- | ---------- | ------------------------------------- |
| Python         | 3.14       | Modern runtime                       |
| uv             | —          | Fast dependency/env manager          |
| `llama-cloud`  | >= 2.8     | Official LlamaParse v2 SDK           |
| pytest         | >= 8       | Test runner (offline suite)          |
| `python-dotenv`| >= 1.0     | `.env` secrets loading               |

---

## Getting Started

```bash
# 1) Install dependencies (once)
uv sync --dev

# 2) Create the secrets file (once)
cp .env.example .env      # then paste your key into LLAMA_CLOUD_API_KEY

# 3) Run the test suite (offline, no API credits spent)
uv run pytest

# 4) Run the real extraction (uses API credits)
uv run main.py
```

The API key lives **only** in `.env` (gitignored). If it is missing or
malformed, the program reports it and exits with code `1` before any
network call.

---

## Testing

### Philosophy

The suite is **100% offline and deterministic** — no network, no API credits,
no flaky timing. Two design decisions make this possible:

1. **Pure functions** — everything in `tabelas.py` (filtering, file naming,
   CSV writing, row/column counting) takes data in and returns data out.
2. **Dependency injection** — `executar_pipeline()` accepts the parse
   function as a parameter. Production passes the real API call; tests pass
   a fake that returns fixture JSON. No mock framework required.

Fixtures in `tests/conftest.py` replicate the exact JSON shape returned by
LlamaParse (pages, items, tables with/without CSV content).

### Test inventory — 20 tests

| File                | Tests | What it guarantees                                                                 |
| ------------------- | ----- | ---------------------------------------------------------------------------------- |
| `test_config.py`    | 7     | Missing key, malformed key, invalid tier, missing PDF all fail with clear errors; valid config loads key from `.env` and creates the output folder |
| `test_tabelas.py`   | 9     | Only tables with CSV content are extracted; page/index order preserved; malformed or empty JSON never crashes; deterministic file naming; CSV written verbatim as UTF-8; row/column counting; summary text |
| `test_pipeline.py`  | 4     | End-to-end orchestration with a fake parse function: correct files on disk, empty results handled, API errors propagate to the caller |

### Running the suite

```bash
uv run pytest
```

Expected output:

```
....................                                                     [100%]
20 passed in 0.03s
```

### Known limitation

The live API call is intentionally **not** covered by automated tests
(it would spend credits and depend on network). It is validated manually
via `uv run main.py` — the last full run extracted 45 tables from the
68-page report.

---

## Results

Last full run over `resultado.pdf` (68 pages):

- **45 tables** extracted
- **32 pages** contained at least one table
- Range: pages 2 through 66

Sample output (`tabelas/tabela_p065_03.csv`, verified against the PDF):

```csv
"3- Indicadores Sociais Externos","Valor","% sobre",,"Valor","% sobre",
,,"RO","RL",,"RO","RL"
"Projetos socioambientais voluntários","293","0,53","0,06","159","0,09","0,03"
```

---

## Configuration

All knobs live in `extrator/config.py`:

| Option            | Default     | Meaning                                                        |
| ----------------- | ----------- | -------------------------------------------------------------- |
| `tier`            | `agentic`   | AI level: `fast`, `cost_effective`, `agentic`, `agentic_plus` |
| `cost_optimizer`  | `True`      | Route simple pages to cheaper processing (agentic tiers only)  |
| `language`        | `pt`        | OCR language hint for the parser                               |

---

## Security Practices

- API key stored **only** in `.env` — gitignored and `chmod 600`
- Key is **never** logged or printed (paths and modes only)
- Startup validation rejects missing/malformed keys before any API call
- `.env.example` documents the required variable without exposing a real key
- Recommendation applied: exposed keys are rotated/revoked in the
  [LlamaCloud dashboard](https://cloud.llamaindex.ai)

---

## Engineering Notes

**Why Parse v2?** The original implementation used the `llama-parse` package
(v1 API), which has been discontinued by LlamaIndex and is rejected by newer
accounts. The migration replaced it with the official `llama-cloud` SDK v2;
because all API access was already isolated in `parser_llama.py`, the rest of
the codebase (and all 20 tests) was untouched.

**Logging.** Console shows progress (`INFO`); `extrator.log` captures the
full debug trail including tracebacks (`DEBUG`) — essential when a 68-page
parse fails.
