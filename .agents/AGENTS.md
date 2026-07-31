# Price History & Fake-Discount Tracker - Project Rules

This document defines the mandatory engineering and product rules for this repository. All future development must follow these rules unless explicitly overridden by the user.

---

# 1. Product Mission

This project is an MVP for tracking historical prices of consumer technology products sold on Amazon India and Flipkart.

The primary goals are:

* Track historical selling prices.
* Detect potentially inflated MRP-based discounts.
* Notify users when prices reach desired thresholds.
* Keep the system simple, reliable, and inexpensive to operate.

Do not change the product vision.

Improve the implementation instead.

---

# 2. Architecture Constraints

## Decoupled Scraper

The scraper module is intentionally isolated.

Business logic must never depend directly on Playwright, selectors, or marketplace HTML.

The scraper should only return normalized product data.

If marketplace HTML changes, only the scraper implementation should require modification.

---

## Graceful Failure

Scraping failures are expected.

Failures must:

* Log the error.
* Preserve existing historical data.
* Continue processing remaining products.
* Never crash the scheduler.

Never overwrite valid data with null values after a failed scrape.

---

## Provider Interfaces

All external services must be abstracted.

Examples:

* BaseScraper
* NotificationProvider

Future providers must be interchangeable without modifying business logic.

---

# 3. Layered Architecture

Application flow must remain:

Frontend
↓
FastAPI API
↓
Service Layer
↓
Repository Layer
↓
Database

External integrations must never bypass the service layer.

---

# 4. Technology Requirements

Backend

* Python
* FastAPI
* SQLAlchemy
* SQLite (MVP)

Frontend

* React (Vite)
* Vanilla CSS
* Recharts

Scraping

* Playwright
* Randomized delays
* Persistent cookies
* Rotating User-Agent
* Low request concurrency

---

# 5. Database Rules

Historical pricing data is immutable.

Never overwrite previous snapshots.

Always append new snapshots.

Every snapshot should include:

* Product ID
* Current price
* Displayed MRP
* Availability
* Timestamp
* Scrape status

---

# 6. Fake Discount Rules

A fake discount is determined mathematically.

The algorithm must remain deterministic.

Use configurable parameters rather than hardcoded values.

Do not generate AI trust scores or subjective ratings.

The algorithm must always be explainable.

---

# 7. Configuration

Do not hardcode:

* Thresholds
* Time windows
* User-Agent strings
* API keys
* Twilio credentials
* Playwright settings

Use centralized configuration.

---

# 8. Testing Requirements

Every new feature should include:

* Unit tests
* Failure tests
* Regression tests where appropriate

Scraper parsing should be tested using saved HTML snapshots rather than live marketplace requests.

---

# 9. Logging

Important operations should be logged.

Examples:

* Scrape started
* Scrape completed
* Scrape failed
* Notification sent
* Notification failed
* Product added
* Scheduler execution

---

# 10. MVP Scope

This project is intentionally limited.

Supported marketplaces:

* Amazon India
* Flipkart

Supported category:

* Consumer technology and gadgets

Do not add:

* User authentication
* Browser extensions
* Premium subscriptions
* AI recommendation engines
* Coupon aggregation
* General shopping features

unless explicitly requested.

---

# 11. Engineering Principles

Prefer:

* Readable code
* Small modules
* Explicit logic
* Clear interfaces
* Simple implementations

Avoid unnecessary abstractions.

Do not introduce design patterns unless they provide measurable value.

---

# 12. Product Preservation

Do not replace the user's product idea with another startup concept.

Improve architecture.
Improve maintainability.
Improve scalability.
Improve reliability.

Preserve the product vision.

---

# 13. Decision Making

When proposing changes:

1. Preserve the current product.
2. Identify technical risks.
3. Recommend improvements.
4. Explain trade-offs.
5. Implement only after the design is sound.

Never redesign the product unless explicitly instructed.

---

# Final Rule

Optimize for a production-quality MVP that is simple, maintainable, resilient, and easy to extend without requiring a future rewrite.

---

# Mandatory Evidence-Based Implementation Policy

This policy applies to every implementation task, feature, milestone, bug fix, refactor, and project completion.

Never declare implementation complete solely because code has been generated.

The existence of source code is NOT evidence that a feature works.

Implementation and verification are separate activities.

---

# Engineering Evidence Policy

Every implementation must classify work into exactly one of the following states.

## VERIFIED

The feature has been implemented AND objectively verified.

Verification requires actual evidence.

Acceptable evidence includes:

* Successful build output
* Successful application startup
* Unit test results
* Integration test results
* End-to-end test results
* HTTP request/response
* Database records
* CLI command output
* Deployment logs
* Screenshots
* Generated artifacts

Never mark something as VERIFIED without evidence.

---

## IMPLEMENTED BUT NOT VERIFIED

Code exists.

However:

* it has not been executed,
* has not been tested,
* or evidence cannot be produced.

Do not speculate.

Be explicit.

---

## PARTIALLY VERIFIED

Only part of the feature has been verified.

Example:

✓ API starts

✓ Database connects

⚠ Endpoint behavior not tested

⚠ Frontend interaction not tested

---

## PENDING

Work intentionally not implemented.

---

## BLOCKED

Implementation cannot continue because of missing:

* Credentials
* API keys
* Infrastructure
* User input
* External services
* Third-party approval
* Network access

Explain the blocker.

---

# Mandatory Completion Report

Every implementation must produce the following report.

## 1. Implementation Summary

Describe:

* What was built
* What changed
* Files created
* Files modified
* Files removed
* Components intentionally unchanged

---

## 2. Verification Matrix

Every feature must be classified as:

Verified

Partially Verified

Implemented but Unverified

Pending

Blocked

Nothing may be omitted.

---

## 3. Verification Evidence

For every VERIFIED item include evidence.

Examples:

Build output

HTTP responses

Test logs

Database row counts

Command output

Generated files

Deployment logs

If evidence cannot be shown, downgrade the status.

---

## 4. Project Structure

Summarize the repository after implementation.

---

## 5. API Status

For every endpoint include:

Method

Route

Purpose

Implementation Status

Verification Status

Evidence

---

## 6. Database Status

Document:

Tables

Relationships

Indexes

Migration status

Current row counts

Seed status

---

## 7. Configuration

List every required environment variable.

Mark each as:

Required

Optional

Default

---

## 8. Manual Verification Checklist

Provide a checklist another engineer can execute.

---

## 9. Automated Testing

Report:

Unit Tests

Integration Tests

Regression Tests

Coverage

Failures

Skipped Tests

Reasons

---

## 10. Known Limitations

List all known technical limitations.

Never hide engineering debt.

---

## 11. Remaining Work

Separate into:

Critical

High

Medium

Low

Future Enhancements

---

## 12. Risks

For every risk include:

Likelihood

Impact

Mitigation

Owner

---

## 13. Operational Readiness

Report status of:

Health checks

Logging

Monitoring

Cron jobs

Background workers

Deployment

Backups

Recovery

Secrets management

---

## 14. Success Criteria

Evaluate every original project requirement.

Each requirement must be marked:

✓ Verified Complete

⚠ Implemented but Unverified

◐ Partial

✗ Not Implemented

Provide justification.

---

## 15. Final Engineering Assessment

Evaluate:

Architecture

Maintainability

Reliability

Scalability

Security

Testing

Operational readiness

Technical debt

Overall implementation quality

Do not inflate scores.

---

# Absolute Engineering Rules

Never confuse implementation with verification.

Never infer successful execution from source code.

Never invent successful test results.

Never fabricate build logs.

Never fabricate deployment results.

Never fabricate API responses.

Never fabricate screenshots.

Never fabricate scraper execution.

Never fabricate database contents.

If something has not been verified, explicitly state that it has not been verified.

Engineering honesty always takes priority over optimistic reporting.

The goal is to produce implementation reports that another senior engineer can trust without needing to guess what was actually proven.

---

# Traceability of AI Claims

Every claim made by the AI must be traceable to one of four sources:

1. Verified by execution
2. Derived directly from source code
3. Inferred (clearly labeled as inference)
4. Provided by the user

Never present inference as verification.
