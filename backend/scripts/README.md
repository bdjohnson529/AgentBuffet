# Scripts

Scripts to pull financial data from the internet for use by Claude or research pipelines. All use **free** data sources (no API keys unless noted).

## Setup

From the repo root:

```bash
pip install -r backend/requirements.txt
```

### Secrets / API keys

Copy the example environment file and fill in your keys:

```bash
cp .env.example .env
```

Then set `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` in `.env`. The report generator scripts will auto-load `.env` if present.

## Master script (recommended)

**`backend/run.py`** — Run every data script for every ticker in one go. No need to pick scripts or tickers manually.

From repo root:

```bash
python backend/run.py
```

- **Tickers:** Read from `stocks.txt` (one per line, optional `$` prefix). Override with `--tickers AAPL,MSFT,GOOGL`.
- **Output:** Each script writes into `stocks/[TICKER]/` (e.g. `news.json`, `financials.json`, `filings.json`, etc.). A run summary is written to `reports/data_run_YYYY-MM-DD.md`.
- **Options:** `--dry-run` (print what would run), `--skip-reports-summary` (do not write the summary to reports).
- **Report generation defaults:** Per-ticker LLM reports and the portfolio rollup are **enabled by default**. Disable with `--no-generate-reports` and/or `--no-generate-portfolio-report`.

Use this instead of invoking individual scripts when you want a full data refresh for all tickers.

---

## Individual scripts

### `get_news.py`

Fetches financial news for a company via **Yahoo Finance RSS** (no API key).

```bash
python backend/scripts/get_news.py AAPL
python backend/scripts/get_news.py AAPL --limit 20 --format markdown -o stocks/AAPL/news.json
```

**Options:** `--limit`, `--format` (json | markdown), `-o` / `--out`

---

### `get_financials.py`

Fetches financial metrics and statement snapshots via **yfinance** (Yahoo Finance; no API key).

```bash
python backend/scripts/get_financials.py AAPL
python backend/scripts/get_financials.py AAPL --format markdown -o stocks/AAPL/financials.json
```

**Output includes:** valuation (P/E, P/B, EV), margins, revenue, cash flow, debt, ratios, and income/balance/cashflow statement snapshots.

**Options:** `--format` (json | markdown), `-o` / `--out`

---

### `get_filings.py`

Fetches **SEC EDGAR** filings list (10-K, 10-Q, 8-K, etc.) for a company. No API key.

```bash
python backend/scripts/get_filings.py AAPL
python backend/scripts/get_filings.py AAPL --forms 10-K,10-Q,8-K --limit 20 -o stocks/AAPL/filings.json
```

**Options:** `--forms` (comma-separated), `--limit`, `--format` (json | markdown), `-o` / `--out`

---

### `get_insider.py`

Fetches recent **insider transactions** (Form 4 filings) from SEC EDGAR.

```bash
python backend/scripts/get_insider.py AAPL
python backend/scripts/get_insider.py AAPL --limit 15 -o stocks/AAPL/insider.json
```

**Options:** `--limit`, `--format` (json | markdown), `-o` / `--out`

---

### `get_prices.py`

Fetches **historical price** data (OHLCV) and summary stats (return, volatility) via yfinance.

```bash
python backend/scripts/get_prices.py AAPL
python backend/scripts/get_prices.py AAPL --days 90 --format markdown -o stocks/AAPL/prices.json
```

**Options:** `--days`, `--format` (json | markdown), `-o` / `--out`

---

### `get_estimates.py`

Fetches **analyst estimates**, price targets, and next earnings date via yfinance.

```bash
python backend/scripts/get_estimates.py AAPL
python backend/scripts/get_estimates.py AAPL --format markdown -o stocks/AAPL/estimates.json
```

**Options:** `--format` (json | markdown), `-o` / `--out`

---

### `get_peers.py`

Fetches **comparable/peer tickers** for a company via yfinance.

```bash
python backend/scripts/get_peers.py AAPL
python backend/scripts/get_peers.py AAPL --format markdown -o stocks/AAPL/peers.json
```

**Options:** `--format` (json | markdown), `-o` / `--out`

---

## Use with Claude

- **Preferred:** Run `python backend/run.py` once to pull all data into `stocks/[TICKER]/`, then reference those files from `research.md` / analysis.
- Alternatively run individual scripts and pass output into context, or save to `stocks/[TICKER]/`.
- **SEC scripts:** EDGAR asks for a descriptive User-Agent; the scripts set one. Stay under ~10 requests/second. The master script adds a short delay between SEC script runs.

---

## Intelligence layer (LLM-generated reports)

These scripts read the existing JSON artifacts under `stocks/<TICKER>/` and generate reports matching `templates/report.md`.

### Per-ticker report

Generates:
- `stocks/<TICKER>/report.json` (structured model output + metadata)
- `stocks/<TICKER>/report.md` (Markdown formatted like `templates/report.md`)
- Crawls latest **10-K/10-Q** and caches:
  - `stocks/<TICKER>/filing_latest.html`
  - `stocks/<TICKER>/filing_latest.txt`
  - `stocks/<TICKER>/filing_latest.meta.json`

```bash
python backend/scripts/generate_report.py AAOI --provider either
```

**Provider selection:**
- OpenAI: set `OPENAI_API_KEY` (optional `OPENAI_MODEL`)
- Anthropic: set `ANTHROPIC_API_KEY` (optional `ANTHROPIC_MODEL`)

Options:
- `--provider openai|anthropic|either`
- `--model <name>`
- `--skip-filing-fetch` (offline; uses cached filing if present)
- `--refresh-filing`

### Portfolio rollup report

Reads `stocks/<TICKER>/report.json` files (or regenerates missing ones if asked) and writes a rollup under `reports/`:

```bash
python backend/scripts/generate_portfolio_report.py --regenerate-missing --provider either
```

