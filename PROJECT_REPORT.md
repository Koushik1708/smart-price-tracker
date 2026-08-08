# Smart Price Tracker & Fake Discount Detector - Detailed Architecture Report

## Executive Summary

This project is a **full-stack price tracking application** that monitors product prices on Amazon India and Flipkart, detects potentially inflated MRP-based discounts ("fake discounts"), and sends WhatsApp notifications when prices drop below user-defined thresholds.

---

## Technology Stack

### Backend (FastAPI + Python)
| Component | Technology |
|-----------|------------|
| API Framework | FastAPI 0.109+ |
| Database ORM | SQLAlchemy 2.0 |
| Database (Dev) | SQLite |
| Database (Prod) | PostgreSQL |
| Task Queue | Celery + Redis |
| Web Scraping | Playwright (async, headless Chromium) |
| Authentication | JWT (HS256) + bcrypt |
| Notifications | Twilio WhatsApp Sandbox API |
| Rate Limiting | SlowAPI (Token Bucket) |
| Metrics | Prometheus Client |
| Tracing | Custom ContextVars-based distributed tracing |
| Containerization | Docker + Docker Compose |

### Frontend (React + Vite)
| Component | Technology |
|-----------|------------|
| Framework | React 19 + Vite 8 |
| Routing | React Router v7 |
| Styling | Tailwind CSS 4 + Vanilla CSS |
| Charts | Recharts 3 |
| Icons | Lucide React |
| HTTP Client | Axios |
| Linting | Oxlint |

---

## Project Structure

```
letsgo/
├── backend/                 # FastAPI application
│   ├── main.py             # App entry point, middleware, exception handlers
│   ├── config.py           # Environment-based configuration
│   ├── database.py         # SQLAlchemy engine & session management
│   ├── models.py           # SQLAlchemy ORM models
│   ├── auth.py             # JWT auth, password hashing, account lockout
│   ├── auth_routes.py      # /auth/* endpoints (register, login, me)
│   ├── api_routes.py       # /products/*, /alerts/*, /health, /metrics
│   ├── dashboard_routes.py # /dashboard/* (analytics, activity, price drops)
│   ├── admin_routes.py     # /admin/* (user mgmt, system diagnostics, audit)
│   ├── celery_app.py       # Celery configuration & worker lifecycle hooks
│   ├── notifications.py    # Twilio WhatsApp provider
│   ├── fake_discount.py    # Fake discount detection algorithm
│   ├── analytics.py        # Statistics, trend analysis, deal scoring
│   ├── metrics.py          # Prometheus metrics definitions
│   ├── tracing.py          # Distributed tracing via ContextVars
│   └── services/           # Business logic layer
│       ├── worker.py       # Celery task execution (execute_job)
│       ├── scrape_service.py   # Scraper wrapper
│       ├── task_scheduler.py   # Job enqueueing via Celery
│       ├── audit_service.py    # Audit logging
│       ├── job_types.py        # Job type enum
│       └── job_result.py       # Job result DTOs
├── scraper/                # Playwright scraping modules
│   ├── base.py             # Abstract BaseScraper
│   ├── amazon_scraper.py   # Amazon India scraper (DOM selectors)
│   ├── flipkart_scraper.py # Flipkart scraper (JSON-LD schema)
│   └── runner.py           # Standalone async scraper runner
├── frontend/               # React + Vite application
│   ├── src/
│   │   ├── App.jsx         # Main layout, routing, state management
│   │   ├── AuthContext.jsx # Auth state & API calls
│   │   ├── apiClient.js    # Axios instance with interceptors
│   │   ├── components/     # UI components
│   │   │   ├── DashboardOverview.jsx
│   │   │   ├── ProductDashboard.jsx
│   │   │   ├── AddProduct.jsx
│   │   │   ├── AdminPanel.jsx
│   │   │   └── ... (dashboard widgets, common UI)
│   │   └── config.js       # API base URL
├── scripts/                # Operational utilities
│   ├── migrate_db.py       # DB schema migration
│   ├── verify_*.py         # E2E & regression test scripts
│   └── backup_db.py        # SQLite backup utility
├── tests/                  # Pytest test suites
├── docker-compose.yml      # Local dev stack (API, Redis, Celery)
├── docker-compose.prod.yml # Production stack
├── Procfile                # Railway/Heroku start command
├── requirements.txt        # Python dependencies
└── openapi.json            # OpenAPI 3.0 spec
```

---

## Database Schema

### Core Tables

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────────┐
│     users       │       │    products      │       │  price_snapshots    │
├─────────────────┤       ├──────────────────┤       ├─────────────────────┤
│ id (PK)         │──1:N──│ id (PK)          │──1:N──│ id (PK)             │
│ name            │       │ user_id (FK)     │       │ product_id (FK)     │
│ email (UQ)      │       │ url              │       │ price               │
│ password_hash   │       │ title            │       │ mrp_shown           │
│ is_admin        │       │ platform         │       │ timestamp           │
│ failed_login_att│       │ product_id       │       │ is_fake_discount    │
│ locked_until    │       │ status           │       └─────────────────────┘
│ created_at      │       │ image_url        │
└─────────────────┘       │ brand            │
                          │ category         │
                          │ retry_count      │
                          │ last_failure     │
                          │ last_failure_rsn │
                          └──────────────────┘
                                  │
                                  │ 1:N
                                  ▼
                         ┌─────────────────────┐
                         │  alert_thresholds   │
                         ├─────────────────────┤
                         │ id (PK)             │
                         │ user_id (FK)        │
                         │ product_id (FK)     │
                         │ phone_number        │
                         │ threshold_price     │
                         │ status (ACTIVE/     │
                         │        TRIGGERED/   │
                         │        FAILED)      │
                         └─────────────────────┘

┌─────────────────┐
│   audit_logs    │
├─────────────────┤
│ id (PK)         │
│ trace_id        │
│ span_id         │
│ request_id      │
│ user_id (FK)    │
│ timestamp       │
│ action          │
│ outcome         │
│ ip_address      │
│ user_agent      │
│ details         │
└─────────────────┘
```

### Key Constraints & Indexes
- `UNIQUE(user_id, url)` on products — prevents duplicate tracking per user
- `CHECK(price > 0)`, `CHECK(mrp_shown > 0)` on snapshots
- Composite indexes: `(user_id, status)`, `(product_id, timestamp)`

---

## System Architecture Flowchart

```mermaid
flowchart TD
    %% ========================================
    %% USER INTERACTION LAYER
    %% ========================================
    User[👤 User] -->|1. Browser| FE[Frontend: React + Vite]
    FE -->|2. HTTPS/REST| API[Backend: FastAPI]
    
    %% ========================================
    %% API GATEWAY & MIDDLEWARE
    %% ========================================
    subgraph API_GW [API Gateway Layer]
        MW1[Security Headers Middleware]
        MW2[Request ID + Tracing Middleware]
        MW3[CORS Middleware]
        MW4[Rate Limiter (SlowAPI)]
        MW5[Exception Handlers]
    end
    
    API --> MW1 --> MW2 --> MW3 --> MW4 --> MW5
    
    %% ========================================
    %% ROUTING
    %% ========================================
    MW5 --> Router{Route Dispatcher}
    
    Router -->|/auth/*| AuthRoutes[Auth Routes]
    Router -->|/products/*| ProdRoutes[Product Routes]
    Router -->|/alerts/*| AlertRoutes[Alert Routes]
    Router -->|/dashboard/*| DashRoutes[Dashboard Routes]
    Router -->|/admin/*| AdminRoutes[Admin Routes]
    Router -->|/health, /metrics| SysRoutes[System Routes]
    
    %% ========================================
    %% AUTHENTICATION FLOW
    %% ========================================
    subgraph AUTH_FLOW [Authentication & Authorization]
        AuthRoutes -->|POST /register| Reg[Register User]
        AuthRoutes -->|POST /login| Login[Login + JWT Issue]
        AuthRoutes -->|GET /me| Me[Validate Token]
        AuthRoutes -->|POST /logout| Logout[Revoke Token]
        
        Reg -->|bcrypt hash| DB[(Database)]
        Login -->|verify_password| DB
        Login -->|JWT create| Token[JWT Token]
        Me -->|JWT decode| Token
        Me -->|User lookup| DB
    end
    
    %% ========================================
    %% PRODUCT TRACKING FLOW
    %% ========================================
    subgraph PROD_FLOW [Product Tracking Flow]
        ProdRoutes -->|POST /track| Track[Track Product]
        Track -->|canonicalize_url| Canon[URL Canonicalizer]
        Canon -->|amazon.in/flipkart.com| Platform{Platform?}
        Platform -->|Amazon| AmazonP[Amazon URL Parser]
        Platform -->|Flipkart| FlipkartP[Flipkart URL Parser]
        
        Track -->|Check limit| Limit{Products < 50?}
        Limit -->|No| Err400[400 Limit Reached]
        Limit -->|Yes| Dup{Exists?}
        Dup -->|Yes| Err409[409 Already Tracked]
        Dup -->|No| Create[Create Product PENDING]
        Create --> DB
        Create -->|schedule_scrape| Scheduler[Task Scheduler]
        
        Scheduler -->|Redis Ping| Redis[(Redis Broker)]
        Scheduler -->|apply_async| CeleryQ[Celery Queue: scraper_queue]
    end
    
    %% ========================================
    %% ASYNC SCRAPING PIPELINE
    %% ========================================
    subgraph SCRAPER_PIPE [Async Scraping Pipeline (Celery Workers)]
        CeleryQ --> Worker[Celery Worker Process]
        Worker -->|execute_job| JobSpan[Start Trace Span]
        JobSpan -->|scrape_service| ScrapeSvc[Scrape Service]
        ScrapeSvc -->|scrape_single_product| Runner[Scraper Runner]
        
        Runner -->|Product.platform| Platform2{Platform?}
        Platform2 -->|amazon| AmazonScraper[AmazonScraper]
        Platform2 -->|flipkart| FlipkartScraper[FlipkartScraper]
        
        AmazonScraper -->|Playwright Chromium| AmazonSite[(Amazon.in)]
        FlipkartScraper -->|Playwright Chromium| FlipkartSite[(Flipkart.com)]
        
        AmazonScraper -->|DOM Selectors| ExtractA[Extract Price, MRP, Title, Image, Brand, Category]
        FlipkartScraper -->|JSON-LD Schema| ExtractF[Extract Price, MRP, Title, Image, Brand, Category]
        
        ExtractA --> Validate[Validate Price > 0, MRP > 0]
        ExtractF --> Validate
        
        Validate -->|Invalid| Fail[Mark FAILED, retry_count++]
        Validate -->|Valid| FakeCheck[Fake Discount Detection]
        
        FakeCheck -->|30-day history| DBSnaps[(Price Snapshots)]
        FakeCheck -->|avg MRP * 1.10| Flag{Current MRP > 110% avg?}
        Flag -->|Yes| MarkFake[is_fake_discount = true]
        Flag -->|No| MarkReal[is_fake_discount = false]
        
        MarkFake --> DupSnap{Duplicate?}
        MarkReal --> DupSnap
        DupSnap -->|Yes| SkipInsert[Skip DB Insert]
        DupSnap -->|No| InsertSnap[Insert PriceSnapshot]
        
        InsertSnap --> UpdateProd[Update Product: title, image, brand, category, status=SUCCESS]
        UpdateProd --> AlertCheck[Check Active Alerts]
        AlertCheck -->|Price <= Threshold| Twilio[Twilio WhatsApp]
        AlertCheck -->|Price > Threshold| NoAlert[No Action]
        
        Twilio -->|Send| AlertUpdate[Alert status = TRIGGERED]
        Fail --> DB
        UpdateProd --> DB
        InsertSnap --> DB
        AlertUpdate --> DB
    end
    
    %% ========================================
    %% DASHBOARD & ANALYTICS
    %% ========================================
    subgraph DASHBOARD [Dashboard Analytics]
        DashRoutes -->|GET /summary| Summary[Summary Stats]
        DashRoutes -->|GET /activity| Activity[Recent Activity Feed]
        DashRoutes -->|GET /price-drops| Drops[Top Price Drops]
        DashRoutes -->|GET /recent-products| Recent[Recently Checked]
        
        Summary -->|SQL Aggregations| DB
        Activity -->|Window Functions + Union| DB
        Drops -->|LAG() Window Function| DB
        Recent -->|COALESCE + MAX| DB
    end
    
    %% ========================================
    %% ADMIN & OBSERVABILITY
    %% ========================================
    subgraph ADMIN [Admin Panel & Observability]
        AdminRoutes -->|GET /users| UserMgmt[User Management]
        AdminRoutes -->|GET /products| ProdMgmt[Global Product Mgmt]
        AdminRoutes -->|GET /failed-jobs| DLQ[Dead Letter Queue View]
        AdminRoutes -->|GET /redis| RedisStatus[Redis Health]
        AdminRoutes -->|GET /queues| QueueDepth[Queue Depth]
        AdminRoutes -->|GET /workers| WorkerStatus[Worker Status]
        AdminRoutes -->|GET /diagnostics| Diagnostics[System Diagnostics]
        AdminRoutes -->|GET /config| Config[Runtime Config View]
        AdminRoutes -->|GET /stats| Stats[System Stats]
        AdminRoutes -->|GET /audit-logs| AuditLog[Audit Log Viewer]
        
        UserMgmt --> DB
        ProdMgmt --> DB
        DLQ --> DB
        RedisStatus --> Redis
        QueueDepth --> Redis
        Diagnostics -->|psutil, shutil| Host[Host Metrics]
        Diagnostics --> DB
    end
    
    %% ========================================
    %% METRICS & TRACING
    %% ========================================
    subgraph OBSERVABILITY [Observability Stack]
        MW2 -->|Request ID, Trace ID| TraceCtx[ContextVars Tracing]
        TraceCtx -->|Structured JSON Logs| Logs[Stdout Logs]
        
        API -->|Prometheus Metrics| Prom[/metrics/prometheus]
        Worker -->|CELERY_* metrics| Prom
        AuthRoutes -->|AUTH_FAILURES| Prom
        AdminRoutes -->|ADMIN_ACTIONS| Prom
        AuditSvc -->|AUDIT_EVENTS| Prom
        
        AuditSvc[audit_service] -->|INSERT| AuditTbl[AuditLog Table]
    end
    
    %% ========================================
    %% DATA STORES
    %% ========================================
    DB[(SQLite/PostgreSQL)]
    Redis[(Redis Broker)]
    
    %% ========================================
    %% EXTERNAL SERVICES
    %% ========================================
    AmazonSite -.->|HTTP| ExtAmazon[Amazon India]
    FlipkartSite -.->|HTTP| ExtFlipkart[Flipkart.com]
    Twilio -.->|HTTPS| TwilioAPI[Twilio WhatsApp API]
    
    %% ========================================
    %% STYLING
    %% ========================================
    classDef fe fill:#61dafb,color:#000
    classDef be fill:#009688,color:#fff
    classDef db fill:#ff9800,color:#fff
    classDef q fill:#9c27b0,color:#fff
    classDef ext fill:#e91e63,color:#fff
    classDef obs fill:#3f51b5,color:#fff
    
    class FE fe
    class API,MW1,MW2,MW3,MW4,MW5,Router,AuthRoutes,ProdRoutes,AlertRoutes,DashRoutes,AdminRoutes,SysRoutes,Track,Canon,Platform,AmazonP,FlipkartP,Limit,Dup,Create,Scheduler,JobSpan,ScrapeSvc,Runner,Platform2,AmazonScraper,FlipkartScraper,ExtractA,ExtractF,Validate,FakeCheck,Flag,MarkFake,MarkReal,DupSnap,SkipInsert,InsertSnap,UpdateProd,AlertCheck,Twilio,AlertUpdate,Fail,Summary,Activity,Drops,Recent,UserMgmt,ProdMgmt,DLQ,RedisStatus,QueueDepth,WorkerStatus,Diagnostics,Config,Stats,AuditLog,AuditSvc be
    class DB,Redis,AuditTbl db
    class CeleryQ,Worker q
    class AmazonSite,FlipkartSite,Twilio,ExtAmazon,ExtFlipkart,TwilioAPI ext
    class TraceCtx,Logs,Prom obs
```

---

## Detailed Component Interactions

### 1. Product Tracking Request Flow
```
User submits URL
       │
       ▼
Frontend: AddProduct.jsx → POST /products/track
       │
       ▼
FastAPI: api_routes.track_product()
       │
       ├─► Rate Limit Check (10/min)
       ├─► User Product Limit Check (50/user)
       ├─► canonicalize_url() → Resolves redirects, extracts ASIN/ITM ID
       ├─► Duplicate Check (UNIQUE user_id + url)
       ├─► Create Product (status=PENDING)
       ├─► schedule_scrape() → Celery apply_async
       │       │
       │       └─► Redis Broker → Celery Queue (scraper_queue)
       │
       └─► Audit Log: PRODUCT_TRACKED
```

### 2. Celery Worker Scraping Flow
```
Celery Worker picks job
       │
       ▼
execute_job() task
       │
       ├─► Start Trace Span (Worker)
       ├─► Observe Queue Wait Time (Histogram)
       ├─► scrape_service.scrape_product(product_id)
       │       │
       │       └─► scraper.runner.scrape_single_product()
       │               │
       │               ├─► Product.status = SCRAPING
       │               ├─► Select Scraper (Amazon/Flipkart)
       │               ├─► Playwright: launch Chromium → goto URL
       │               │       ├─► Amazon: DOM selectors (#productTitle, .a-price-whole)
       │               │       └─► Flipkart: JSON-LD schema (application/ld+json)
       │               ├─► Extract: price, mrp, title, image, brand, category
       │               ├─► Validate price > 0, mrp > 0
       │               ├─► detect_fake_discount() → 30-day MRP average comparison
       │               ├─► Deduplication: compare with latest snapshot
       │               ├─► Insert PriceSnapshot (is_fake_discount flag)
       │               ├─► Update Product metadata + status=SUCCESS
       │               ├─► Check AlertThresholds (ACTIVE)
       │               │       └─► If price ≤ threshold → Twilio WhatsApp send
       │               │               └─► Alert status = TRIGGERED
       │               └─► On failure: status=FAILED, retry_count++, log reason
       │
       ├─► On Success: CELERY_JOBS_COMPLETED(SUCCESS)
       ├─► On Failure: 
       │       ├─► Retry with exponential backoff (max 3)
       │       ├─► After max retries → Dead Letter Queue (Redis list)
       │       └─► CELERY_JOBS_COMPLETED(FAILED)
       │
       └─► Observe Execution Time (Histogram)
```

### 3. Alert Notification Flow
```
PriceSnapshot inserted
       │
       ▼
Check AlertThreshold WHERE product_id AND status=ACTIVE
       │
       ▼
For each alert:
       ├─► current_price ≤ threshold_price?
       │       │
       │       ├─► YES → TwilioSandboxProvider.send_alert()
       │       │       ├─► Format WhatsApp message
       │       │       ├─► Twilio REST API call
       │       │       └─► On success: alert.status = TRIGGERED
       │       │
       │       └─► NO → No action
       │
       ▼
Commit transaction
```

### 4. Fake Discount Detection Algorithm
```
detect_fake_discount(db, product_id):
       │
       ├─► Query PriceSnapshots last 30 days (timestamp ≥ now - 30d)
       ├─► Require minimum 5 snapshots
       ├─► latest = most recent snapshot
       ├─► historical = all except latest
       ├─► avg_mrp = mean(historical.mrp_shown)
       ├─► IF latest.mrp_shown > avg_mrp * 1.10:
       │       RETURN True (fake discount detected)
       └─► ELSE:
               RETURN False
```

### 5. Deal Score Calculation
```
calculate_deal_score(product, snapshots, is_fake_discount):
       │
       ├─► Base Score: 50
       ├─► Current vs Average (±25): 
       │       current < avg → +min(25, drop% * 125)
       │       current > avg → -min(25, increase% * 125)
       ├─► Current vs Lowest (±20/-10):
       │       current ≤ lowest → +20
       │       else → -min(10, diff% * 50)
       ├─► Fake Discount Penalty: -30
       ├─► Trend Bonus/Penalty: DOWN +5, UP -5
       ├─► Clamp: 0-100
       └─► Stars: ≥90 ★★★★★, ≥70 ★★★★☆, ≥50 ★★★☆☆, ≥30 ★★☆☆☆, else ★☆☆☆☆
```

---

## API Endpoints Summary

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/` | Root health check | No |
| GET | `/health` | Detailed system health (DB, Redis, Celery, Disk, Mem, CPU, Queue) | No |
| GET | `/live` | Liveness probe | No |
| GET | `/ready` | Readiness probe (DB + Redis) | No |
| GET | `/version` | App version & build info | No |
| GET | `/metrics` | User metrics (products, alerts, fake discounts) | Yes |
| GET | `/metrics/prometheus` | Prometheus scrape endpoint | No |
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | Login, returns JWT | No |
| GET | `/auth/me` | Get current user profile | Yes |
| POST | `/auth/logout` | Logout (client-side token removal) | Yes |
| POST | `/products/track` | Submit URL to track | Yes |
| GET | `/products/search` | Paginated search & filter | Yes |
| GET | `/products/{id}` | Product details + history + analytics | Yes |
| PATCH | `/products/{id}` | Update product status | Yes |
| POST | `/products/{id}/retry` | Manual retry failed scrape | Yes |
| DELETE | `/products/{id}` | Delete product & history | Yes |
| GET | `/products/{id}/export` | CSV export of price history | Yes |
| POST | `/products/{id}/alerts` | Create WhatsApp price alert | Yes |
| GET | `/products/{id}/alerts` | List alerts for product | Yes |
| DELETE | `/alerts/{id}` | Delete alert | Yes |
| GET | `/dashboard/summary` | Dashboard KPI cards | Yes |
| GET | `/dashboard/activity` | Recent activity feed | Yes |
| GET | `/dashboard/price-drops` | Top 5 price drops | Yes |
| GET | `/dashboard/recent-products` | Recently checked products | Yes |
| GET | `/admin/users` | Paginated user management | Admin |
| POST | `/admin/users/{id}/role` | Toggle admin role | Admin |
| GET | `/admin/products` | Global product management | Admin |
| POST | `/admin/products/{id}/retry` | Force retry any product | Admin |
| DELETE | `/admin/products/{id}` | Admin delete product | Admin |
| GET | `/admin/alerts` | Global alerts view | Admin |
| GET | `/admin/failed-jobs` | Dead Letter Queue viewer | Admin |
| GET | `/admin/redis` | Redis connection info | Admin |
| GET | `/admin/queues` | Queue depth & status | Admin |
| GET | `/admin/workers` | Worker status | Admin |
| GET | `/admin/diagnostics` | System diagnostics (CPU, Mem, Disk, DB) | Admin |
| GET | `/admin/config` | Runtime config (masked secrets) | Admin |
| GET | `/admin/stats` | Global system statistics | Admin |
| GET | `/admin/audit-logs` | Paginated audit log viewer | Admin |

---

## Key Design Patterns & Architectural Decisions

### 1. **Separation of Concerns**
- **Routes** → HTTP handling, validation, serialization
- **Services** → Business logic (scraping, scheduling, auditing)
- **Models** → Data persistence (SQLAlchemy)
- **Scrapers** → Platform-specific extraction (Playwright)

### 2. **Async-First Architecture**
- FastAPI async endpoints
- Playwright async scraping
- Celery for background job processing
- SQLite/PostgreSQL with connection pooling

### 3. **Distributed Tracing (Custom)**
- ContextVars-based trace propagation
- Request ID → Trace ID → Span hierarchy
- Structured JSON logging with trace context
- Spans: API → Scheduler → Worker → Scraper

### 4. **Resilience Patterns**
- **Retry with Exponential Backoff**: Celery task retries (max 3)
- **Dead Letter Queue**: Failed jobs pushed to Redis list after max retries
- **Circuit Breaker**: Health endpoint checks Redis/DB/Celery before marking healthy
- **Graceful Degradation**: Twilio optional; scraper continues without notifications
- **Worker Startup Cleanup**: Resets stuck `SCRAPING` products to `PENDING`

### 5. **Security**
- JWT HS256 with configurable expiry
- bcrypt password hashing
- Account lockout after 5 failed attempts (15 min)
- Rate limiting per endpoint (login, register, track, alert)
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- CORS configured via env vars
- Audit logging for all mutating operations
- Input validation via Pydantic

### 6. **Observability**
- **Prometheus Metrics**: HTTP, Celery, Auth, Admin, Audit counters/histograms
- **Structured Logging**: JSON with trace context
- **Health Endpoints**: `/live`, `/ready`, `/health` (detailed)
- **Admin Diagnostics**: Real-time system metrics

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PRODUCTION ENVIRONMENT                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │  Vercel  │    │  Railway │    │  Railway │               │
│  │ Frontend │    │  Backend │    │PostgreSQL│               │
│  │ (React)  │◄───│ (FastAPI)│◄───│   DB     │               │
│  └──────────┘    └────┬─────┘    └──────────┘               │
│                       │                                      │
│              ┌────────┴────────┐                             │
│              │    Redis        │                             │
│              │  (Celery Broker)│                             │
│              └────────┬────────┘                             │
│                       │                                      │
│              ┌────────┴────────┐                             │
│              │ Celery Workers  │                             │
│              │ (Playwright +   │                             │
│              │  Chromium)      │                             │
│              └─────────────────┘                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Docker Compose Services (Local Dev)
- **backend**: FastAPI + Uvicorn
- **celery_worker**: Celery worker (concurrency=4)
- **redis**: Redis 7 (broker + result backend)
- **frontend**: Vite dev server (optional)

### Production Checklist
- [ ] PostgreSQL provisioned & `DATABASE_URL` set
- [ ] `python scripts/migrate_db.py` executed
- [ ] Playwright Chromium installed (`playwright install chromium`)
- [ ] Redis provisioned & `CELERY_BROKER_URL` set
- [ ] Twilio credentials configured (optional)
- [ ] JWT_SECRET ≥ 32 chars in production
- [ ] `ALLOWED_ORIGINS` matches frontend URL exactly
- [ ] Celery workers running with Chromium available
- [ ] Health endpoints verified (`/health`, `/live`, `/ready`)

---

## Data Flow Summary

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   USER      │────►│  FRONTEND   │────►│   BACKEND   │────►│  DATABASE   │
│  (Browser)  │     │  (React)    │     │  (FastAPI)  │     │ (SQLite/PG) │
└─────────────┘     └─────────────┘     └──────┬──────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    ▼                          ▼                          ▼
           ┌───────────────┐          ┌───────────────┐          ┌───────────────┐
           │   REDIS       │          │  CELERY       │          │  EXTERNAL     │
           │  (Broker)     │◄────────►│  WORKERS      │─────────►│  SERVICES     │
           └───────────────┘          │ (Scrapers)    │          │ (Amazon,      │
                                      └───────┬───────┘          │  Flipkart,    │
                                              │                │  Twilio)      │
                                              ▼                └───────────────┘
                                     ┌───────────────┐
                                     │  PROMETHEUS   │
                                     │  METRICS      │
                                     └───────────────┘
```

---

## Testing & Quality

| Test Type | Location | Coverage |
|-----------|----------|----------|
| Unit/Integration | `tests/` | Auth, API routes, fake discount, analytics |
| E2E | `scripts/verify_*.py` | Full flow verification |
| Load | `locustfile.py` | Locust load testing |
| Browser | `test_playwright.py` | Playwright scraper validation |
| Regression | `scripts/e2e_regression.py` | API regression suite |

---

## Configuration Reference (.env)

```env
# Required for Production
DATABASE_URL=postgresql://user:pass@host/db
FRONTEND_URL=https://app.example.com
ALLOWED_ORIGINS=https://app.example.com

# Auth
JWT_SECRET_KEY=your-32-char-min-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Optional: Twilio WhatsApp
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Celery/Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_CONCURRENCY=4
QUEUE_NAME=scraper_queue
MAX_RETRIES=3

# Limits
MAX_PRODUCTS_PER_USER=50
MAX_ALERTS_PER_USER=20
QUEUE_SIZE_LIMIT=1000
MAX_CONCURRENT_SCRAPE_JOBS=10

# Scraper Timeouts (ms)
SCRAPER_TIMEOUT=60000
PLAYWRIGHT_TIMEOUT=60000

# Security
ACCOUNT_LOCKOUT_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION_MINUTES=15
LOGIN_RATE_LIMIT=5/minute
REGISTER_RATE_LIMIT=5/minute
TRACK_RATE_LIMIT=10/minute
ALERT_RATE_LIMIT=5/minute
```

---

## Conclusion

This project demonstrates a **production-grade, enterprise-ready price tracking system** with:

✅ **Scalable async architecture** (FastAPI + Celery + Playwright)  
✅ **Multi-platform scraping** (Amazon India + Flipkart) with fallback strategies  
✅ **Intelligent fake discount detection** using statistical MRP analysis  
✅ **Real-time WhatsApp notifications** via Twilio  
✅ **Comprehensive observability** (tracing, metrics, structured logging, health checks)  
✅ **Operational excellence** (admin panel, DLQ, audit logs, diagnostics)  
✅ **Security hardening** (JWT, rate limiting, account lockout, security headers)  
✅ **Modern frontend** (React 19, Tailwind 4, Recharts) with responsive UX  

The system is designed for **horizontal scalability** (add Celery workers), **operational visibility** (Prometheus + admin diagnostics), and **data integrity** (audit trails, deduplication, constraints).