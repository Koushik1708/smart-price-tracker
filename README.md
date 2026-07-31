# Smart Price Tracker & Fake Discount Detector

This project tracks historical prices of consumer technology products sold on Amazon India and Flipkart, detects potentially inflated MRP-based discounts, and notifies users when prices reach desired thresholds via WhatsApp.

---

## Project Architecture

- **Frontend:** React (Vite) with Vanilla CSS and Recharts.
- **Backend:** FastAPI (Python), serving REST APIs.
- **Database:** SQLite (Development) / PostgreSQL (Production) using SQLAlchemy ORM.
- **Scraper:** Playwright (headless Chromium) with graceful timeouts and retry bookkeeping.
- **Notifications:** Twilio Sandbox API for WhatsApp alerts.
- **Scheduler:** Standalone async Python script to poll prices periodically.

## Folder Structure

```
├── backend/            # FastAPI application, models, routes, analytics
├── frontend/           # React + Vite UI
├── scraper/            # Playwright scraping logic (Amazon & Flipkart)
├── scripts/            # Utility scripts (e2e tests, db migrations)
├── .env.example        # Environment variable template
├── Procfile            # Deployment execution command
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
# Required for Production Database
DATABASE_URL=postgresql://user:password@host/dbname

# Required for API CORS
FRONTEND_URL=https://your-production-frontend.vercel.app
ALLOWED_ORIGINS=https://your-production-frontend.vercel.app

# Optional (Twilio WhatsApp)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Application info
APP_VERSION=1.0.0
ENVIRONMENT=production
```

*(Note: If `DATABASE_URL` is omitted, the app gracefully falls back to a local SQLite database for development.)*

---

## Local Setup

### 1. Python Backend
```bash
python -m venv venv
source venv/bin/activate  # (On Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

### 2. Playwright Installation
Playwright requires headless browsers to function:
```bash
playwright install chromium
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

---

## Running Locally

### Backend Startup
```bash
# From project root
uvicorn backend.main:app --reload --port 8000
```

### Frontend Startup
```bash
cd frontend
npm run dev
```

### Scheduler Setup
Run the background scraper periodically (e.g., via cron or systemd):
```bash
# From project root
python scraper/runner.py
```

---

## Twilio Setup (WhatsApp Alerts)

1. Sign up for Twilio and navigate to the WhatsApp Sandbox.
2. Send the join code (e.g., `join something-something`) to the Twilio number from your WhatsApp to opt-in.
3. Update `.env` with your `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`.
4. Users tracking products must also join the sandbox to receive alerts.

---

## Database Migration (PostgreSQL)

The migration script safely sets up tables and adds missing columns for both SQLite and PostgreSQL without recreating tables or losing data.

### Production Deployment Steps:
1. Deploy Backend to your provider (e.g., Railway).
2. Configure the `DATABASE_URL` environment variable to point to the newly provisioned PostgreSQL instance.
3. Execute the migration script on the server:
   ```bash
   python scripts/migrate_db.py
   ```
4. Verify that tables were created successfully by checking the server logs or querying the database.

---

## Migrating Existing SQLite Data

- **Local SQLite data is NOT automatically copied into PostgreSQL.**
- Your production PostgreSQL database will start completely empty.
- Existing products, alerts, price snapshots, and history remain exclusively inside your local `price_tracker.db`.
- **Note:** If you want production to contain the same historical data you gathered locally, you must manually migrate your SQLite database records into PostgreSQL before switching production traffic. 
- No built-in migration utility is provided for transferring data between SQLite and PostgreSQL, so plan accordingly.

---

## Deployment

### Deployment on Railway (Backend)
1. Link your GitHub repository to Railway.
2. Add a **PostgreSQL Database** in Railway and link it to your backend service.
3. Railway automatically injects the `DATABASE_URL`.
4. Set your other `.env` variables in Railway.
5. Railway reads `Procfile` to start the app: `web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
6. **Important:** Add a build command to install Playwright: `pip install -r requirements.txt && playwright install chromium`

### Deployment on Vercel (Frontend)
1. Link your `frontend/` directory to Vercel.
2. Set the Environment Variable: `VITE_API_URL=https://your-railway-app-url.railway.app`
3. Deploy.

---

## API Endpoints

- `GET /` - Root health check
- `GET /health` - Detailed operational status (DB, Playwright, Twilio)
- `GET /version` - App version and build info
- `GET /metrics` - Read-only aggregate metrics (counts of products, scrapes, alerts)
- `POST /products/track` - Submit an Amazon/Flipkart URL to track
- `GET /products/search` - Paginated product search & filtering
- `GET /products/{id}` - Product details, snapshots, and deal score
- `POST /products/{id}/retry` - Manually retry a failed scrape
- `DELETE /products/{id}` - Delete product and history
- `POST /products/{id}/alerts` - Setup WhatsApp alert threshold

---

## Troubleshooting

- **Scraper Timeouts:** Playwright will automatically timeout after 30 seconds and increment the retry counter. Ensure network isn't blocked.
- **Database URL Issues:** If using Heroku/Railway, `postgres://` URLs are automatically rewritten to `postgresql://` by the app to support SQLAlchemy.
- **Playwright Missing:** Ensure `playwright install chromium` was run on the production server. (Railway deployments require Chromium).
- **CORS Errors:** Verify `ALLOWED_ORIGINS` in `.env` matches your frontend URL EXACTLY.

---

## Final Verification Notes

**CRITICAL:** The backend API may report as "healthy" (returning 200 OK on `/health`), while the background scraper will still silently fail if the Playwright Chromium browser binaries are missing from the production environment. Always run a manual test scrape to verify Chromium is installed before considering the deployment successful.

---

## Production Checklist

- [ ] PostgreSQL database created
- [ ] `DATABASE_URL` configured
- [ ] `migrate_db.py` executed successfully
- [ ] Playwright Chromium installed
- [ ] Backend health endpoint verified
- [ ] Version endpoint verified
- [ ] Metrics endpoint verified
- [ ] Product tracking tested
- [ ] Background scraping tested
- [ ] WhatsApp notification tested
- [ ] CSV export tested
- [ ] Search tested
- [ ] Pagination tested
- [ ] Retry tested
- [ ] Delete tested
- [ ] Fake discount detection verified
