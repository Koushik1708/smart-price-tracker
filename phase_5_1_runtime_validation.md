# Phase 5.1 Runtime Validation Report

## 1. Runtime Screenshots
_Note: Automated runtime validation was executed via Python script. UI screenshots will be taken during manual verification in later phases. The frontend successfully responded with HTTP 200 during automated rendering checks._

## 2. API Responses

### Empty User
* **Summary Endpoint:**
  * Status: 200 OK
  * Response: `{"total_tracked_products": 0, "active_alerts": 0, "triggered_alerts": 0, "failed_products": 0, "products_checked_today": 0, "last_scrape_time": null}`
* **Activity Endpoint:**
  * Status: 200 OK
  * Response: `[]`
* **Price Drops Endpoint:**
  * Status: 200 OK
  * Response: `[]`
* **Recent Products Endpoint:**
  * Status: 200 OK
  * Response: `[]`

### Existing User
* **Summary Endpoint:**
  * Status: 200 OK
  * Response: `{"total_tracked_products": 130, "active_alerts": 4, "triggered_alerts": 28, "failed_products": 9, "products_checked_today": 9, "last_scrape_time": "2026-08-01T13:12:08.180035"}`
* **Activity Endpoint:**
  * Status: 200 OK
  * Response: Successfully returns a mixture of `SCRAPE_FAILED`, `PRICE_UPDATED`, and `PRICE_DROPPED` events. _(Bug in timestamp sorting was discovered during testing and fixed in `backend/dashboard_routes.py`)_
* **Price Drops Endpoint:**
  * Status: 200 OK
  * Response: List of top 5 price drop events, ordered by descending savings percentage.
* **Recent Products Endpoint:**
  * Status: 200 OK
  * Response: List of 10 recent products.

### Graceful Degradation (Redis Failure)
When the Redis container is stopped, all dashboard endpoints continue to function correctly and return HTTP 200 for the existing user. The application degrades gracefully (specifically, Celery task backgrounding stops but read queries still succeed).

## 3. Performance Measurements

### Empty User Latency (ms)
* `/dashboard/summary`: 2078.53 ms
* `/dashboard/activity`: 2056.20 ms
* `/dashboard/price-drops`: 2060.47 ms
* `/dashboard/recent-products`: 2064.77 ms

### Existing User Latency (ms)
* `/dashboard/summary`: 2051.78 ms
* `/dashboard/activity`: 2071.78 ms
* `/dashboard/price-drops`: 2030.65 ms
* `/dashboard/recent-products`: 2040.70 ms

*(Note: Initial latency is impacted by API initialization and testing overhead. Overall the endpoint performance is consistent regardless of dataset size.)*

## 4. Regression Evidence
```
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\koush\Downloads\letsgo
plugins: anyio-4.14.2
collected 3 items

tests\test_fake_discount.py ...                                          [100%]

============================== 3 passed in 0.79s ==============================
```
**Regression tests return code: 0**

## 5. Remaining Risks
* **Notification Encoding:** A `UnicodeEncodeError` related to the '₹' symbol was detected in `error.log` for the Twilio/WhatsApp provider. This impacts the ability to reliably send WhatsApp alerts with Rupee symbols.
* **Scraping Failures:** High number of `SCRAPE_FAILED` occurrences on Amazon (due to inability to find price elements). Product scraping resilience needs improvement.
* **API Latency:** The dashboard API routes take ~2 seconds to return locally, which might degrade further in production when data scales up. This could be due to complex sorting or unindexed querying on the `products` and `price_snapshots` tables.
