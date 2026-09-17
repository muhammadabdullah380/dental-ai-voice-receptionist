# Portfolio API

FastAPI backend for Muhammad ABDULLAH's React portfolio.

## Run

From this directory:

```powershell
..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

API docs: http://127.0.0.1:8001/docs

Endpoints:

- `GET /health`
- `GET /api/projects`
- `GET /api/experience`
- `POST /api/contact`

The default database is a local SQLite file named `portfolio.db`. Set `PORTFOLIO_DATABASE_URL` for PostgreSQL in production.
