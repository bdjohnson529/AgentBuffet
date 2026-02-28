# AgentBuffet

Investment analyst workspace: stock data scripts and research pipelines. See [CLAUDE.md](CLAUDE.md) for role and modes (Research, Analysis, Portfolio).

## Virtual environment setup

Use a virtual environment so project dependencies don’t pollute your system Python.

## Web UI (browse `stocks/` in a browser)

This repo includes a simple React/Vite frontend for browsing the generated JSON under `stocks/<TICKER>/`.

From the repo root:

```bash
cd frontend
npm install
npm run dev
```

Then open the URL printed by Vite (typically `http://localhost:5173`).

### Chat + report generation (frontend intelligence)

The UI now includes an **Analysis** tab where you can:

- Chat with the model about valuation/decision using your `thesis.md` + `stocks/<TICKER>/*.json`
- Generate `stocks/<TICKER>/report.json` and `report.md` from the browser (writes files via the local Vite dev server)

To enable LLM calls, copy `.env.example` to `.env` at the repo root and set at least one provider key:

```bash
cp .env.example .env
```

To refresh the data the UI reads:

```bash
./backend/setup.sh
source backend/.venv/bin/activate
python backend/run.py
```

### Option 1: Setup script (recommended)

From the repo root:

```bash
./backend/setup.sh
```

This creates `backend/.venv` and installs dependencies from `backend/requirements.txt`. Then activate and run:

```bash
source backend/.venv/bin/activate
python backend/run.py
```

To leave the virtual environment:

```bash
deactivate
```

### Option 2: Manual setup

From the repo root:

```bash
# Create the virtual environment
python3 -m venv backend/.venv

# Activate it (macOS/Linux)
source backend/.venv/bin/activate

# On Windows (Command Prompt)
# .venv\Scripts\activate.bat

# On Windows (PowerShell)
# .venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt
```

After that, run `python backend/run.py` (or individual scripts under `backend/scripts/`). When finished, run `deactivate`.

### Notes

- `.venv` is in `.gitignore`; it is not committed.
- Requirements are listed in `backend/requirements.txt`.
- For script usage and data refresh, see [backend/scripts/README.md](backend/scripts/README.md).
