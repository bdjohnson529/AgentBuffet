# AgentBuffet

Investment analyst workspace: stock data scripts and research pipelines. See [CLAUDE.md](CLAUDE.md) for role and modes (Research, Analysis, Portfolio).

## Environment

To enable LLM calls, copy `.env.example` to `.env` at the repo root and set at least one provider key:

```bash
cp .env.example .env
```



## Backend

This creates `backend/.venv` and installs dependencies from `backend/requirements.txt`. Then activate and run:

```bash
./backend/setup.sh
source backend/.venv/bin/activate
python backend/run.py
```

## Frontend

From the repo root:

```bash
cd frontend
npm install
npm run dev
```

### Notes

- `.venv` is in `.gitignore`; it is not committed.
- Requirements are listed in `backend/requirements.txt`.
- For script usage and data refresh, see [backend/scripts/README.md](backend/scripts/README.md).
