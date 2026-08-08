# Goal Description

Phase 5.1 introduces a production-quality User Dashboard providing immediate visibility into tracked products, price movements, active alerts, and system health. The implementation strictly adheres to the "No schema changes" and "Zero regression" rules, reusing existing architectures (FastAPI, Redis, Celery, Twilio) and creating aggregated views over the current data.

## Proposed Changes

---

### Backend Components

#### [NEW] `backend/dashboard_routes.py`
Create a new router exclusively for dashboard aggregations to keep `api_routes.py` clean.
- `GET /dashboard/summary`: 
  - Calculates `total_tracked_products`, `active_alerts`, `triggered_alerts`, `failed_products`, `products_checked_today`, `last_scrape_time`.
- `GET /dashboard/activity`: 
  - Queries recent `PriceSnapshot` entries (Price Updates, Dropped, Increased, Alert Triggered) and `Product.last_failure` (Errors) for the current user. Unions them in Python, sorts chronologically (newest first), and returns max 20 items.
- `GET /dashboard/price-drops`: 
  - Uses ONE optimized SQL query with SQLite Window Functions (`LAG()`) to find the difference between the most recent and second most recent `PriceSnapshot`. Returns `image`, `product title`, `previous price`, `current price`, `savings`, `savings %`, `timestamp`.
- `GET /dashboard/recent-products`: 
  - Returns recently checked products. Max 10 items. Fields: `image`, `title`, `current price`, `status`, `last checked`.

#### [MODIFY] `backend/main.py`
- Include the new `dashboard_routes.py` router.

---

### Frontend Components

#### [MODIFY] `frontend/src/App.jsx`
- Reorganize the top-level route `/` to point to a new `DashboardOverview` component instead of directly listing products.

#### [NEW] `frontend/src/components/DashboardOverview.jsx`
- Main dashboard layout container ensuring `<500ms` load time, utilizing loading skeletons and error boundaries. Includes the following sections:
  1. **Overview Cards**: Displays `Total Products`, `Active Alerts`, `Triggered Alerts`, `Products Checked Today`.
  2. **Biggest Price Drops**: Responsive table.
  3. **Recently Checked Products**: Card layout.
  4. **Recent Activity Timeline**: Newest first with icons.
  5. **Alert Summary**: Displays `Active`, `Triggered`, `Disabled`, `Failed`.
  6. **System Status**: Reuses `/health`. Displays pills for Backend, DB, Redis, Celery (Green/Yellow/Red). Gracefully degrades.
  7. **Quick Actions**: Buttons for Track Product, Refresh, View Products, View Alerts.

## Security & Observability
- Dashboard endpoints require authentication (users only access their own data).
- Endpoints emit `trace_id`, `request_id`, `execution_time_ms`, and `status`.

## Verification Plan

### Automated Tests
- Run existing regression tests via pytest.
- Ensure `flake8` or `pylint` passes for new endpoints.
- Check that FastAPI startup succeeds without routing errors.

### Manual Verification
- Empty dashboard state.
- One product and hundreds of products states.
- Slow backend / backend unavailable states.
- Unauthorized access prevention.
- Mobile, tablet, and desktop layout responsiveness.
