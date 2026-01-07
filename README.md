# Jira Sprint API (FastAPI)

A production-grade(ish) FastAPI service to fetch and **resolve sprint details** from **Jira Software Data Center**
using a **Personal Access Token (PAT)**.

## Features
- Smart endpoint: `/v1/sprints/details` (resolve by sprint_id, sprint_name, issue_key, date, date range)
- Direct endpoint: `/v1/sprints/{sprint_id}`
- List endpoint: `/v1/boards/{board_id}/sprints`
- Retries with exponential backoff + jitter (safe transient errors)
- Structured-ish logging + correlation/request-id
- Centralized error handling with consistent error schema
- Pagination loops for boards with many sprints
- Optional in-memory TTL caching for board sprint lists and Sprint custom-field discovery
- Health endpoints: `/health`, `/ready`
- Dockerfile included (optional)

## Requirements
- Python 3.11+
- Jira Software (Data Center) with Agile REST API enabled
- PAT with permissions to read boards/sprints/issues

## Configure
Copy `.env.example` to `.env` and fill values.

## Run locally
### Option A: simple run script
```bash
bash scripts/run_local.sh
```

### Option B: directly
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open docs:
- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

## Example calls

### Smart sprint details
Resolve by sprint id:
```bash
curl "http://localhost:8000/v1/sprints/details?sprint_id=123"
```

Resolve by name:
```bash
curl "http://localhost:8000/v1/sprints/details?sprint_name=Sprint%2015"
```

Resolve by date (DDMMYYYY):
```bash
curl "http://localhost:8000/v1/sprints/details?date=07012026"
```

Resolve by date range:
```bash
curl "http://localhost:8000/v1/sprints/details?start_date=01012026&end_date=31012026&mode=list"
```

Resolve by issue key:
```bash
curl "http://localhost:8000/v1/sprints/details?issue_key=ABC-123"
```

### Direct fetch
```bash
curl "http://localhost:8000/v1/sprints/123"
```

### List board sprints
```bash
curl "http://localhost:8000/v1/boards/45/sprints?state=closed&maxResults=50"
```

## Notes on issue_key behavior
- Default returns **one** sprint (latest by end/complete/start date).
- If `mode=list`, returns all discovered sprints from the issue's Sprint field.

## License
Internal / sample project.
