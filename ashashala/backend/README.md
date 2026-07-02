# AshaShala Backend

FastAPI-based backend for the AshaShala Agentic AI Tutoring Platform.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (Neon free tier)
- Qdrant Cloud (free tier)
- Cloudflare R2 (free tier)
- Google AI Studio API key (Gemini)
- NVIDIA NGC API key (NIM)

### Installation

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env with your credentials
```

### Running the Server

```bash
# Development with auto-reload
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/api/v1/health

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app factory
│   ├── core/
│   │   ├── config.py           # Pydantic Settings
│   │   └── exceptions.py       # Custom exceptions
│   ├── db/
│   │   ├── session.py          # Async SQLAlchemy session
│   │   └── tenant_filter.py    # Automatic tenant isolation
│   ├── services/
│   │   ├── model_registry.py   # Model registry loader
│   │   ├── gemini_client.py    # Gemini API client
│   │   ├── nvidia_client.py    # NVIDIA NIM client
│   │   ├── llm_router.py       # Task-based LLM routing
│   │   ├── r2_client.py        # Cloudflare R2 client
│   │   └── rag/
│   │       └── store.py        # Qdrant vector store
│   ├── models/                 # SQLAlchemy models (Phase 2+)
│   ├── api/                    # API routes (Phase 2+)
│   └── schemas/                # Pydantic schemas (Phase 2+)
├── tests/
│   ├── test_phase1_health.py   # Health endpoint tests
│   └── test_phase1_llm_router.py  # LLM router tests
├── config/
│   └── model_registry.yaml     # Model ID mappings
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── .gitignore
```

## Configuration

All configuration is via environment variables (see `.env.example`). Key settings:

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google AI Studio API key | Yes |
| `NVIDIA_API_KEY` | NVIDIA NGC API key | Yes |
| `DATABASE_URL` | Neon Postgres connection string | Yes |
| `QDRANT_URL` | Qdrant Cloud cluster URL | Yes |
| `QDRANT_API_KEY` | Qdrant Cloud API key | Yes |
| `R2_ACCOUNT_ID` | Cloudflare R2 account ID | Yes |
| `R2_ACCESS_KEY_ID` | R2 access key | Yes |
| `R2_SECRET_ACCESS_KEY` | R2 secret key | Yes |
| `R2_BUCKET_NAME` | R2 bucket name | Yes |
| `R2_PUBLIC_URL` | R2 public URL base | Yes |
| `JWT_SECRET` | JWT signing secret (32+ chars) | Yes |
| `JWT_REFRESH_SECRET` | JWT refresh secret (32+ chars) | Yes |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | Yes |
| `SENTRY_DSN` | Sentry DSN for error tracking | No |

## Model Registry

Model IDs are configured in `config/model_registry.yaml`. This file maps roles to specific model IDs for each provider. Update from the [NVIDIA catalog](https://build.nvidia.com/models?pageSize=96&filters=publisher%3Anvidia) when models are deprecated.

Roles:
- `fast_chat` - Quick responses, general tutoring
- `reasoning` - Complex reasoning, lesson planning
- `multilingual_indic` - Indian language support
- `vision` - Image understanding
- `ocr` - Optical character recognition
- `asr` - Automatic speech recognition
- `embeddings` - Text embeddings for RAG
- `safety_jailbreak` - Content safety

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_phase1_health.py -v
```

## Health Check

The `/api/v1/health` endpoint returns status of all services:

```json
{
  "status": "healthy|degraded|unhealthy",
  "version": "0.1.0",
  "environment": "development",
  "checks": {
    "database": true,
    "gemini": true,
    "nvidia": true,
    "qdrant": true,
    "r2": true,
    "llm_router": true
  }
}
```

## Architecture Highlights

### Automatic Tenant Isolation
All database queries are automatically filtered by `school_id` via SQLAlchemy event listeners. Developers don't need to manually add WHERE clauses.

### LLM Routing
The `LLMRouter` automatically selects the best provider/model for each task with fallback support. See `ROUTING_TABLE` in `llm_router.py`.

### Free-Tier Optimized
All external services use free tiers:
- Neon Postgres: 0.5 GB
- Qdrant Cloud: 1 GB
- Cloudflare R2: 10 GB
- Gemini API: Free tier
- NVIDIA NIM: Free tier (~40 req/min)

## Development

### Code Style

```bash
# Format
black app tests

# Lint
ruff check app tests

# Type check
mypy app
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## Deployment

### Render (Recommended)

1. Connect GitHub repo to Render
2. Create Web Service
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example`

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## License

MIT License - see LICENSE file for details.