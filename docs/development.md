# Development Commands

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

## Sprint 1 Smoke Commands

```bash
python scripts/run_ingestion.py --help
python scripts/build_knowledge_index.py --help
python scripts/run_pipeline.py --help
```

## Run Tests

```bash
python -m unittest discover -s tests -v
```
