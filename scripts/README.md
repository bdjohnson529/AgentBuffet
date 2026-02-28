# Scripts

Scripts to pull financial data from the internet for use by Claude or research pipelines. All use **free** data sources (no API keys unless noted).

## Setup

From the repo root:

```bash
pip install -r requirements.txt
```


## Scripts

### `get_news.py`

Fetches financial news for a company via **Yahoo Finance RSS** (no API key).

```bash
python scripts/get_news.py AAPL
python scripts/get_news.py AAPL --limit 20 --format markdown -o stocks/AAPL/news.json
```

**Options:** `--limit`, `--format` (json | markdown), `-o` / `--out`

---

### `get_financials.py`

Fetches financial metrics and statement snapshots via **yfinance** (Yahoo Finance; no API key).

```bash
python scripts/get_financials.py AAPL
python scripts/get_financials.py AAPL --format markdown -o stocks/AAPL/financials.json
```

**Output includes:** valuation (P/E, P/B, EV), margins, revenue, cash flow, debt, ratios, and income/balance/cashflow statement snapshots.

**Options:** `--format` (json | markdown), `-o` / `--out`

---

### `get_filings.py`

Fetches **SEC EDGAR** filings list (10-K, 10-Q, 8-K, etc.) for a company. No API key.

```bash
python scripts/get_filings.py AAPL
python scripts/get_filings.py AAPL --forms 10-K,10-Q,8-K --limit 20 -o stocks/AAPL/filings.json
```

**Options:** `--forms` (comma-separated), `--limit`, `--format` (json | markdown), `-o` / `--out`

---

### `get_insider.py`

Fetches recent **insider transactions** (Form 4 filings) from SEC EDGAR.

```bash
python scripts/get_insider.py AAPL
python scripts/get_insider.py AAPL --limit 15 -o stocks/AAPL/insider.json
```

**Options:** `--limit`, `--format` (json | markdown), `-o` / `--out`

---

### `get_prices.py`

Fetches **historical price** data (OHLCV) and summary stats (return, volatility) via yfinance.

```bash
python scripts/get_prices.py AAPL
python scripts/get_prices.py AAPL --days 90 --format markdown -o stocks/AAPL/prices.json
```

**Options:** `--days`, `--format` (json | markdown), `-o` / `--out`

---

### `get_estimates.py`

Fetches **analyst estimates**, price targets, and next earnings date via yfinance.

```bash
python scripts/get_estimates.py AAPL
python scripts/get_estimates.py AAPL --format markdown -o stocks/AAPL/estimates.json
```

**Options:** `--format` (json | markdown), `-o` / `--out`

---

### `get_peers.py`

Fetches **comparable/peer tickers** for a company via yfinance.

```bash
python scripts/get_peers.py AAPL
python scripts/get_peers.py AAPL --format markdown -o stocks/AAPL/peers.json
```

**Options:** `--format` (json | markdown), `-o` / `--out`

---

## Use with Claude

- Run scripts and pass output into context, or
- Save to `stocks/[TICKER]/` and reference from `research.md` / analysis.
- **SEC scripts:** EDGAR asks for a descriptive User-Agent; the scripts set one. Stay under ~10 requests/second.
