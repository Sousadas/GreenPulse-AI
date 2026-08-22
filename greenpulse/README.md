# GreenPulse AI

**Smart Renewable Energy Asset Monitoring for Kutch & Banaskantha, Gujarat, India**

Agentic AI platform for intelligent monitoring, forecasting, predictive maintenance, and grid-integration optimization of hybrid solar-wind renewable energy parks.

---

## IBM Cloud Architecture

```
IBM Cloud IAM (API Key)
        ↓
IBM watsonx.ai Runtime  (us-south)
        ↓
IBM Granite  (ibm/granite-4-h-small)
        ↓
GreenPulse watsonx_service.py
        ↓
Orchestrator Agent  →  Asset / Maintenance / Grid / Forecast Agents
        ↓
FastAPI backend  (http://localhost:8000)
        ↓
React dashboard  (http://localhost:5173)
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp greenpulse/backend/.env.example greenpulse/backend/.env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `WATSONX_API_KEY` | **Yes** | IBM Cloud IAM API key — obtain from https://cloud.ibm.com/iam/apikeys |
| `WATSONX_PROJECT_ID` | **Yes** | watsonx.ai project ID (`c7b0f97f-cac0-49ee-9dca-6cb12f6c7d2d`) |
| `WATSONX_URL` | Yes | `https://us-south.ml.cloud.ibm.com` |
| `IBM_REGION` | Yes | `us-south` |
| `WATSONX_MODEL_ID` | No | Default: `ibm/granite-4-h-small` |
| `AI_MODE` | No | `ibm` / `simulation` / `hybrid` (default: `hybrid`) |
| `DATA_SOURCE_MODE` | No | `SIMULATED` / `LIVE` / `HISTORICAL` (default: `SIMULATED`) |

> **NEVER commit `.env` to Git.** It is listed in `.gitignore`.  
> **NEVER share or log `WATSONX_API_KEY`.**

---

## How to Configure the API Key

1. Go to [IBM Cloud → IAM → API Keys](https://cloud.ibm.com/iam/apikeys)
2. Create or rotate an API key scoped to your watsonx.ai project
3. Open `greenpulse/backend/.env`
4. Set: `WATSONX_API_KEY=<your key here>`
5. Restart the backend

---

## How to Run the Backend

```bash
cd greenpulse/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # then edit .env and add your API key
uvicorn app.main:app --reload --port 8000
```

---

## How to Run the Frontend

```bash
cd greenpulse/frontend
npm install
npm run dev
# Dashboard: http://localhost:5173
```

---

## How to Test IBM Connectivity

After adding your API key:

```bash
# 1. Health check (no generation)
curl http://localhost:8000/api/health/ai

# Expected when configured:
# { "status": "CONFIGURED", "available": true, "effective_mode": "ibm", ... }

# 2. Test generation (sends a real prompt to IBM Granite)
curl -X POST http://localhost:8000/api/ai/test \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Briefly describe the GreenPulse renewable energy platform."}'

# 3. Full AI assistant query
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the current grid status?"}'
```

---

## AI Modes

| Mode | Behavior |
|------|----------|
| `ibm` | Always calls IBM Granite. Returns error if unavailable. |
| `simulation` | Returns deterministic local stub. No IBM call. Good for development. |
| `hybrid` | Uses IBM Granite when `WATSONX_API_KEY` is set and valid. Falls back to simulation otherwise. **Default.** |

Set via `.env`:
```
AI_MODE=hybrid
```

---

## Data Modes

| Mode | Meaning |
|------|---------|
| `SIMULATED` | Physics-based synthetic telemetry (solar bell-curve, wind power curve, fault injection) |
| `LIVE` | Real IoT/SCADA telemetry (not active — requires hardware connection) |
| `HISTORICAL` | Stored dataset replay (not active — requires database) |

Every data point in the API is labelled with its source: `LIVE`, `API`, `SIMULATED`, `HISTORICAL`, or `FORECAST`.

---

## Simulation Mode

The simulation engine is never removed. It provides:
- Realistic solar generation (bell-curve, day/night, irradiance)
- Realistic wind generation (turbine power curve: cut-in 3 m/s, rated 12 m/s, cut-out 25 m/s)
- 7 fault scenarios injectable via `POST /api/simulation/fault`

Fault scenarios:
- `NORMAL`
- `SOLAR_INVERTER_DEGRADATION` (SOL-INV-042)
- `WIND_TURBINE_OVERHEATING` (WT-017)
- `HIGH_WIND_EVENT`
- `CLOUD_COVER_EVENT`
- `RENEWABLE_SURPLUS`
- `GRID_DEMAND_INCREASE`

---

## Security

- `WATSONX_API_KEY` is loaded only in the backend process
- It is passed only to the IBM SDK (which exchanges it for an IAM bearer token)
- It is **never** logged, never included in any API response, never sent to the frontend
- The frontend communicates only with `/api/*` — it never receives IBM credentials
- `.env` is in `.gitignore`

---

## Running Tests

```bash
cd greenpulse/backend
source .venv/bin/activate
pytest tests/test_watsonx.py -v
# 20 tests — no real API key required (IBM calls are mocked)
```

---

## Project Structure

```
greenpulse/
├── backend/
│   ├── app/
│   │   ├── agents/            # 5 AI agents (performance, maintenance, forecast, grid, orchestrator)
│   │   ├── api/               # FastAPI routers (assets, solar, wind, grid, alerts, ai, ...)
│   │   ├── core/
│   │   │   ├── config.py      # Settings — reads from .env
│   │   │   └── ibm_client.py  # Compatibility shim → watsonx_service
│   │   ├── models/            # Pydantic schemas + asset registry (40 assets)
│   │   ├── services/
│   │   │   ├── watsonx_service.py   # ← IBM Granite integration
│   │   │   └── alert_service.py
│   │   ├── simulation/        # Physics-based synthetic data engine
│   │   └── observability/     # Structured logging
│   ├── tests/
│   │   └── test_watsonx.py    # 20 unit tests (mocked IBM)
│   ├── requirements.txt
│   └── .env.example
└── frontend/                  # React + Vite dashboard
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | System health |
| `GET` | `/api/health/ai` | IBM Granite connectivity |
| `POST` | `/api/ai/query` | AI assistant (full orchestrator) |
| `POST` | `/api/ai/test` | Direct Granite test prompt |
| `GET` | `/api/system/info` | System info + AI mode |
| `GET` | `/api/assets` | All 40 assets |
| `GET` | `/api/assets/{id}/health` | Asset health score |
| `GET` | `/api/maintenance/risks` | Predictive maintenance scores |
| `GET` | `/api/grid/recommendation` | Grid advisory (AI RECOMMENDATION) |
| `GET` | `/api/forecast` | 24h generation forecast |
| `POST` | `/api/simulation/fault` | Inject fault scenario |
| `GET` | `/docs` | Swagger UI |
