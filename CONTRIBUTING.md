# Contributing

Reconcile is currently a solo portfolio project. Issues and suggestions are welcome, but pull requests may not be actively accepted.

## Local setup

Install the project in editable mode with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Create and seed a local fake demo database:

```powershell
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db
python scripts/run_reconcile.py import-bank examples/demo_company/bank_statement.csv --db-path exports/reconcile.db
```

Run tests and linting:

```powershell
python -m pytest
python -m ruff check .
```

## Data safety

Use fake demo data only. Do not add real bank statements, real customer data, private financial records, API credentials, secrets, or local generated databases.

Do not commit:

```text
exports/reconcile.db
.pytest_cache/
__pycache__/
*.pyc
*.pkl
*.joblib
.env
.streamlit/secrets.toml
.coverage
htmlcov/
```
