# AgentBuffet

Investment analyst workspace: stock data scripts and research pipelines. See [CLAUDE.md](CLAUDE.md) for role and modes (Research, Analysis, Portfolio).

## Virtual environment setup

Use a virtual environment so project dependencies don’t pollute your system Python.

## Web UI (browse `stocks/` in a browser)

This repo includes a simple React/Vite frontend for browsing the generated JSON under `stocks/<TICKER>/`.

From the repo root:

```bash
npm install
npm run dev
```

Then open the URL printed by Vite (typically `http://localhost:5173`).

To refresh the data the UI reads:

```bash
source .venv/bin/activate
python run.py
```

### Option 1: Setup script (recommended)

From the repo root:

```bash
./setup.sh
```

This creates `.venv` in the repo root and installs dependencies from `scripts/requirements.txt`. Then activate and run scripts:

```bash
source .venv/bin/activate
python run.py
```

To leave the virtual environment:

```bash
deactivate
```

### Option 2: Manual setup

From the repo root:

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it (macOS/Linux)
source .venv/bin/activate

# On Windows (Command Prompt)
# .venv\Scripts\activate.bat

# On Windows (PowerShell)
# .venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r scripts/requirements.txt
```

After that, run scripts with the venv active (e.g. `python scripts/run_all.py`). When finished, run `deactivate`.

### Notes

- `.venv` is in `.gitignore`; it is not committed.
- Requirements are listed in `scripts/requirements.txt`.
- For script usage and data refresh, see [scripts/README.md](scripts/README.md).
