# ChurnIQ — Client Churn Prediction and Retention Analytics System

Backend API built with FastAPI, scikit-learn, XGBoost, SHAP, and pandas for real-time customer churn prediction, batch CSV processing, explainable AI, and actionable customer retention analytics.

---

## 🚀 Running the Backend

From the project directory, activate your virtual environment, install dependencies, and start FastAPI:

```powershell
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

- **Health check**: `http://127.0.0.1:8000/health`
- **Interactive OpenAPI docs (Swagger UI)**: `http://127.0.0.1:8000/docs`
- **ReDoc documentation**: `http://127.0.0.1:8000/redoc`

---

## 💻 Running the React Frontend (Phase 4)

Built with **React 19**, **Vite**, **TypeScript**, **Tailwind CSS**, **Recharts**, and **Axios**.

```powershell
cd frontend
npm install
npm run dev
```

The frontend dashboard will be available at **`http://localhost:5173`** (proxies `/api` calls directly to the FastAPI backend at `http://127.0.0.1:8000`).

### Authentication

Create an account from the sign-in page. Registration creates an analyst
account; administrative privileges must be assigned through a trusted
administrative process. Sign-in requires the account's username and password.
The frontend validates the bearer token with the API when the app is reopened.

### Dashboard Suite Pages:
1. **Main Dashboard (`/`)**: Executive KPIs, predicted churners, interactive Recharts risk donut chart, customer segment churn bar chart, global SHAP drivers, and priority interventions.
2. **Dataset Upload (`/upload`)**: Drag-and-drop CSV upload, 5-row preview, column mapping verification (19 features), validation error logs, and batch processing history.
3. **Customer Analytics (`/customers`)**: Search by customer ID, risk category filters (High, Medium, Low), contract segment filters, churn probability sorting, and pagination.
4. **Customer Details (`/customers/:id`)**: Individual profile breakdown, churn probability gauge, SHAP waterfall chart (positive/negative feature impacts), top drivers, and retention actions.
5. **Retention Management (`/retention`)**: Interactive retention workflow tracker, follow-up status updater (Pending, In Progress, Contacted, Retained, Escalated, Closed), analyst notes, and retention success metrics.
6. **Reports & Exports (`/reports`)**: Direct batch predictions CSV download, high-risk customer report export, and retention action plan export.

---

## Database (Phase 3)

ChurnIQ persists users, datasets, customers, prediction history, SHAP
explanations, recommendations, and batch-job metadata with SQLAlchemy.
PostgreSQL is the deployment database; set `backend/.env` from
`backend/.env.example`, then create the database and apply the reviewed
Alembic schema before starting the API:

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg2://churniq:your_password@localhost:5432/churniq"
alembic upgrade head
uvicorn app.main:app --reload
```

For local experiments only, omitting `DATABASE_URL` uses `churniq.db` SQLite.
Set `AUTO_CREATE_SCHEMA=true` only when you intentionally want SQLAlchemy to
create a local schema without Alembic. Production database changes must use
new migrations.

## Security and Privacy (Phase 5)

All customer-data endpoints require `Authorization: Bearer <JWT>`. Register
with `POST /auth/register`, then use the returned access token; public
registration always creates an `analyst` account and cannot grant administrator
privileges. Dataset, customer, batch-result, retention, and job access is
scoped to the authenticated tenant. Administrators alone can list users, purge
expired datasets, or permanently delete a dataset.

Passwords use bcrypt hashes, tokens are signed JWTs, and `JWT_SECRET_KEY` must
be supplied through `backend/.env` in production. Configure `CORS_ORIGINS`,
`ALLOWED_HOSTS`, `DATABASE_URL`, and HTTPS before deployment; do not commit a
real `.env` file. CSV uploads are limited to `MAX_UPLOAD_SIZE_BYTES` (50 MB by
default), must be UTF-8 `.csv` files, reject executable/binary content, and
neutralize spreadsheet formulas before downloadable output. Dataset deletion is
soft by default; the configured `DATASET_RETENTION_DAYS` controls eligible
administrator purge operations.

## Docker deployment (Phase 6)

Docker Compose orchestrates four concerns in one command:

| Service | Image / Build | Role |
|---|---|---|
| `db` | `postgres:16-alpine` | PostgreSQL 16 database |
| `backend` | `backend/Dockerfile` (Python 3.13-slim, multi-stage) | FastAPI API + ML inference |
| `frontend` | `frontend/Dockerfile` (Node 22 build → Nginx 1.27) | React SPA + API reverse proxy |

### Quick start

```powershell
# 1. Copy the example env file and fill in real secrets
Copy-Item .env.example .env.docker
#    Open .env.docker and set POSTGRES_PASSWORD and JWT_SECRET_KEY.

# 2. Build images and start all services
docker compose --env-file .env.docker up --build

# 3. (Optional) Run in the background
docker compose --env-file .env.docker up --build -d
```

| URL | Description |
|---|---|
| `http://localhost:5173` | React frontend dashboard |
| `http://localhost:8000/docs` | FastAPI Swagger UI |
| `http://localhost:8000/health` | Backend health check |

### Project layout (Docker)

```text
client-churn-prediction/
├── backend/
│   ├── app/                  # FastAPI application + ML inference
│   ├── alembic/              # Database migrations
│   ├── tests/
│   ├── storage/batch_jobs/   # Named volume: persisted batch CSVs
│   ├── requirements.txt
│   └── Dockerfile            # Multi-stage Python build
├── frontend/
│   ├── src/
│   ├── public/
│   ├── nginx.conf            # SPA routing + /api → backend proxy
│   ├── package.json
│   └── Dockerfile            # Node build → Nginx runtime
├── models/
│   └── churn_model_bundle.joblib   # Mounted read-only into backend
├── data/                     # Drop sample CSVs here (gitignored)
├── docker-compose.yml
├── .env.example              # Safe template — copy to .env.docker
├── .env.docker.example       # Local-dev defaults (do not use in prod)
├── .dockerignore
├── .gitignore
└── README.md
```

### Environment variables

Edit `.env.docker` (copied from `.env.example`) before running:

| Variable | Required | Description |
|---|:---:|---|
| `POSTGRES_PASSWORD` | ✅ | Database password |
| `JWT_SECRET_KEY` | ✅ | Token signing secret — generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `POSTGRES_DB` | | Database name (default: `churniq`) |
| `POSTGRES_USER` | | Database user (default: `churniq`) |
| `CORS_ORIGINS` | | Comma-separated allowed origins (default: `http://localhost:5173`) |
| `ALLOWED_HOSTS` | | Comma-separated trusted hostnames |
| `HTTPS_ENFORCE` | | `true` enforces HTTPS redirect (default: `false`) |
| `API_PORT` | | Host port for the backend (default: `8000`) |
| `FRONTEND_PORT` | | Host port for the frontend (default: `5173`) |

### Useful Compose commands

```powershell
# View logs for all services
docker compose --env-file .env.docker logs -f

# View logs for one service
docker compose --env-file .env.docker logs -f backend

# Stop and remove containers (data volumes are preserved)
docker compose --env-file .env.docker down

# Stop and remove containers AND wipe the database volume
docker compose --env-file .env.docker down -v

# Rebuild only the backend image
docker compose --env-file .env.docker build backend
```

### Production notes

- Supply strong, unique values for `POSTGRES_PASSWORD` and `JWT_SECRET_KEY`.
- Set `HTTPS_ENFORCE=true` and place a TLS-terminating reverse proxy (e.g. Caddy, Traefik, or Nginx) in front.
- Use a managed PostgreSQL service and point `DATABASE_URL` to it instead of the `db` container.
- URL-encode any reserved characters (`@`, `:`, `/`) in PostgreSQL credentials embedded in `DATABASE_URL`.
- The `models/` directory is mounted read-only (`ro`); swap the `.joblib` file and restart `backend` to deploy a new model without rebuilding the image.

---

## 🔍 Single Customer Prediction & SHAP Explanations (`POST /predict`)

To predict churn probability, risk tier, SHAP explanations, and retention recommendations:

```powershell
$customer = @{
    customer_id = "CUST-001"
    gender = "Male"
    SeniorCitizen = 0
    Partner = "No"
    Dependents = "No"
    tenure = 2
    PhoneService = "Yes"
    MultipleLines = "No"
    InternetService = "Fiber optic"
    OnlineSecurity = "No"
    OnlineBackup = "No"
    DeviceProtection = "No"
    TechSupport = "No"
    StreamingTV = "Yes"
    StreamingMovies = "Yes"
    Contract = "Month-to-month"
    PaperlessBilling = "Yes"
    PaymentMethod = "Electronic check"
    MonthlyCharges = 89.5
    TotalCharges = 179.0
} | ConvertTo-Json

# Request prediction with SHAP explanations and retention actions
Invoke-RestMethod -Uri "http://127.0.0.1:8000/predict?explain=true" `
    -Method Post -ContentType "application/json" -Body $customer
```

### Sample Response:
```json
{
  "customer_id": "CUST-001",
  "churn_probability": 0.8766,
  "churn_prediction": "Yes",
  "risk_category": "HIGH",
  "action_urgency": "URGENT",
  "threshold": 0.4,
  "top_churn_factors": [
    "Month-to-month contract",
    "Short customer tenure",
    "No online security"
  ],
  "top_protective_factors": [
    "Single phone line",
    "Has partner"
  ],
  "recommendations": [
    {
      "customer_id": "CUST-001",
      "churn_probability": 0.8766,
      "risk_category": "HIGH",
      "recommendation_reason": "Month-to-month contract",
      "suggested_action": "Offer a longer-term contract (one-year or two-year plan with incentive)",
      "priority": "High",
      "action_urgency": "URGENT",
      "supporting_shap_contribution": 0.4385,
      "shap_feature": "cat__Contract_Month-to-month"
    },
    {
      "customer_id": "CUST-001",
      "churn_probability": 0.8766,
      "risk_category": "HIGH",
      "recommendation_reason": "Short customer tenure",
      "suggested_action": "Provide onboarding assistance and schedule a satisfaction check-in",
      "priority": "High",
      "action_urgency": "URGENT",
      "supporting_shap_contribution": 0.2912,
      "shap_feature": "num__tenure"
    }
  ]
}
```

---

## 💡 Retention Recommendation Engine

The recommendation engine analyzes both rule-based conditions and supporting SHAP feature contributions:

| Customer Condition | Retention Action | Priority | Supporting SHAP Feature |
|---|---|:---:|---|
| Month-to-month contract | Offer a longer-term contract (one-year or two-year plan) | High | `cat__Contract_Month-to-month` |
| Short tenure ($\le 12$ months) | Provide onboarding assistance and schedule satisfaction check-in | High | `num__tenure` |
| No online security | Offer a security package with complimentary trial protection | Medium | `cat__OnlineSecurity_No` |
| No technical support | Offer a support plan with 24/7 dedicated assistance | Medium | `cat__TechSupport_No` |
| Electronic check | Encourage an automatic payment method (credit card or bank transfer) | Low | `cat__PaymentMethod_Electronic check` |
| High monthly charges ($\ge \$70$) | Review suitable pricing plans and identify cost-effective alternatives | Medium | `num__MonthlyCharges` |

### Action Urgency Rules:
- **`URGENT`**: Customers in the **HIGH** risk tier ($\ge 0.70$)
- **`PLANNED`**: Customers in the **MEDIUM** risk tier ($0.30 - 0.69$)
- **`MONITOR`**: Customers in the **LOW** risk tier ($< 0.30$)

---

## 📈 Customer Risk Analytics Endpoints (`/analytics`)

| Endpoint | Method | Description |
|---|---|---|
| `/analytics/overview` | `GET` | Overall customer counts, predicted churners, churn rate %, and risk distribution |
| `/analytics/risk-distribution` | `GET` | LOW, MEDIUM, and HIGH risk customer counts, percentages, and definitions |
| `/analytics/churn-factors` | `GET` | Global SHAP-derived churn drivers and protective retention factors |
| `/analytics/recommendations` | `GET` | Summary of retention recommendations by reason, priority, urgency, and action |
| `/analytics/segments` | `GET` | Churn rates and risk levels across Contract, TenureGroup, Internet, and Payment methods |

*Note: All `/analytics/*` endpoints accept an optional `?job_id={job_id}` query parameter to analyze a specific batch upload, or default to the latest completed dataset.*

---

## 📊 Batch CSV Prediction (`/batch`)

| Endpoint | Method | Description |
|---|---|---|
| `/batch/predict` | `POST` | Upload customer CSV and generate batch predictions |
| `/batch/{job_id}` | `GET` | Retrieve job processing status and validation metrics |
| `/batch/{job_id}/results` | `GET` | Retrieve paginated prediction results and invalid record details |
| `/batch/{job_id}/download` | `GET` | Download full prediction report as CSV |

---

## 🧪 Running the Test Suite

Run the full pytest suite (unit, integration, validation, model, workflow, and
security tests):

```powershell
cd backend
pytest -v
```

Run the marked large-CSV response-time check separately:

```powershell
pytest -m performance -v
```
