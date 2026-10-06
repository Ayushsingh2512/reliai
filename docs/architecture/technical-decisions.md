# Technical Decisions — ReliAI

> Architectural Decision Records (ADRs) for the ReliAI platform.
> Each decision records the context, options considered, the choice made, and the rationale.
> Version: 0.2 — Updated per architecture review.

---

## ADR-001 — Backend Architecture: Modular Monolith vs Microservices

**Status:** Accepted

**Context:**
The backend must handle: REST API serving, observability data ingestion, incident detection,
background AI analysis jobs, and the evaluation framework. A fully microservices backend would
require service discovery, inter-service networking, and distributed tracing of the backend
itself — adding significant complexity for a 3-person team.

**Decision:**
Use a **modular monolith** for the ReliAI backend.

The codebase is structured into discrete Python packages (`api`, `core`, `ingestion`,
`detection`, `incidents`, `ai_pipeline`, `experiments`) but deployed as a single FastAPI
process. Celery workers run as a separate process but share the same codebase.

**Rationale:**
- Achievable for a 3-person team within a semester
- Each module has clear boundaries and can be explained independently during viva
- Simpler debugging and local development
- Celery separation still demonstrates async job processing concepts
- Can be split into services later if needed

**Demo services are separate** because their purpose is specifically to simulate a distributed
system that the platform monitors — they must be independent processes generating real
distributed-system failures.

---

## ADR-002 — Primary Database: PostgreSQL

**Status:** Accepted

**Context:**
We need persistent storage for: incidents, incident events, services metadata, AI analyses,
remediation recommendations, experiment results, and users.

**Decision:**
PostgreSQL 15 as the primary relational database, accessed via SQLAlchemy 2 (async),
migrations via Alembic.

**Rationale:**
- ACID guarantees for incident records and audit trail
- Rich JSON support (JSONB) for storing structured AI outputs and evidence payloads
- Full-text search support for log snippets stored in incident context
- Industry-standard: can be explained comprehensively in viva
- Alembic migrations demonstrate professional DB practices

**What we do NOT store in PostgreSQL:**
Raw observability data (high-cardinality log streams, raw metric time series) is NOT stored
in PostgreSQL. Only summarised metric snapshots and log excerpts attached to specific incidents
are stored. Raw logs live in demo-service stdout; Prometheus stores raw metric time series.
This is architecturally correct and avoids building a custom TSDB.

---

## ADR-003 — Cache and Message Broker: Redis

**Status:** Accepted

**Context:**
We need: (1) caching for API responses (service health, recent incidents), (2) a Celery
message broker for background AI analysis jobs, (3) pub/sub for real-time event propagation.

**Decision:**
Redis 7 serves all three roles.

**Rationale:**
- Single dependency fulfilling multiple roles avoids adding RabbitMQ or Kafka
- Redis pub/sub is sufficient for the event volume of a local demo environment
- Celery's Redis broker is well-documented and simple to operate
- Redis is widely understood; explainable in viva

**What we do NOT use Redis for:**
Persistent incident data. Redis is ephemeral cache only; all durable state is in PostgreSQL.

---

## ADR-004 — Background Job Processing: Celery

**Status:** Accepted

**Context:**
AI RCA analysis involves LLM API calls that may take 5–30 seconds. These must not block the
REST API request cycle. Additionally, periodic metric scraping and anomaly detection need
scheduling.

**Decision:**
Celery 5 with Redis as broker and result backend.

**Rationale:**
- Industry-standard Python async task queue
- Demonstrates understanding of event-driven async processing for academic purposes
- Celery Beat for scheduled periodic tasks (metric snapshots, anomaly checks)
- Tasks are individually testable and monitorable via Flower (optional)

**Alternatives rejected:**
- FastAPI BackgroundTasks: insufficient for long-running tasks and retries
- ARQ: simpler but less feature-complete; fewer academic references
- Kafka: significant overengineering for a local demo

---

## ADR-005 — AI/LLM Integration: LLMProvider Abstraction

**Status:** Accepted

**Context:**
The AI RCA pipeline must produce structured, evidence-grounded analysis rather than free-form
text. The system must remain functional if the LLM API is unavailable. Model names and
providers change frequently; hard-coding a specific model version into the architecture
would create unnecessary coupling and could invalidate the design as models are deprecated.

**Decision:**
The AI layer is accessed through a provider abstraction interface:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, response_schema: dict) -> str: ...

class GeminiProvider(LLMProvider): ...
class OpenAICompatibleProvider(LLMProvider): ...
class MockProvider(LLMProvider): ...   # deterministic, no API call
```

Configuration via environment variables only:
```
LLM_PROVIDER=gemini              # or: openai_compatible
LLM_MODEL=gemini-2.0-flash       # set at deployment time; not hard-coded
LLM_API_KEY=...                  # from env; never in code
LLM_TIMEOUT_SECONDS=30
AI_MOCK_MODE=false               # set true for offline demo
```

Output: Pydantic-validated JSON schema enforced at the API call level (structured output mode).

**AI must NOT:**
- Receive raw unstructured prompts without evidence context
- Be called without timeout and retry handling
- Produce unvalidated free-form text as the final output
- Have a specific model name hard-coded anywhere in source code

**Rationale:**
- Provider abstraction makes the architecture valid regardless of which model is in use
- Switching from Gemini to any OpenAI-compatible endpoint requires only an env-var change
- Pydantic validation catches malformed AI responses before they reach the API layer
- MockProvider ensures the demo works without internet / API key during viva
- Students can explain the abstraction clearly during viva without defending a specific model choice

**Alternatives rejected:**
- Hard-coded `google-generativeai` SDK calls: breaks if SDK or model name changes
- LangChain: adds a heavyweight abstraction layer with its own complexity and maintenance burden

---

## ADR-006 — Observability Instrumentation: OpenTelemetry + Prometheus

**Status:** Accepted

**Context:**
The demo services and backend need to emit metrics, logs, and traces that the platform can
ingest and analyse.

**Decision:**
- **Metrics:** Prometheus exposition format; Prometheus server scrapes demo services and backend
- **Traces:** OpenTelemetry SDK in demo services; traces exported to OTel Collector (OTLP)
- **Logs:** Structured JSON logs (Python `structlog`; demo services emit JSON to stdout)
- **OTel Collector:** Receives OTLP traces, can fan-out to backend ingestor

**What we do NOT do:**
- Deploy a full Jaeger/Tempo/Grafana/Loki stack — this would be infrastructure for
  infrastructure's sake and is not the project deliverable
- The ReliAI backend IS the observability consumer; it reads from Prometheus HTTP API and
  from a log ingestion endpoint

**Rationale:**
OpenTelemetry is the industry standard; using it demonstrates real observability engineering.
Prometheus is the de-facto standard for metrics in container environments. Both are well-documented
for academic citation.

---

## ADR-007 — Frontend: React + TypeScript + Vite

**Status:** Accepted

**Context:**
The SRE dashboard must feel professional, support real-time-ish updates, display charts, tables,
dependency graphs, and incident timelines.

**Decision:**
- **Framework:** React 18 with TypeScript
- **Build tool:** Vite (fast dev server, modern ESM)
- **Data fetching / server state:** TanStack Query (React Query) v5
- **Charts:** Recharts (composable, TypeScript-first)
- **Dependency graph:** React Flow (force-directed service topology)
- **UI primitives:** Radix UI (accessible, unstyled) + custom CSS design system
- **Icons:** Lucide React
- **Routing:** React Router v6

**Alternatives rejected:**
- Next.js: SSR/SSG unnecessary for a local dashboard; adds complexity
- Material UI / Ant Design: Heavy, opinionated, results in generic-looking UI
- Tailwind: Acceptable but adds a build dependency; custom CSS gives more control

---

## ADR-008 — Authentication: JWT-based with Simple Role Model

**Status:** Accepted

**Context:**
The platform needs user authentication to protect the API and demonstrate security practices.
However, complex RBAC is out of scope.

**Decision:**
- JWT access tokens (short-lived, 15 min) + refresh tokens (stored in PostgreSQL, 7 days)
- Roles: `admin`, `engineer`, `viewer`
- Passwords: bcrypt hashed, never stored plaintext
- API keys for demo-service ingestion endpoints (separate from user JWTs)

**Rationale:**
Demonstrates professional auth practices without overengineering. JWT is standard and easily
testable. Refresh token rotation in DB allows token revocation.

---

## ADR-009 — Incident Detection: Hybrid Rule-Based + Correlation Engine

**Status:** Accepted

**Context:**
The evaluation requires comparing a baseline (threshold-only) against the proposed approach
(hybrid correlation). Both must be implemented in the same system so experiments can be run
with a feature flag.

**Decision:**
- **Baseline mode:** Each metric evaluated independently against static thresholds; alert fires
  immediately on threshold breach → creates incident
- **Hybrid mode:** Multiple signals within a time window are correlated using service dependency
  graph; incident is created only when correlation score exceeds a configurable threshold;
  severity is adjusted based on blast radius

**Implementation:**
A `DetectionMode` enum (`THRESHOLD_ONLY`, `HYBRID_CORRELATION`) is stored per experiment run,
allowing side-by-side comparison with identical failure scenarios.

---

## ADR-010 — Containerisation: Docker Compose Only (No Kubernetes)

**Status:** Accepted

**Context:**
The project must be demonstrable on a local development machine.

**Decision:**
Docker Compose with named services, health checks, and dependency ordering. No Kubernetes.

**Rationale:**
Kubernetes adds days of configuration work with no added academic value for this project scope.
Docker Compose is the correct tool: every service is defined, dependencies are declared,
and the entire platform starts with `docker compose up`.

---

## ADR-011 — Evaluation Framework Design

**Status:** Accepted

**Decision:**
- Failure scenarios implemented as Python scripts in `experiments/scenarios/`
- Experiment lifecycle managed via **REST API** (`/api/v1/experiments/`) plus a
  `experiments/runner.py` CLI wrapper for scripted batch runs
- REST API enables the frontend experiment management page; CLI enables overnight automation
- `ExperimentRun` records capture: scenario, detection mode, RCA mode, ground truth timestamps,
  measured latencies, and human grading
- Results exported to CSV via `/api/v1/experiments/{id}/results/export`
- Random seeds stored per experiment for reproducibility

**Rationale:**
REST API + CLI wrapper gives maximum flexibility: interactive use via dashboard, batch use
via runner script, and programmatic control from test harnesses.

---

## ADR-012 — Log Storage Architecture

**Status:** Accepted

**Decision:**
- Demo services POST structured JSON log batches to `/ingest/v1/logs`
- Recent logs buffered in Redis: per-service LPUSH/LTRIM list, **1000 entries max**, TTL 1 hour
- On incident creation: LRANGE → extract time-window subset → store as `log_snapshots` JSONB in PostgreSQL
- Logs Explorer queries Redis buffer (live) + PostgreSQL snapshots (historical/incident-linked)
- **No file-based fallback** — Redis buffer is sufficient for the demo environment scale

**Rationale:**
Redis buffer size of 1000 entries per service is sufficient for the 5-minute incident
detection window at expected traffic volumes. JSONB snapshot in PostgreSQL provides
persistent access without a dedicated log storage system.

---

## ADR-013 — Dual RCA Mode Design: RCA_BASELINE and RCA_AI

**Status:** Accepted

**Context:**
RQ2 compares LLM-assisted RCA against a deterministic baseline. The baseline must be
genuine — not artificially weak — for the comparison to have academic validity.

**Decision:**
Two RCA modes operate on the same `EvidencePackage` input and produce the same `RCAOutput` schema:

- **`RCA_BASELINE`** (`core/ai_pipeline/rule_rca.py`): 9-rule deterministic engine covering all
  8 failure scenarios. Rules reference specific metric thresholds and log patterns. Every
  conclusion cites evidence items from the EvidencePackage. No LLM call.
- **`RCA_AI`** (`core/ai_pipeline/pipeline.py`): LLMProvider-based analysis. Same EvidencePackage.
  Same output schema. LLM temperature fixed at 0 for reproducibility.

**Key invariant:** Both modes receive **identical EvidencePackage**. The comparison tests
reasoning quality, not evidence access.

**`analysis_metadata.rca_mode`** field (`"RULE_BASED"` | `"LLM_ASSISTED"`) is always recorded
for auditability.

**Rationale:**
A deterministic baseline:
- Makes RQ2 a fair, technically sound comparison
- Ensures the system is functional without any LLM API
- Provides a comprehensible, explainable alternative for viva
- Demonstrates understanding of rule-based expert systems alongside LLM integration

**Alternative rejected:** Using mock_rca as the baseline. Rejected because mock_rca is
designed for offline demos only (low confidence, minimal rules). RCA_BASELINE is a proper
engineered system, not a placeholder.

---

## ADR-014 — Configurable Detection and Scrape Intervals

**Status:** Accepted

**Context:**
The original architecture specified 30-second metric collection intervals. For a local
demonstration, this means failures may not be detected for up to 30 seconds after injection,
making live demos feel sluggish. More importantly, hard-coded timing values cannot be
adjusted without code changes.

**Decision:**
All timing values are configurable via environment variables with sensible defaults:

```
PROMETHEUS_SCRAPE_INTERVAL=10s       # in prometheus.yml
DETECTION_INTERVAL=10                # seconds; Celery Beat schedule
CORRELATION_WINDOW_SECONDS=90        # signal grouping window
DEDUP_WINDOW_SECONDS=300             # incident deduplication window
EXPERIMENT_RESET_WAIT_SECONDS=30     # wait after env reset
EXPERIMENT_OBSERVATION_WINDOW=600    # max seconds to wait for detection
EXPERIMENT_BASELINE_WINDOW=60        # steady-state collection before injection
```

The Celery Beat schedule reads `DETECTION_INTERVAL` from `Settings` at startup.
Prometheus scrape interval is templated into `prometheus.yml` at compose startup.

**No timing value is hard-coded in application source code.**

**Rationale:**
- 10s detection interval is appropriate for local demo (fast enough to be visually compelling)
- Configurable intervals allow the experiment protocol to be tuned without code changes
- Students can explain and justify these values during viva
- Shorter intervals increase CPU load slightly but are acceptable on local hardware

---

## Summary of All Decisions

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | Modular monolith backend | ✅ Accepted |
| ADR-002 | PostgreSQL primary database | ✅ Accepted |
| ADR-003 | Redis for cache + broker + log buffer | ✅ Accepted |
| ADR-004 | Celery background jobs | ✅ Accepted |
| ADR-005 | LLMProvider abstraction (no hard-coded model) | ✅ Accepted |
| ADR-006 | OpenTelemetry + Prometheus observability | ✅ Accepted |
| ADR-007 | React + TypeScript + Vite frontend | ✅ Accepted |
| ADR-008 | JWT authentication with simple roles | ✅ Accepted |
| ADR-009 | Hybrid detection engine (THRESHOLD_ONLY + HYBRID_CORRELATION) | ✅ Accepted |
| ADR-010 | Docker Compose only, no Kubernetes | ✅ Accepted |
| ADR-011 | Experiment controller: REST API + CLI wrapper | ✅ Accepted |
| ADR-012 | Log buffer: Redis 1000 entries/service, no file fallback | ✅ Accepted |
| ADR-013 | Dual RCA modes: RCA_BASELINE (rules) + RCA_AI (LLM) | ✅ Accepted |
| ADR-014 | All timing intervals configurable via environment variables | ✅ Accepted |

**All decisions are now accepted. No decisions are pending approval.**
