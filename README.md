# FraudVault

Document and image forgery detection platform. FraudVault provides a REST API for detecting tampered images and PDFs using forensic analysis techniques including Error Level Analysis (ELA), clone detection, EXIF metadata analysis, AI-generated image detection, font consistency checks, and OCR text diffing.

## Architecture

```
Client (JWT / API Key)
        │
        ▼
   FastAPI API ──► PostgreSQL (jobs, users, results)
        │              │
        ├──► Redis (rate limits, Celery broker)
        │
        ├──► Celery Worker ──► Detection Engine
        │                           │
        ├──► Cloudflare R2 ◄────────┘ (files, heatmaps)
        │
        └──► Stripe (usage metering)
```

## Prerequisites

- Python 3.11 (recommended; 3.12 supported; avoid 3.14 — several ML/PDF deps lack wheels)
- PostgreSQL 14+
- Redis 6+
- Tesseract OCR (`brew install tesseract` on macOS)

## Local Setup

### 1. System dependencies (macOS)

```bash
brew install postgresql@16 redis tesseract
brew services start postgresql@16
brew services start redis
```

### 2. Create database

```bash
psql postgres -c "CREATE USER fraudvault WITH PASSWORD 'password';"
psql postgres -c "CREATE DATABASE fraudvault OWNER fraudvault;"
```

### 3. Python environment

```bash
cd fraudvault
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start services

```bash
# Terminal 1 — API server
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

API docs: http://localhost:8000/docs

## Running Tests

```bash
pytest -v
```

Tests use an in-memory SQLite database and local file storage — no PostgreSQL or Redis required.

### Benchmark accuracy gate

```bash
pytest tests/test_benchmark_accuracy.py -v
```

The benchmark suite (`tests/benchmark/`) runs labeled fixtures through the detection engine and asserts **≥ 90% accuracy**. Fixtures are auto-generated on first `pytest` run and include authentic phone photos (with EXIF), tampered JPEGs, synthetic AI PNGs, and a ChatGPT-generated reference image (`ai/sukhbir_chatgpt.png`).

### Detection thresholds

Thresholds are configurable via `.env` (defaults shown):

| Variable | Default | Meaning |
|----------|---------|---------|
| `AI_GENERATED_THRESHOLD` | 0.40 | `effective_ai` ≥ this → `ai_generated` |
| `AI_INCONCLUSIVE_THRESHOLD` | 0.30 | `effective_ai` ≥ this → `inconclusive` |
| `FORENSIC_TAMPERED_THRESHOLD` | 0.75 | Forensic score above → `tampered` |
| `FORENSIC_INCONCLUSIVE_THRESHOLD` | 0.55 | Highest forensic score → `inconclusive` |

`effective_ai = max(ai_generated, synthetic)` — synthetic heuristics (PNG/no-EXIF, AI dimensions, smoothness) boost detection of ChatGPT/DALL-E images even when ML models are unavailable.

### Interpreting results

- **`confidence`** and **`risk_score`** measure **suspicion level** (higher = more suspicious), not confidence that a file is authentic.
- **`scores.ai_generated`** — ML ensemble score (max across loaded HuggingFace models).
- **`scores.synthetic`** — heuristic score for generator-like patterns.
- **`scores.effective_ai`** — combined AI signal used for verdict.
- **`scores.model_used`** — e.g. `ensemble:Organika/sdxl-detector,...` or `null` if models not loaded.

## Postman Collection

Import the collection and local environment into Postman:

1. **Collection:** `postman/FraudVault.postman_collection.json`
2. **Environment:** `postman/FraudVault.local.postman_environment.json`

Select the **FraudVault Local** environment, then run requests in this order:

1. Health Check
2. Register (or Login)
3. Create API Key
4. Detect (Sync) — select a `.jpg` or `.pdf` file in the Body tab
5. Get Usage
6. Detect (Async) → Get Result (requires Celery worker)

Collection variables (`access_token`, `api_key`, `job_id`, etc.) are auto-populated by test scripts after Register, Create API Key, and Detect requests.

## API Usage

### Register and get a token

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123","full_name":"Jane Doe"}'
```

### Detect a file (sync mode)

```bash
curl -X POST http://localhost:8000/v1/detect \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@document.jpg" \
  -F "async_mode=false"
```

### Create an API key

```bash
curl -X POST http://localhost:8000/v1/keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Production","environment":"live"}'
```

### Detect with API key

```bash
curl -X POST http://localhost:8000/v1/detect \
  -H "X-API-Key: fv_live_..." \
  -F "file=@document.pdf" \
  -F "async_mode=true"
```

### Python SDK example

```python
import httpx

API_KEY = "fv_live_your_key_here"
BASE_URL = "http://localhost:8000"

with open("document.jpg", "rb") as f:
    response = httpx.post(
        f"{BASE_URL}/v1/detect",
        headers={"X-API-Key": API_KEY},
        files={"file": ("document.jpg", f, "image/jpeg")},
        data={"async_mode": "false"},
    )
    result = response.json()
    print(f"Verdict: {result['verdict']} (confidence: {result['confidence']})")
```

### JavaScript example

```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);
formData.append("async_mode", "false");

const response = await fetch("http://localhost:8000/v1/detect", {
  method: "POST",
  headers: { "X-API-Key": "fv_live_your_key_here" },
  body: formData,
});
const result = await response.json();
console.log(result.verdict, result.risk_score);
```

## Deployment (Railway)

1. Create a Railway project with PostgreSQL and Redis plugins
2. Set environment variables from `.env.example`
3. Deploy with start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add a worker service: `celery -A app.workers.celery_app worker --loglevel=info`
5. Run migrations: `alembic upgrade head`

## Project Structure

```
fraudvault/
├── app/
│   ├── api/v1/          # REST endpoints
│   ├── detection/       # Forensics engine
│   ├── models/          # SQLAlchemy ORM
│   ├── services/        # Business logic
│   ├── workers/         # Celery tasks
│   └── middleware/      # Auth + rate limiting
├── alembic/             # DB migrations
├── postman/             # Postman collection + environment
└── tests/               # pytest suite
```

## License

Proprietary — FraudVault Platform
