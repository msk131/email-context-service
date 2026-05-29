# Email Context Service

A concise backend for storing and summarizing client email context for CPA firms.

Quick start: see the quickstart guide — [docs/QUICKSTART.md](docs/QUICKSTART.md)

Documentation

- [docs/QUICKSTART.md](docs/QUICKSTART.md) — Quick start
- [docs/INITIAL_DATA.md](docs/INITIAL_DATA.md) — Initial DB data & script
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Architecture notes
- [docs/DDD_ARCHITECTURE.md](docs/DDD_ARCHITECTURE.md) — DDD design reasoning
- [docs/MODULE_MAP.md](docs/MODULE_MAP.md) — Module responsibilities
- [docs/PACKAGE_REFERENCE.md](docs/PACKAGE_REFERENCE.md) — Package & runtime details

Run locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

