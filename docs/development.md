# Development Commands

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

## Database

Set `DATABASE_URL` in your environment (Supabase Postgres in shared environments).

```bash
# Apply migrations
python scripts/apply_migrations.py
```

## Sprint 1 Smoke Commands

```bash
python scripts/run_ingestion.py --help
python scripts/build_knowledge_index.py --help
python scripts/run_pipeline.py --help
```

```bash
# DB-backed ingestion examples
python scripts/run_ingestion.py --source email --input-file data/samples/email_event.json --run-migrations
python scripts/run_ingestion.py --batch-file data/samples/mixed_source_batch.json --run-migrations
```

## Run Tests

```bash
python -m unittest discover -s tests -v
```
