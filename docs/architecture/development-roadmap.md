# ReliAI — Development Roadmap

> Phased implementation plan for the ReliAI platform.
> Version: 0.2 — Updated per architecture review

---

## Implementation Control Principles

> These principles apply to every phase. They must not be bypassed under time pressure.

1. **Incremental milestones.** No phase generates a large, unreviewed code dump. Each phase
   has small, verifiable milestones. The team verifies each milestone before proceeding to the next.

2. **Tests before proceeding.** Each phase specifies required tests. Those tests must pass
   before the next phase begins. A feature without passing tests is not complete.

3. **Definition of Done is non-negotiable.** "Mostly done" does not satisfy a DoD.
   If the DoD cannot be met, the scope of the phase is reduced — it is not skipped.

4. **No speculative implementation.** Do not implement features beyond the current phase's
   scope. Future phases will be clearer when the present one is complete.

5. **Architecture is the source of truth.** If implementation reveals an ambiguity or
   conflict with `system-architecture.md`, stop and update the architecture document
   before writing code. Do not silently deviate.

6. **Each PR is reviewable.** Changes within a phase should be committable in small
   reviewable units (1 module, 1 endpoint group, 1 component). No giant single commits.

---

## Phase 0 — Architecture & Blueprint ✅ COMPLETE

**Goal:** Produce a complete, reviewed architecture before writing any application code.
Avoid wasted implementation effort.

**Components:**
- `docs/architecture/system-architecture.md`
- `docs/architecture/technical-decisions.md`
- `docs/architecture/development-roadmap.md`
- `docs/research/evaluation-plan.md`
- `README.md`

**Dependencies:** None

**Deliverables:**
- ✅ Workspace inspected (empty)
- ✅ System architecture document (DB schema, API spec, frontend pages, AI pipeline, viva reference)
- ✅ Architectural Decision Records (14 ADRs, all accepted)
- ✅ Evaluation plan (research questions, paired experimental protocol, corrected metric definitions)
- ✅ Development roadmap (this document)
- ✅ Root README

**Tests:** N/A (documentation phase)

**Definition of Done:**
✅ All 14 ADRs accepted. Architecture reviewed and approved. No pending decisions.
Implementation may begin at Phase 1.

**Milestones:**
1. ✅ Initial architecture documents created
2. ✅ Architecture review corrections applied (v0.2)
3. ✅ All ADRs resolved

---

## Phase 1 — Repository & Development Infrastructure

**Goal:** Set up the monorepo skeleton, tooling, CI, and local development environment.
No application logic yet.

**Components:**
- Monorepo directory structure created
- Python backend: `pyproject.toml`, virtual environment, `ruff` + `mypy` configured
- Frontend: Vite + React + TypeScript project bootstrapped
- Docker Compose skeleton (placeholder services)
- `.env.example` files for backend and frontend (including all ADR-014 timing variables)
- `pre-commit` hooks (ruff, mypy, prettier)
- `Makefile` with common commands (`make up`, `make migrate`, `make test`, etc.)

**Specific Tasks:**

```
backend/
├── pyproject.toml              (FastAPI, SQLAlchemy, Alembic, Celery, Pydantic, pytest, ruff, mypy)
├── .env.example                (all env vars documented including DETECTION_INTERVAL, LLM_PROVIDER etc.)
└── app/
    ├── main.py                 (bare FastAPI app, /health endpoint only)
    └── config.py               (pydantic-settings Settings class with all env vars)

frontend/
├── package.json                (React, TypeScript, Vite, React Router, TanStack Query, Recharts, Radix UI)
├── vite.config.ts
├── tsconfig.json
└── src/
    ├── main.tsx
    └── App.tsx                 (placeholder route skeleton)

docker/
├── backend.Dockerfile
├── frontend.Dockerfile
└── demo-service.Dockerfile

docker-compose.yml              (postgres, redis, backend, frontend stubs)
Makefile
.gitignore
```

**Dependencies:** Phase 0 approved

**Deliverables:**
- Running `docker compose up` brings up postgres + redis (no application code yet)
- `make dev-backend` starts FastAPI with hot reload; `/health` returns `{"status": "ok"}`
- `make dev-frontend` starts Vite dev server
- `make lint` passes with no errors

**Tests:**
- Backend: `pytest` runs and reports 0 tests (infrastructure is ready)
- Frontend: `vitest` runs and reports 0 tests

**Definition of Done:**
`docker compose up` succeeds. `/health` endpoint reachable. Both dev servers start.
Lint passes. Team members can all run the environment locally.

---

## Phase 2 — Backend Foundation + PostgreSQL

**Goal:** Establish the database schema, ORM models, migrations, and core API infrastructure.
Authentication fully implemented.

**Components:**
- All SQLAlchemy models (users, refresh_tokens, services, service_dependencies, incidents,
  incident_events, incident_services, metric_snapshots, log_snapshots, ai_analyses,
  remediation_recommendations, experiments, experiment_runs)
- Alembic migration: initial schema
- Pydantic schemas for all models
- JWT authentication endpoints (`/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`)
- Dependency injection: `get_db`, `get_current_user`, `require_role`
- Redis connection setup
- `pytest` database fixtures (test database, transaction rollback per test)

**Specific Tasks:**

```
backend/app/
├── database.py             (async SQLAlchemy engine, session factory)
├── models/                 (all ORM models as per schema)
├── schemas/                (all Pydantic v2 schemas)
├── api/v1/auth.py          (register, login, refresh, logout, me)
├── utils/auth.py           (JWT create/verify, password hash/verify)
└── dependencies.py         (get_db, get_current_user, require_role)

alembic/versions/001_initial_schema.py
```

**Dependencies:** Phase 1

**Deliverables:**
- `alembic upgrade head` creates all tables cleanly
- Auth endpoints functional and tested
- Postman/HTTPie collection for auth endpoints (for team reference)

**Tests:**
- `tests/unit/test_auth.py` — password hashing, JWT encode/decode
- `tests/api/test_auth.py` — register, login, refresh, logout, protected route
- `tests/integration/test_database.py` — model creation, relationship integrity

**Definition of Done:**
All auth endpoints pass tests. Migration applies and rolls back cleanly. 100% coverage
on auth module.

---

## Phase 3 — Demo Microservices

**Goal:** Build the controlled demo environment: three realistic services that generate
real observability signals and support controlled failure injection.

**Components:**
- `api-gateway/` — FastAPI reverse proxy with simple routing
- `user-service/` — User CRUD (create, get, list users) with PostgreSQL
- `order-service/` — Order creation with PostgreSQL + Redis dependency
- `shared/` — Shared instrumentation library (OTel, Prometheus, structlog)
- Docker Compose integration
- Failure injection hooks in each service (controlled via environment variable feature flags)

**Shared instrumentation provides:**
```python
# shared/instrumentation.py
setup_opentelemetry(service_name, otlp_endpoint)
setup_prometheus(app)          # adds /metrics endpoint
setup_structured_logging()     # structlog JSON to stdout
```

**Realistic traffic generation:**
- `demo-services/traffic_generator.py` — sends realistic HTTP traffic patterns
- Runs as a separate container; generates background load for baseline metrics

**Failure injection flags (per-service env vars):**
```
FORCE_500_RATE=0.0           # 0.0–1.0 probability of returning 500
LATENCY_INJECT_MS=0          # additional ms delay on all requests
DB_HOLD_CONNECTIONS=false    # hold DB connections without releasing
REDIS_DISABLED=false         # skip Redis operations (simulates Redis failure)
MEMORY_PRESSURE_MB=0         # allocate N MB of memory
```

**Dependencies:** Phase 2

**Deliverables:**
- `docker compose up demo` starts all demo services
- Prometheus scrapes all three services + observes /metrics endpoints
- Structured JSON logs appear on stdout
- OTel traces flow to collector
- Traffic generator produces background requests visible in Prometheus

**Tests:**
- `tests/unit/test_demo_services.py` — each service endpoint returns expected responses
- `tests/integration/test_failure_injection.py` — verify failure flags produce expected behaviour

**Definition of Done:**
All three demo services running. Prometheus showing live metrics. Logs flowing.
Each failure injection mechanism verified working.

---

## Phase 4 — Observability Pipeline

**Goal:** Connect the observability signals into the ReliAI backend. The backend can now
read metrics and ingest logs/traces.

**Components:**
- `core/ingestion/metric_scraper.py` — queries Prometheus HTTP API; stores MetricSnapshot
- `core/ingestion/log_ingestor.py` — receives log batches; writes to Redis buffer
- `core/ingestion/trace_ingestor.py` — receives trace batches; stores references
- `/ingest/v1/logs` endpoint (API-key authenticated)
- `/ingest/v1/traces` endpoint (API-key authenticated)
- Demo services updated to POST logs to ReliAI
- Celery Beat task: `metric_collection_task` (interval from `DETECTION_INTERVAL` env var, default: 10s)
- `/api/v1/metrics/{service_id}` — returns recent snapshots
- `/api/v1/logs` — queries Redis buffer + PostgreSQL snapshots

**Milestone breakdown:**
1. MetricScraper implemented and unit-tested (mocked Prometheus)
2. `/ingest/v1/logs` endpoint working with API key auth
3. Redis log buffer tested (LPUSH/LTRIM/overflow handling)
4. Celery Beat task confirmed running at configured interval
5. Integration test: demo service → ingest → query API

**Dependencies:** Phase 3

**Deliverables:**
- `GET /api/v1/metrics/summary` returns live Prometheus data
- `GET /api/v1/logs?service=order-service` returns recent logs
- MetricSnapshot records accumulating in PostgreSQL

**Tests:**
- `tests/unit/test_metric_scraper.py` — Prometheus HTTP API mocked, scraper parses correctly
- `tests/unit/test_log_ingestor.py` — batch parsing, Redis writes, overflow handling
- `tests/api/test_ingest.py` — API key auth, valid/invalid batch handling
- `tests/integration/test_observability_pipeline.py` — end-to-end: demo service → ingest → query

**Definition of Done:**
Metrics queryable via API. Logs queryable via API. Both pipelines visible in integration test.

---

## Phase 5 — Incident Detection Engine

**Goal:** Implement both detection modes. The system autonomously detects injected failures.

**Components:**
- `core/detection/rules.py` — threshold rule definitions (configurable)
- `core/detection/evaluator.py` — evaluates rules against metric snapshots
- `core/detection/anomaly.py` — Z-score based anomaly detection on rolling window
- `core/detection/correlator.py` — correlates violations using service dependency graph
- `core/detection/incident_creator.py` — deduplication + incident creation logic
- `core/detection/engine.py` — orchestrates full detection pipeline
- Celery Beat task: `anomaly_check_task` at `DETECTION_INTERVAL` (default: 10s, calls engine)
- `/api/v1/incidents` — list, filter, create (manual)
- `/api/v1/incidents/{id}` — incident detail
- Service health endpoint: `/api/v1/services/{id}/health`

**Dependencies:** Phase 4

**Deliverables:**
- Inject S1 (HTTP 500 spike) → incident created automatically within detection window
- Incident record visible via API
- Detection mode (`THRESHOLD_ONLY` vs `HYBRID_CORRELATION`) toggleable via config

**Tests:**
- `tests/unit/test_rule_evaluator.py` — test each rule with fixture metric sets
- `tests/unit/test_correlator.py` — correlation scoring with known input
- `tests/unit/test_incident_creator.py` — deduplication logic
- `tests/integration/test_detection_pipeline.py` — inject fake metric violation → incident created

**Definition of Done:**
All 8 failure scenarios detectable in THRESHOLD_ONLY mode. At least 6 detectable in
HYBRID_CORRELATION mode (baseline for evaluation). No duplicate incidents created for
same ongoing failure.

---

## Phase 6 — Incident Management API

**Goal:** Complete incident lifecycle management: timeline, resolution, comments, signals.

**Components:**
- `incident_events` system (auto-generated and user-created events)
- `/api/v1/incidents/{id}/events` — timeline endpoint
- `/api/v1/incidents/{id}/signals` — related metrics + log excerpts
- `PATCH /api/v1/incidents/{id}` — status updates, comments
- `POST /api/v1/incidents/{id}/resolve` — resolution flow (creates log snapshot)
- `/api/v1/services/{id}/incidents` — per-service incident history
- `/api/v1/analytics/*` — basic analytics endpoints

**Dependencies:** Phase 5

**Deliverables:**
- Complete incident lifecycle testable via API
- Analytics endpoints returning real data

**Tests:**
- `tests/api/test_incidents.py` — CRUD, status transitions, timeline
- `tests/api/test_analytics.py` — analytics endpoints return correct aggregates

**Definition of Done:**
Full incident lifecycle (detection → investigation → resolution) completable via API calls.

---

## Phase 7 — AI RCA Pipeline

**Goal:** Implement both RCA modes (RCA_BASELINE and RCA_AI) plus the LLMProvider abstraction.
The system produces structured, evidence-grounded RCA for every detected incident, with
the deterministic baseline always available as a fallback and for experimental comparison.

**Components:**

*Shared infrastructure (both modes):*
- `core/ai_pipeline/evidence.py` — EvidenceCollector (shared)
- `core/ai_pipeline/output_validator.py` — Pydantic schema validation (shared)
- `core/ai_pipeline/confidence.py` — ConfidenceScorer (shared)
- `core/ai_pipeline/dispatcher.py` — selects RCA_BASELINE or RCA_AI per request

*RCA_BASELINE (implement first):*
- `core/ai_pipeline/rule_rca.py` — 9-rule deterministic engine (no LLM dependency)
  - Rules R1–R9 as defined in `evaluation-plan.md` Section 3.1
  - Each rule cites specific evidence items from EvidencePackage
  - Fully testable without any external API

*LLMProvider abstraction:*
- `core/ai_pipeline/providers/base.py` — `LLMProvider` ABC
- `core/ai_pipeline/providers/gemini.py` — `GeminiProvider`
- `core/ai_pipeline/providers/openai_compat.py` — `OpenAICompatibleProvider`
- `core/ai_pipeline/providers/mock.py` — `MockProvider` (offline demo)

*RCA_AI (build after providers):*
- `core/ai_pipeline/context_builder.py` — ContextBuilder
- `core/ai_pipeline/pipeline.py` — LLMRCAPipeline orchestrator
- `tasks/ai_analysis.py` — Celery task wrapping dispatcher

*API:*
- `/api/v1/analysis/{incident_id}` — GET analysis
- `/api/v1/analysis/{incident_id}/trigger` — POST (accepts `rca_mode` param)
- `/api/v1/analysis/{incident_id}/evidence` — GET evidence used
- `/api/v1/remediation/{incident_id}` — GET recommendations
- `/api/v1/remediation/{id}/approve` and `/reject`

**Milestone breakdown:**
1. EvidenceCollector implemented and unit-tested
2. RCA_BASELINE (rule_rca.py) implemented and tested for all 8 scenarios
3. LLMProvider ABC + MockProvider implemented and tested
4. GeminiProvider implemented (requires `LLM_API_KEY`); offline test uses MockProvider
5. ContextBuilder + LLMRCAPipeline implemented and integration-tested with MockProvider
6. Dispatcher, Celery task, and analysis API endpoints wired up
7. Remediation approval flow working

**Dependencies:** Phase 6

**Deliverables:**
- RCA_BASELINE produces valid output for all 8 scenarios (no LLM required)
- RCA_AI produces valid output with `AI_MOCK_MODE=true` (MockProvider)
- RCA_AI produces valid output with live GeminiProvider for at least 2 scenarios
- Both modes record `rca_mode` in `analysis_metadata`
- Both modes store `RCAOutput` in `ai_analyses` table
- `POST /api/v1/remediation/{id}/approve` stores approval with timestamp and user

**Tests:**
- `tests/unit/test_evidence_collector.py` — evidence collection with mocked DB
- `tests/unit/test_rule_rca.py` — each of 9 rules tested with matching and non-matching inputs
- `tests/unit/test_context_builder.py` — prompt structure, evidence-bounds
- `tests/unit/test_output_validator.py` — valid/invalid JSON schema handling
- `tests/unit/test_confidence_scorer.py` — confidence adjustment, floor logic
- `tests/unit/test_providers.py` — MockProvider output, GeminiProvider (mocked HTTP)
- `tests/ai_pipeline/test_rca_baseline.py` — RCA_BASELINE for all 8 scenarios
- `tests/ai_pipeline/test_rca_ai_mocked.py` — full RCA_AI pipeline with mocked LLMProvider
- `tests/api/test_analysis.py` — analysis and remediation endpoint tests

**Definition of Done:**
RCA_BASELINE produces correct, evidence-referenced output for all 8 scenarios.
RCA_AI pipeline end-to-end with MockProvider. Both modes produce identical schema.
Remediation approval flow working. All tests pass.

---

## Phase 8 — React Dashboard

**Goal:** Build the professional SRE dashboard frontend. This is the primary user-facing
deliverable.

**Components (in order of priority):**

1. **Design system setup** — CSS variables, typography (Inter font), colour tokens, dark mode
2. **AppLayout** — Sidebar, TopBar, routing setup
3. **LoginPage** — JWT auth flow
4. **/dashboard** — health summary, active incidents, error rate chart, service status grid
5. **/incidents** — table with filters, severity/status badges
6. **/incidents/:id** — incident detail with timeline, signals, AI analysis panel, remediation
7. **/services** — service list with health badges, SLO indicators
8. **/services/:id** — service detail with metrics charts
9. **/logs** — log explorer with search, filter, live toggle (SSE)
10. **/metrics** — metric charts with time range selector
11. **/ai-analysis** — AI analysis list with confidence indicators

**Dependencies:** Phase 7 (API must be complete)

**Deliverables:**
- All 9 pages above implemented and connected to real API
- Dark mode working
- Responsive layout (min 1280px wide)
- Loading, error, and empty states for every data-fetching component

**Tests:**
- `tests/e2e/test_dashboard.py` — Playwright: login → view dashboard → view incident detail
- Component unit tests for key components (Vitest + React Testing Library)

**Definition of Done:**
All 9 pages load real data from running backend. No console errors. Dark mode works.
E2E test passes against local Docker environment.

---

## Phase 9 — Dependency Graph + Analytics

**Goal:** Add the service dependency graph visualisation and complete analytics views.

**Components:**
- `/dependencies` page with React Flow service graph
  - Nodes: services (coloured by health status)
  - Edges: dependencies (styled by criticality)
  - Hover: service detail popover
  - Click: navigate to service detail
- `/analytics` page:
  - Incident frequency chart (time series)
  - MTTR per service
  - Reliability heat map
  - SLO compliance table
- Backend `/api/v1/analytics/` endpoints (if not done in Phase 6)
- `GET /api/v1/services/{id}/dependencies` — subgraph for single service

**Dependencies:** Phase 8

**Deliverables:**
- Dependency graph renders all demo services with correct edges
- Analytics charts show real historical data from experiment runs

**Definition of Done:**
Dependency graph interactive and reflects real service topology. Analytics charts populated
after at least one experiment run.

---

## Phase 10 — Failure Injection + Evaluation

**Goal:** Execute the complete paired experiment protocol and collect all evaluation data.

**Components:**
- `experiments/scenarios/*.py` — all 8 scenario scripts finalised and reviewed
- `experiments/runner.py` — CLI batch runner with automated environment reset
- `experiments/` REST API endpoints complete (including `/grade` endpoint)
- `/experiments` frontend page — experiment management UI
- Run all **80 detection evaluations** (8 scenarios × 5 reps × 2 detection modes, paired with reset)
- Run all **80 RCA evaluations** (8 scenarios × 5 reps × 2 RCA modes)
- Blind human grading of all 80 RCA outputs (mode label hidden during grading)
- `experiments/analysis/results_analysis.py` — compute all metrics defined in `evaluation-plan.md`
- Export results to CSV

**Milestone breakdown:**
1. All 8 scenario scripts reviewed and verified working
2. Environment reset protocol (`runner.py reset`) automated and verified
3. Batch runner completes 8 scenarios × 1 rep × 2 modes without errors (smoke test)
4. Full 80-run detection experiment completed (overnight batch)
5. Full 80-run RCA experiment completed (overnight batch)
6. Human grading completed for all 80 RCA outputs
7. `results_analysis.py` produces all metrics and figures from `evaluation-plan.md`

**Dependencies:** Phase 9

**Deliverables:**
- 80 detection experiment runs completed and graded
- 80 RCA experiment runs completed and graded
- Results CSV exported with all columns from `evaluation-plan.md` Section 7.1
- All evaluation metrics computed (DR, MR, FAR, ACR, DL, RCIR, ACA, CC, ERR, RL, E2E-TTD)
- Figures ready for dissertation Chapter 5

**Definition of Done:**
All 160 experiment evaluations completed without system errors.
Results exported and metrics computed. Blind grading completed. Reviewer inter-rater
agreement (Cohen's Kappa) computed for remediation quality scores.

---

## Phase 11 — Testing Suite

**Goal:** Achieve comprehensive test coverage across all layers.

**Components:**
- Complete `tests/unit/` coverage for all core modules
- Complete `tests/api/` coverage for all endpoints
- `tests/integration/` covering full pipeline scenarios
- `tests/ai_pipeline/` covering pipeline with mocked LLM
- `tests/e2e/` Playwright tests for critical user journeys
- Code coverage report (target: >80% backend coverage)

**Dependencies:** Phase 10

**Deliverables:**
- `make test` runs all tests and passes
- Coverage report generated
- No known test failures

**Definition of Done:**
All tests pass. Coverage >80% backend. At least 3 E2E tests passing. CI pipeline
(GitHub Actions or local equivalent) configured.

---

## Phase 12 — Docker / Deployment

**Goal:** Ensure the entire platform is runnable from a single `docker compose up` command
on a clean machine.

**Components:**
- Production Dockerfiles (multi-stage for frontend, slim Python for backend)
- `docker-compose.yml` with all services, health checks, dependency ordering
- `docker-compose.dev.yml` with volume mounts for hot-reload
- Prometheus configuration for all scrape targets
- OTel Collector configuration
- `.env.example` with all required variables documented
- `docs/setup.md` — Getting Started guide

**Dependencies:** Phase 11

**Deliverables:**
- Fresh machine test: clone repo → `cp .env.example .env` → `docker compose up` → platform running
- Prometheus showing all targets UP
- Demo traffic flowing

**Definition of Done:**
Team member who did not write the Docker config can bring up the platform from scratch
in under 10 minutes using only the README.

---

## Phase 13 — Documentation & Demo Polish

**Goal:** Prepare final academic documentation and a polished demonstration.

**Components:**
- UML diagrams (use case, class diagram, sequence, activity, DFD, ER) for dissertation Chapter 3
- API documentation (FastAPI auto-generates OpenAPI; supplement with narrative)
- Updated README with full setup guide and screenshots
- Demo script: end-to-end walkthrough of a cascading failure scenario
- Academic report sections (Chapter 3 system design, Chapter 4 implementation, Chapter 5 results)
- Recorded demo video (optional)

**Dependencies:** Phase 12

**Deliverables:**
- Complete dissertation Chapters 3, 4, 5 drafts supportable by the implementation
- Demo script rehearsed and working
- All documentation reviewed by supervisor

**Definition of Done:**
Platform demonstrated successfully. Dissertation chapters drafted. Repository clean and
tagged with final version.

---

## Timeline Summary

| Phase | Title | Estimated Duration |
|---|---|---|
| 0 | Architecture | 1 week |
| 1 | Repository & Infra | 3 days |
| 2 | Backend Foundation | 1 week |
| 3 | Demo Microservices | 1 week |
| 4 | Observability Pipeline | 1 week |
| 5 | Incident Detection | 1.5 weeks |
| 6 | Incident Management API | 1 week |
| 7 | AI RCA Pipeline (both modes) | 2 weeks |
| 8 | React Dashboard | 2 weeks |
| 9 | Dependency Graph + Analytics | 1 week |
| 10 | Failure Injection + Evaluation | 1.5 weeks |
| 11 | Testing | 1 week |
| 12 | Docker / Deployment | 3–4 days |
| 13 | Documentation + Demo | 1–1.5 weeks |
| **Total** | | **≈ 17–18 weeks** |

---

## Team Responsibility Suggestion (3 members)

| Member | Primary Phases | Secondary |
|---|---|---|
| Member A (Backend Lead) | 2, 4, 5, 6, 7 | 12, testing |
| Member B (Demo + Experiments) | 3, 10, 11 | 4, evaluation analysis |
| Member C (Frontend Lead) | 8, 9 | 13, UI polish |

*Phase 0, 1, 12, 13 are shared responsibilities.*
