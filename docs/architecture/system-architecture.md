# ReliAI — System Architecture

> Version: 0.2 — Updated per architecture review
> Status: Architecture approved — implementation begins at Phase 1

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Repository Structure](#2-repository-structure)
3. [Component Architecture](#3-component-architecture)
4. [Database Design](#4-database-design)
5. [API Architecture](#5-api-architecture)
6. [Frontend Architecture](#6-frontend-architecture)
7. [AI RCA Pipeline](#7-ai-rca-pipeline)
8. [Observability Pipeline](#8-observability-pipeline)
9. [Demo Environment](#9-demo-environment)
10. [Docker Architecture](#10-docker-architecture)
11. [Security Architecture](#11-security-architecture)
12. [Viva Reference — Key Architectural Decisions](#12-viva-reference--key-architectural-decisions)

---

## 1. System Overview

ReliAI is a locally deployable, AI-assisted SRE (Site Reliability Engineering) platform that:

1. Monitors a controlled demo microservice environment
2. Ingests observability signals (metrics, logs, traces)
3. Detects incidents via a hybrid rule-based + correlation engine
4. Performs structured, evidence-grounded AI root cause analysis
5. Recommends human-approved remediation actions
6. Presents everything through a professional React dashboard

### High-Level Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                        DEMO ENVIRONMENT                              │
│                                                                      │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │ API Gateway│  │ User Service │  │ Order Service│  │ Postgres │  │
│  │  :8001     │  │   :8002      │  │   :8003      │  │  :5432   │  │
│  └──────┬─────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  │
│         │               │                  │               │        │
│    Prometheus metrics + OTel traces + structured JSON logs          │
└─────────┼───────────────┼──────────────────┼───────────────┼────────┘
          │               │                  │               │
          ▼               ▼                  ▼               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY LAYER                              │
│                                                                      │
│  Prometheus Server (:9090)     OTel Collector (:4317 OTLP)          │
│  - Scrapes /metrics endpoints  - Receives traces                     │
│  - Stores metric time series   - Forwards to ReliAI ingestor         │
└───────────────────────┬──────────────────────────────────────────────┘
                        │ Prometheus HTTP API + OTLP HTTP + Log POST
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  ReliAI BACKEND  (FastAPI :8000)                     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Ingestion Layer                                            │    │
│  │  MetricScraper (pulls Prometheus) · LogIngestor · TraceIngestor│ │
│  └───────────────────────────┬─────────────────────────────────┘    │
│                              │                                       │
│  ┌───────────────────────────▼─────────────────────────────────┐    │
│  │  Detection Engine                                           │    │
│  │  RuleEvaluator · AnomalyDetector · CorrelationEngine       │    │
│  │  → IncidentCreator                                          │    │
│  └───────────────────────────┬─────────────────────────────────┘    │
│                              │ Incident event                        │
│  ┌───────────────────────────▼─────────────────────────────────┐    │
│  │  AI RCA Pipeline  (Celery async task)                       │    │
│  │  EvidenceCollector → ContextBuilder → LLMClient →           │    │
│  │  OutputValidator → ConfidenceScorer → RCAStore              │    │
│  └───────────────────────────┬─────────────────────────────────┘    │
│                              │                                       │
│  ┌───────────────────────────▼─────────────────────────────────┐    │
│  │  REST API Layer  (FastAPI routers)                          │    │
│  │  /auth  /services  /incidents  /logs  /metrics  /traces     │    │
│  │  /analysis  /remediation  /analytics  /experiments          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  PostgreSQL (:5432)          Redis (:6379)                           │
│  - Incidents, analyses,      - Celery broker/result                  │
│    recommendations, users,   - API response cache                    │
│    experiment results        - Log buffer (TTL)                      │
└───────────────────────┬──────────────────────────────────────────────┘
                        │ REST JSON
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│              React / TypeScript Frontend  (Vite :5173)               │
│                                                                      │
│  Dashboard · Services · Incidents · Logs · Metrics · AI Analysis    │
│  Dependency Graph · Analytics · Postmortem · Settings               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Repository Structure

```
reliai/
│
├── frontend/                          # React 18 + TypeScript + Vite SRE Dashboard
│   ├── src/
│   │   ├── api/                       # Typed API client (React Query hooks)
│   │   ├── components/
│   │   │   ├── ui/                    # Base design system components
│   │   │   ├── charts/                # Recharts wrappers
│   │   │   ├── incidents/             # Incident-specific components
│   │   │   ├── services/              # Service monitoring components
│   │   │   └── ai/                    # AI analysis display components
│   │   ├── pages/                     # Route-level page components
│   │   ├── hooks/                     # Custom React hooks
│   │   ├── store/                     # Zustand global state (auth, settings)
│   │   ├── types/                     # Shared TypeScript types (mirrors API schemas)
│   │   └── utils/                     # Formatters, helpers
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── backend/                           # FastAPI modular monolith
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory
│   │   ├── config.py                  # Settings (pydantic-settings, .env)
│   │   ├── database.py                # SQLAlchemy async engine + session
│   │   ├── dependencies.py            # FastAPI dependency injection
│   │   │
│   │   ├── api/                       # REST API routers
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── services.py
│   │   │   │   ├── incidents.py
│   │   │   │   ├── logs.py
│   │   │   │   ├── metrics.py
│   │   │   │   ├── traces.py
│   │   │   │   ├── analysis.py
│   │   │   │   ├── remediation.py
│   │   │   │   ├── analytics.py
│   │   │   │   └── experiments.py
│   │   │   └── ingest/
│   │   │       ├── logs.py            # Log ingestion endpoint
│   │   │       └── traces.py          # Trace ingestion endpoint
│   │   │
│   │   ├── models/                    # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── service.py
│   │   │   ├── incident.py
│   │   │   ├── log_entry.py
│   │   │   ├── metric_snapshot.py
│   │   │   ├── ai_analysis.py
│   │   │   ├── remediation.py
│   │   │   └── experiment.py
│   │   │
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── service.py
│   │   │   ├── incident.py
│   │   │   ├── analysis.py
│   │   │   └── experiment.py
│   │   │
│   │   ├── core/                      # Core domain logic
│   │   │   ├── ingestion/
│   │   │   │   ├── metric_scraper.py  # Prometheus HTTP API client
│   │   │   │   ├── log_ingestor.py    # Process incoming log batches
│   │   │   │   └── trace_ingestor.py  # Process incoming traces
│   │   │   │
│   │   │   ├── detection/
│   │   │   │   ├── engine.py          # Detection orchestrator
│   │   │   │   ├── rules.py           # Threshold rule definitions
│   │   │   │   ├── evaluator.py       # Rule evaluation
│   │   │   │   ├── anomaly.py         # Simple statistical anomaly detection
│   │   │   │   ├── correlator.py      # Signal correlation engine
│   │   │   │   └── incident_creator.py
│   │   │   │
│   │   │   ├── ai_pipeline/
│   │   │   │   ├── pipeline.py        # Orchestrates RCA_AI pipeline
│   │   │   │   ├── rule_rca.py        # RCA_BASELINE: deterministic 9-rule engine
│   │   │   │   ├── evidence.py        # Evidence collection & formatting
│   │   │   │   ├── context_builder.py # Builds structured LLM prompt context
│   │   │   │   ├── providers/
│   │   │   │   │   ├── base.py        # LLMProvider abstract base class
│   │   │   │   │   ├── gemini.py      # GeminiProvider implementation
│   │   │   │   │   ├── openai_compat.py # OpenAICompatibleProvider
│   │   │   │   │   └── mock.py        # MockProvider (offline demo)
│   │   │   │   ├── output_validator.py# Validates RCA output against schema
│   │   │   │   ├── confidence.py      # Confidence scoring logic
│   │   │   │   └── dispatcher.py      # Selects the appropriate RCA mode per request
│   │   │   │
│   │   │   └── experiments/
│   │   │       ├── controller.py      # Experiment lifecycle management
│   │   │       └── metrics_store.py   # Writes experiment results to DB
│   │   │
│   │   ├── tasks/                     # Celery task definitions
│   │   │   ├── celery_app.py
│   │   │   ├── ai_analysis.py         # Async RCA task
│   │   │   ├── metric_collection.py   # Periodic metric snapshot task
│   │   │   └── anomaly_check.py       # Periodic anomaly detection task
│   │   │
│   │   └── utils/
│   │       ├── auth.py                # JWT helpers, password hashing
│   │       ├── pagination.py
│   │       └── time.py
│   │
│   ├── alembic/                       # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── .env.example
│
├── demo-services/                     # Controlled microservice environment
│   ├── api-gateway/                   # FastAPI reverse proxy + rate limiter
│   ├── user-service/                  # FastAPI CRUD service
│   ├── order-service/                 # FastAPI service with DB + Redis deps
│   ├── shared/                        # Shared OTel + Prometheus instrumentation
│   └── docker-compose.demo.yml        # Demo services only compose file
│
├── observability/
│   ├── prometheus/
│   │   └── prometheus.yml             # Scrape config targeting all services
│   └── otel-collector/
│       └── otel-collector-config.yaml # OTLP receiver → ReliAI exporter
│
├── experiments/
│   ├── scenarios/                     # Failure injection scripts
│   │   ├── http_500_spike.py
│   │   ├── high_latency.py
│   │   ├── db_connection_exhaustion.py
│   │   ├── redis_failure.py
│   │   ├── service_unavailable.py
│   │   ├── cascading_failure.py
│   │   └── memory_pressure.py
│   ├── runner.py                      # CLI experiment runner
│   └── analysis/                      # Result analysis notebooks / scripts
│
├── tests/
│   ├── unit/                          # Unit tests for core logic
│   ├── api/                           # FastAPI endpoint tests (HTTPX)
│   ├── integration/                   # DB integration tests
│   ├── ai_pipeline/                   # AI pipeline tests (mocked LLM)
│   └── e2e/                           # Playwright E2E tests
│
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── demo-service.Dockerfile
│
├── docker-compose.yml                 # Full platform compose (primary)
├── docker-compose.dev.yml             # Dev overrides (hot-reload, no rebuild)
│
├── docs/
│   ├── architecture/
│   │   ├── system-architecture.md    ← THIS FILE
│   │   ├── technical-decisions.md
│   │   └── development-roadmap.md
│   └── research/
│       └── evaluation-plan.md
│
└── README.md
```

---

## 3. Component Architecture

### 3.1 Backend Module Responsibilities

| Module | Responsibility | Key Classes |
|---|---|---|
| `api/v1/` | REST endpoint routing, request validation, response serialisation | FastAPI routers |
| `api/ingest/` | Receives log and trace batches from demo services | LogIngestRouter, TraceIngestRouter |
| `models/` | ORM table definitions and relationships | SQLAlchemy `DeclarativeBase` subclasses |
| `schemas/` | Pydantic input/output contracts | Request/Response schemas |
| `core/ingestion/` | Pulls metrics from Prometheus; processes incoming logs/traces | MetricScraper, LogIngestor |
| `core/detection/` | Evaluates rules, correlates signals, creates incidents | DetectionEngine, RuleEvaluator, Correlator |
| `core/ai_pipeline/` | Dispatches to the selected RCA mode; collects evidence; validates output | RCADispatcher, RuleRCA, RCAPipeline, AgenticRCAPipeline |
| `core/ai_pipeline/providers/` | LLMProvider abstraction; Gemini, OpenAI-compatible, Mock implementations | LLMProvider (ABC), GeminiProvider, MockProvider |
| `core/experiments/` | Manages experiment runs, records ground truth and results | ExperimentController |
| `tasks/` | Celery async task definitions | ai_analysis_task, metric_collection_task |

### 3.2 Detection Engine Detail

```
Trigger: Celery Beat schedules metric_collection_task every DETECTION_INTERVAL seconds
         (default: 10s, configurable via environment variable)

MetricScraper.pull()
    │
    ▼
RuleEvaluator.evaluate(metric_snapshots)
    │ Produces: List[RuleViolation]
    ▼
AnomalyDetector.check(recent_snapshots)   [if HYBRID mode]
    │ Produces: List[AnomalySignal]
    ▼
Correlator.correlate(violations, anomalies, dependency_graph)  [if HYBRID mode]
    │ Produces: CorrelationResult (affected_services, blast_radius, correlation_score)
    ▼
IncidentCreator.maybe_create(correlation_result)
    │ Only creates if: no open incident for same service cluster in last N minutes
    ▼
Incident record persisted to PostgreSQL
    │
    ▼
Celery task: ai_analysis_task(incident_id) enqueued
```

### 3.3 RCA Mode Dispatch

The `RCADispatcher` selects the analysis mode based on the `rca_mode` parameter passed
to the analysis task (derived from the experiment run config or API request):

| Mode | Implementation | LLM Call | Deterministic |
|---|---|---|---|
| `RCA_BASELINE` | `rule_rca.RuleBasedRCA` | No | Yes |
| `RCA_AI` | `pipeline.LLMRCAPipeline` | Yes | No (temperature=0) |
| `RCA_AI_NO_EVIDENCE` | `pipeline.LLMRCAPipeline` (with evidence stripped) | Yes | No (temperature=0) |
| `RCA_AI_NO_GRAPH` | `pipeline.LLMRCAPipeline` (with graph stripped) | Yes | No (temperature=0) |
| `RCA_AGENT` | `pipeline.AgenticRCAPipeline` | Yes | No (experimental tool-calling) |

*Note: `MockProvider` is an offline LLMProvider configuration, not an experimental mode.*

`RCA_BASELINE` and `RCA_AI` receive an identical `EvidencePackage` and all modes produce an
identical `RCAOutput` schema. The dispatcher records `rca_mode` in `analysis_metadata`.

### 3.4 AI RCA Pipeline Detail (`RCA_AI` path)

```
ai_analysis_task(incident_id, rca_mode)
    │
    ▼
EvidenceCollector.collect(incident)
    ├── Metric snapshots for affected services (from PostgreSQL)
    ├── Log excerpts from incident time window (from Redis buffer → PostgreSQL snapshot)
    ├── Trace references for affected services (from PostgreSQL)
    ├── Service dependency graph subgraph
    └── Recent similar incidents (from PostgreSQL)
    │
    ▼ EvidencePackage (typed, bounded in size)
    │
    ▼ [if rca_mode == RCA_BASELINE]
RuleBasedRCA.analyse(evidence)
    │ Applies 9 deterministic rules in priority order
    │ Every conclusion references evidence items from EvidencePackage
    └── Returns: RCAOutput (rca_mode="RULE_BASED", is_mock=false)

    ▼ [if rca_mode == RCA_AI]
ContextBuilder.build(incident, evidence)
    │ Produces: structured prompt with:
    │   - Incident summary (service, severity, timeline)
    │   - Metric evidence (tabular, delta from baseline)
    │   - Log excerpts (top N most relevant by timestamp proximity)
    │   - Dependency context (which services depend on affected ones)
    │   - Constraint: "Distinguish observed evidence from inference"
    │
    ▼ Prompt + JSON schema
    │
LLMProvider.complete(prompt, response_schema)
    ├── Provider selected by LLM_PROVIDER env var (gemini | openai_compatible)
    ├── Model selected by LLM_MODEL env var (no hard-coded model name)
    ├── Timeout: LLM_TIMEOUT_SECONDS (default: 30s)
    ├── Retry: 2 attempts with exponential backoff
    ├── On failure: falls back to MockProvider if AI_MOCK_MODE=true or API error
    └── Returns: raw JSON string
    │
    ▼
OutputValidator.validate(raw_json, RCAOutput schema)
    │ Pydantic validation; on failure: log error, store error result, low confidence
    │
    ▼ Validated RCAOutput
    │
ConfidenceScorer.score(rca_output, evidence)
    │ Adjusts LLM self-reported confidence based on evidence quantity/quality
    │ Evidence count floor: < 3 items → confidence capped at 0.4
    │
    ▼
RCAStore.save(incident_id, rca_output, confidence)
    │ Stores AIAnalysis record in PostgreSQL
    │ Updates Incident status to ANALYSED
    │
    ▼
RemediationStore.save(incident_id, recommendations)
    └── Stores RemediationRecommendation records
```

### 3.5 Agentic Tool-Calling Pipeline (`RCA_AGENT` path)

`RCA_AGENT` is an experimental variant intended to evaluate whether iterative, autonomous evidence retrieval improves RCA. It is NOT a replacement for `RCA_AI`.

**Constraints:**
- Bounded execution with configurable max tool calls, max iterations, and timeout.
- Bounded read-only tools: can only retrieve predefined observability data (metrics, logs, traces, dependency graph, incident timeline).
- No arbitrary code execution or autonomous remediation.
- Output strictly validated against the identical `RCAOutput` schema.

### 3.4 AI Output JSON Schema

```jsonc
{
  "root_cause": {
    "summary": "string — one sentence human-readable root cause",
    "affected_component": "string — service or component name",
    "failure_type": "enum: DEPENDENCY_FAILURE | RESOURCE_EXHAUSTION | CODE_ERROR | CONFIG_ERROR | CASCADING | UNKNOWN",
    "confidence": "float 0.0–1.0 — LLM self-reported confidence",
    "is_inference": "bool — true if conclusion goes beyond directly observed evidence"
  },
  "evidence_used": [
    {
      "type": "enum: METRIC | LOG | TRACE | DEPENDENCY",
      "source": "string — service or data source",
      "description": "string — what this evidence shows",
      "supports_hypothesis": "bool"
    }
  ],
  "alternative_hypotheses": [
    {
      "summary": "string",
      "confidence": "float",
      "reason_rejected": "string"
    }
  ],
  "suggested_investigation": [
    "string — specific actionable next step"
  ],
  "remediation_recommendations": [
    {
      "action": "string — specific action",
      "reason": "string — why this action",
      "expected_impact": "string",
      "risk": "enum: LOW | MEDIUM | HIGH",
      "requires_human_approval": true
    }
  ],
  "analysis_metadata": {
    "model_used": "string",
    "evidence_count": "int",
    "analysis_duration_ms": "int",
    "is_mock": "bool"
  }
}
```

---

## 4. Database Design

### Design Principles

1. PostgreSQL stores **durable state** only: incidents, analyses, recommendations, users,
   service registry, experiment results, and metric snapshots.
2. Raw high-volume observability data (log streams) is NOT stored in PostgreSQL.
   Redis buffers recent logs; PostgreSQL stores snapshots attached to incidents.
3. JSONB columns are used where the structure is known but variable (e.g., AI output,
   evidence payload, metric label sets).

### 4.1 Entity-Relationship Overview

```
users ──────────────────────────────────────────────────────────────────┐
                                                                        │ created_by
services ─────────────────────────┐                                     │
    │                             │ service_dependencies                 │
    │                             ▼                                     │
    │                    service_dependencies                            │
    │                                                                    │
    ▼                                                                    │
incidents ──────────────────┐                                           │
    │                       │                                           │
    ├── incident_services ──┘  (many-to-many: incident ↔ service)      │
    │                                                                    │
    ├── incident_events (timeline events)                                │
    │                                                                    │
    ├── metric_snapshots (metric state at incident time)                 │
    │                                                                    │
    ├── log_snapshots (log excerpts at incident time)                    │
    │                                                                    │
    ├── ai_analyses ─────────────────────────────────────────────┐      │
    │       │                                                     │      │
    │       └── remediation_recommendations                       │      │
    │                                                             │      │
    └── experiment_results                                        │      │
                                                                  │      │
experiments ──────────────────────────────────────────────────────┘      │
    └── experiment_runs                                                   │

refresh_tokens ──── users                                                │
```

### 4.2 Table Definitions

#### `users`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | VARCHAR(255) UNIQUE NOT NULL | |
| password_hash | VARCHAR(255) NOT NULL | bcrypt |
| role | ENUM('admin','engineer','viewer') NOT NULL | |
| display_name | VARCHAR(100) | |
| is_active | BOOLEAN DEFAULT true | |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

#### `refresh_tokens`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| token_hash | VARCHAR(255) NOT NULL | SHA-256 of token |
| expires_at | TIMESTAMPTZ NOT NULL | |
| revoked | BOOLEAN DEFAULT false | |
| created_at | TIMESTAMPTZ NOT NULL | |

#### `services`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(100) UNIQUE NOT NULL | e.g. `order-service` |
| display_name | VARCHAR(150) | |
| description | TEXT | |
| service_type | ENUM('api','database','cache','queue','gateway') | |
| prometheus_job | VARCHAR(100) | Label for Prometheus scrape job |
| base_url | VARCHAR(255) | Internal Docker network URL |
| slo_availability | FLOAT | Target availability SLO, e.g. 0.999 |
| slo_latency_p99_ms | INTEGER | P99 latency SLO in ms |
| is_active | BOOLEAN DEFAULT true | |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

#### `service_dependencies`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| source_service_id | UUID FK → services.id | The caller |
| target_service_id | UUID FK → services.id | The dependency |
| dependency_type | ENUM('http','database','cache','queue') | |
| is_critical | BOOLEAN DEFAULT true | Failure propagates? |
| created_at | TIMESTAMPTZ NOT NULL | |

#### `incidents`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| title | VARCHAR(255) NOT NULL | Auto-generated from detection |
| description | TEXT | |
| severity | ENUM('CRITICAL','HIGH','MEDIUM','LOW') NOT NULL | |
| status | ENUM('OPEN','INVESTIGATING','ANALYSED','RESOLVED','FALSE_POSITIVE') | |
| detection_mode | ENUM('THRESHOLD_ONLY','HYBRID_CORRELATION') NOT NULL | Records which mode was active |
| detected_at | TIMESTAMPTZ NOT NULL | When system detected the incident |
| resolved_at | TIMESTAMPTZ | |
| created_by_rule | VARCHAR(100) | Rule/correlator that triggered this |
| correlation_score | FLOAT | Score from correlation engine (0–1) |
| blast_radius | INTEGER | Number of potentially affected services |
| experiment_run_id | UUID FK → experiment_runs.id NULL | Set if part of experiment |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

#### `incident_services` (junction table)
| Column | Type | Notes |
|---|---|---|
| incident_id | UUID FK → incidents.id | |
| service_id | UUID FK → services.id | |
| role | ENUM('primary','secondary','affected') | |
| PRIMARY KEY | (incident_id, service_id) | |

#### `incident_events`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| incident_id | UUID FK → incidents.id | |
| event_type | ENUM('DETECTED','STATUS_CHANGED','AI_ANALYSIS_STARTED','AI_ANALYSIS_COMPLETE','REMEDIATION_APPLIED','COMMENT','RESOLVED') | |
| message | TEXT NOT NULL | |
| actor | VARCHAR(100) | 'system' or user email |
| metadata | JSONB | Additional event-specific data |
| occurred_at | TIMESTAMPTZ NOT NULL | |

#### `metric_snapshots`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| service_id | UUID FK → services.id | |
| incident_id | UUID FK → incidents.id NULL | NULL for periodic snapshots |
| metric_name | VARCHAR(100) NOT NULL | e.g. `http_request_duration_seconds` |
| metric_labels | JSONB | Prometheus label set |
| value | FLOAT NOT NULL | |
| timestamp | TIMESTAMPTZ NOT NULL | When metric was measured |

#### `log_snapshots`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| incident_id | UUID FK → incidents.id | |
| service_id | UUID FK → services.id | |
| window_start | TIMESTAMPTZ NOT NULL | |
| window_end | TIMESTAMPTZ NOT NULL | |
| entries | JSONB NOT NULL | Array of log entry objects |
| entry_count | INTEGER NOT NULL | |
| created_at | TIMESTAMPTZ NOT NULL | |

*Log entry JSONB structure:*
```json
{
  "timestamp": "ISO8601",
  "level": "ERROR|WARN|INFO|DEBUG",
  "message": "string",
  "service": "string",
  "trace_id": "string|null",
  "span_id": "string|null",
  "extra": {}
}
```

#### `ai_analyses`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| incident_id | UUID FK → incidents.id UNIQUE | One analysis per incident |
| model_used | VARCHAR(100) | e.g. `gemini-2.0-flash` |
| is_mock | BOOLEAN NOT NULL | True if generated by mock_rca |
| root_cause_summary | TEXT NOT NULL | |
| affected_component | VARCHAR(100) | |
| failure_type | ENUM(...) | |
| llm_confidence | FLOAT | Raw LLM self-reported confidence |
| adjusted_confidence | FLOAT | After evidence-quantity adjustment |
| evidence_used | JSONB NOT NULL | Array of evidence objects |
| alternative_hypotheses | JSONB | |
| suggested_investigation | JSONB | Array of strings |
| full_output | JSONB NOT NULL | Complete validated LLM output |
| evidence_count | INTEGER | |
| analysis_duration_ms | INTEGER | |
| prompt_tokens | INTEGER NULL | |
| completion_tokens | INTEGER NULL | |
| error | TEXT NULL | If analysis failed |
| created_at | TIMESTAMPTZ NOT NULL | |

#### `remediation_recommendations`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| incident_id | UUID FK → incidents.id | |
| ai_analysis_id | UUID FK → ai_analyses.id | |
| action | TEXT NOT NULL | |
| reason | TEXT NOT NULL | |
| expected_impact | TEXT | |
| risk | ENUM('LOW','MEDIUM','HIGH') NOT NULL | |
| status | ENUM('PENDING','APPROVED','REJECTED','APPLIED') DEFAULT 'PENDING' | |
| approved_by | UUID FK → users.id NULL | |
| approved_at | TIMESTAMPTZ NULL | |
| created_at | TIMESTAMPTZ NOT NULL | |

#### `experiments`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(150) NOT NULL | |
| description | TEXT | |
| created_by | UUID FK → users.id | |
| created_at | TIMESTAMPTZ NOT NULL | |

#### `experiment_runs`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| experiment_id | UUID FK → experiments.id | |
| scenario_name | VARCHAR(100) NOT NULL | e.g. `http_500_spike` |
| detection_mode | ENUM('THRESHOLD_ONLY','HYBRID_CORRELATION') NOT NULL | |
| failure_injected_at | TIMESTAMPTZ NULL | Ground truth: when failure was triggered |
| incident_detected_at | TIMESTAMPTZ NULL | When system created incident |
| detection_latency_ms | INTEGER NULL | Computed: incident_detected_at - failure_injected_at |
| rca_started_at | TIMESTAMPTZ NULL | |
| rca_completed_at | TIMESTAMPTZ NULL | |
| ai_diagnosis_latency_ms | INTEGER NULL | |
| rca_correct | BOOLEAN NULL | Human-graded after run |
| false_positive | BOOLEAN NULL | |
| notes | TEXT | |
| status | ENUM('RUNNING','COMPLETED','FAILED') | |
| started_at | TIMESTAMPTZ NOT NULL | |
| completed_at | TIMESTAMPTZ NULL | |
| raw_results | JSONB | Full result dump for offline analysis |

---

## 5. API Architecture

### Design Principles
- All endpoints are prefixed `/api/v1/`
- Ingestion endpoints are prefixed `/ingest/v1/` (API-key authenticated, not JWT)
- All responses follow a consistent envelope where practical
- Authentication: Bearer JWT except ingest endpoints (API key header)
- Pagination: cursor-based for logs; offset-based for incidents/services

### 5.1 Authentication

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Register new user | None |
| POST | `/api/v1/auth/login` | Login, receive access + refresh tokens | None |
| POST | `/api/v1/auth/refresh` | Refresh access token | Refresh token cookie |
| POST | `/api/v1/auth/logout` | Revoke refresh token | JWT |
| GET | `/api/v1/auth/me` | Get current user profile | JWT |

### 5.2 Services

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/services` | List all services with health summary | JWT |
| POST | `/api/v1/services` | Register a service | JWT (admin) |
| GET | `/api/v1/services/{id}` | Service detail + recent metrics | JWT |
| PUT | `/api/v1/services/{id}` | Update service metadata/SLOs | JWT (admin) |
| GET | `/api/v1/services/{id}/health` | Current health status | JWT |
| GET | `/api/v1/services/{id}/metrics` | Recent metric snapshots | JWT |
| GET | `/api/v1/services/{id}/incidents` | Incidents for this service | JWT |
| GET | `/api/v1/services/{id}/dependencies` | Dependency graph for this service | JWT |

### 5.3 Incidents

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/incidents` | List incidents (filter: status, severity, service, date) | JWT |
| POST | `/api/v1/incidents` | Manually create incident | JWT (engineer+) |
| GET | `/api/v1/incidents/{id}` | Incident detail with full timeline | JWT |
| PATCH | `/api/v1/incidents/{id}` | Update status, add comment | JWT |
| GET | `/api/v1/incidents/{id}/events` | Incident timeline events | JWT |
| GET | `/api/v1/incidents/{id}/signals` | Related metrics/logs for incident | JWT |
| POST | `/api/v1/incidents/{id}/resolve` | Mark incident resolved | JWT (engineer+) |

### 5.4 AI Analysis

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/analysis/{incident_id}` | Get RCA for incident | JWT |
| POST | `/api/v1/analysis/{incident_id}/trigger` | Manually trigger RCA | JWT (engineer+) |
| GET | `/api/v1/analysis/{incident_id}/evidence` | Get evidence used | JWT |
| GET | `/api/v1/analysis/{incident_id}/postmortem` | Get AI postmortem report | JWT |

### 5.5 Remediation

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/remediation/{incident_id}` | Get recommendations for incident | JWT |
| POST | `/api/v1/remediation/{id}/approve` | Approve a recommendation | JWT (engineer+) |
| POST | `/api/v1/remediation/{id}/reject` | Reject a recommendation | JWT (engineer+) |

### 5.6 Logs

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/logs` | Query logs (filter: service, level, time, query) | JWT |
| GET | `/api/v1/logs/live` | Live log stream (SSE) | JWT |

### 5.7 Metrics

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/metrics/summary` | Aggregated platform-wide metrics | JWT |
| GET | `/api/v1/metrics/{service_id}` | Metrics for service (time range) | JWT |
| GET | `/api/v1/metrics/slo` | SLO status for all services | JWT |

### 5.8 Analytics

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/analytics/incidents` | Incident frequency over time | JWT |
| GET | `/api/v1/analytics/mttr` | Mean time to resolution | JWT |
| GET | `/api/v1/analytics/services/reliability` | Reliability scores per service | JWT |
| GET | `/api/v1/analytics/detection` | Detection accuracy stats | JWT (admin) |

### 5.9 Experiments

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/experiments` | List experiments | JWT (admin) |
| POST | `/api/v1/experiments` | Create experiment definition | JWT (admin) |
| POST | `/api/v1/experiments/{id}/runs` | Start experiment run | JWT (admin) |
| GET | `/api/v1/experiments/{id}/runs` | List runs for experiment | JWT (admin) |
| GET | `/api/v1/experiments/{id}/runs/{run_id}` | Run detail + results | JWT (admin) |
| POST | `/api/v1/experiments/{id}/runs/{run_id}/grade` | Human-grade RCA result | JWT (admin) |
| GET | `/api/v1/experiments/{id}/results/export` | Export results CSV | JWT (admin) |

### 5.10 Ingestion (API-key authenticated)

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| POST | `/ingest/v1/logs` | Batch log ingestion from demo services | API Key |
| POST | `/ingest/v1/traces` | Batch trace ingestion | API Key |

---

## 6. Frontend Architecture

### 6.1 Page/Route Map

| Route | Page | Key Components |
|---|---|---|
| `/` | Redirect to `/dashboard` | — |
| `/dashboard` | SRE Dashboard | HealthSummaryBar, MetricCards, IncidentFeed, ServiceStatusGrid, ErrorRateChart |
| `/services` | Service List | ServiceTable, HealthBadge, SLOIndicator |
| `/services/:id` | Service Detail | ServiceHeader, MetricsPanel, DependencyMiniGraph, IncidentHistory |
| `/incidents` | Incident List | IncidentTable, FilterBar, SeverityBadge, StatusBadge |
| `/incidents/:id` | Incident Detail | IncidentHeader, Timeline, SignalsPanel, AIAnalysisPanel, RemediationPanel |
| `/logs` | Logs Explorer | LogSearchBar, LogLevelFilter, ServiceFilter, LogTable, LiveToggle |
| `/metrics` | Metrics Explorer | ServiceSelector, MetricSelector, TimeRangeSelector, MetricChart |
| `/dependencies` | Dependency Graph | ServiceGraph (React Flow), DependencyLegend, ServiceDetailDrawer |
| `/ai-analysis` | AI Analysis List | AnalysisTable, ConfidenceIndicator, EvidenceDrawer |
| `/analytics` | Analytics | IncidentFrequencyChart, MTTRChart, ReliabilityHeatmap, SLOSummary |
| `/experiments` | Experiment Manager | ExperimentTable, RunTable, ResultsChart |
| `/settings` | Settings | ProfileForm, APIKeyManager, ThemeToggle |
| `/login` | Login | LoginForm |

### 6.2 Component Hierarchy

```
App
├── AuthProvider (Zustand auth store)
├── QueryClientProvider (TanStack Query)
│
├── AuthLayout
│   └── LoginPage
│
└── AppLayout
    ├── Sidebar (navigation, service health mini-indicators)
    ├── TopBar (user menu, notification bell, dark mode toggle)
    │
    └── [Page Content]
        │
        ├── ui/                     # Base design system
        │   ├── Button
        │   ├── Badge (severity/status colours)
        │   ├── Card
        │   ├── Table (sortable, paginated)
        │   ├── Modal
        │   ├── Drawer
        │   ├── Tabs
        │   ├── Select
        │   ├── DateRangePicker
        │   ├── Skeleton (loading states)
        │   ├── EmptyState
        │   └── ErrorBoundary
        │
        ├── charts/
        │   ├── TimeSeriesChart (Recharts LineChart wrapper)
        │   ├── BarChart
        │   ├── SLOGauge
        │   └── HeatmapChart
        │
        ├── incidents/
        │   ├── IncidentTable
        │   ├── IncidentCard
        │   ├── IncidentTimeline
        │   ├── SeverityBadge
        │   └── StatusBadge
        │
        ├── services/
        │   ├── ServiceCard
        │   ├── ServiceTable
        │   ├── HealthBadge
        │   └── SLOProgressBar
        │
        ├── ai/
        │   ├── RCAPanel
        │   ├── EvidenceList
        │   ├── ConfidenceBar
        │   ├── AlternativeHypotheses
        │   └── RemediationRecommendations
        │
        └── graph/
            ├── ServiceDependencyGraph (React Flow)
            └── GraphLegend
```

### 6.3 State Management

| State Type | Solution | Rationale |
|---|---|---|
| Server state (API data) | TanStack Query | Caching, refetch intervals, optimistic updates |
| Auth state | Zustand | Lightweight, persist to localStorage |
| UI state (modals, filters) | React local state / URL params | Keep simple |
| Live log stream | EventSource (SSE) hook | Browser-native, no library needed |
| Theme | CSS variables + localStorage | No library overhead |

### 6.4 API Client Structure

```
src/api/
├── client.ts           # Axios instance with JWT interceptors, error handling
├── hooks/
│   ├── useServices.ts  # React Query hooks for /services
│   ├── useIncidents.ts # React Query hooks for /incidents
│   ├── useLogs.ts      # Query hooks + SSE for live logs
│   ├── useMetrics.ts
│   ├── useAnalysis.ts
│   └── useExperiments.ts
└── types/              # TypeScript interfaces mirroring Pydantic schemas
```

---

## 7. AI RCA Pipeline

*(Detailed flow described in Section 3.3 and 3.4)*

### 7.1 LLMProvider Abstraction

The AI pipeline does not call any LLM provider directly. All LLM access goes through
`LLMProvider`, an abstract base class in `core/ai_pipeline/providers/base.py`:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        response_schema: dict,
        temperature: float = 0.0
    ) -> str: ...

class GeminiProvider(LLMProvider): ...          # Uses LLM_MODEL from env
class OpenAICompatibleProvider(LLMProvider): .. # OpenAI-format API
class MockProvider(LLMProvider): ...            # Deterministic, no API call
```

**Configuration (all via environment variables — nothing hard-coded):**
```
LLM_PROVIDER=gemini          # or: openai_compatible
LLM_MODEL=gemini-2.0-flash   # any model name; set at deployment
LLM_API_KEY=...              # secret; never in source code
LLM_TIMEOUT_SECONDS=30
AI_MOCK_MODE=false
```

### 7.2 Hallucination Mitigation Strategy

1. **Evidence-bounded prompts:** The LLM receives only verified evidence extracted from
   the system. Prompt explicitly states: *"Base your analysis ONLY on the evidence provided.
   Clearly mark any inference as such."*
2. **Structured output enforcement:** LLMProvider uses the provider's JSON/structured output
   mode with an explicit Pydantic-derived schema — prevents free-form narrative.
3. **`is_inference` flag:** The schema requires the LLM to flag when the root cause goes
   beyond direct evidence.
4. **Pydantic validation:** Any response not conforming to the schema is rejected; a partial
   result with `confidence=0.0` is stored with an error flag.
5. **Evidence count floor:** Fewer than 3 evidence items → confidence capped at 0.4.
6. **Baseline comparison:** RCA_BASELINE provides a ground-truth anchor for evaluating
   whether RCA_AI conclusions are reasonable.

### 7.3 LLM Failure Handling

| Failure Type | Handling |
|---|---|
| API timeout (> `LLM_TIMEOUT_SECONDS`) | Cancel request, retry once with backoff; second failure → MockProvider |
| Rate limit (429) | Exponential backoff (1s, 2s, 4s) × 3 retries |
| API error (5xx) | Immediate fallback to MockProvider |
| Schema validation failure | Store error result, set `adjusted_confidence=0.0`, flag for review |
| `AI_MOCK_MODE=true` | Skip LLMProvider entirely, route to MockProvider |

### 7.4 MockProvider (Offline Demo Mode)

`providers/mock.py` `MockProvider`:
- Takes same `EvidencePackage` as live providers
- Applies a small fixed set of pattern-matching rules
- Returns valid `RCAOutput` with `is_mock=true` and `confidence=0.5`
- Activation: `AI_MOCK_MODE=true` env var or automatic on API failure
- **Distinct from `RCA_BASELINE`:** MockProvider is for offline demos only.
  RCA_BASELINE is a genuine evaluation baseline with full rule coverage.

---

## 8. Observability Pipeline

```
Demo Service
├── /metrics (Prometheus exposition format)          ← Scraped by Prometheus
├── OTLP gRPC :4317                                  ← Traces sent to OTel Collector
└── POST /ingest/v1/logs  (JSON batch)               ← Logs pushed to ReliAI

Prometheus Server
├── Scrapes all demo services + ReliAI backend
├── Scrape interval: PROMETHEUS_SCRAPE_INTERVAL (default: 10s)
└── HTTP API at :9090 queried by MetricScraper

OTel Collector
├── Receives OTLP traces
└── Forwards to ReliAI /ingest/v1/traces

ReliAI Backend
├── MetricScraper (Celery Beat task, every DETECTION_INTERVAL seconds, default: 10s)
│   └── Queries Prometheus HTTP API → stores MetricSnapshot in PostgreSQL
│
├── LogIngestor (/ingest/v1/logs)
│   ├── Validates and parses log batch
│   ├── Writes to Redis LPUSH (per-service list, LTRIM to 1000 entries)
│   └── On incident creation: LRANGE → store LogSnapshot in PostgreSQL
│
└── TraceIngestor (/ingest/v1/traces)
    └── Stores trace references (trace_id, root span summary) in PostgreSQL
        (not full spans — avoids TSDB problem)
```

**Configurable timing (all environment variables, no hard-coded values):**
```
PROMETHEUS_SCRAPE_INTERVAL=10s
DETECTION_INTERVAL=10
CORRELATION_WINDOW_SECONDS=90
DEDUP_WINDOW_SECONDS=300
```

### Metrics Collected from Demo Services

| Metric | Type | Description |
|---|---|---|
| `http_requests_total` | Counter | By service, method, path, status |
| `http_request_duration_seconds` | Histogram | Latency distribution |
| `http_requests_in_flight` | Gauge | Active requests |
| `db_connection_pool_size` | Gauge | Pool size |
| `db_connection_pool_available` | Gauge | Free connections |
| `db_query_duration_seconds` | Histogram | DB query latency |
| `redis_operations_total` | Counter | Redis ops by command, result |
| `process_resident_memory_bytes` | Gauge | RSS memory |
| `process_cpu_seconds_total` | Counter | CPU time |

---

## 9. Demo Environment

### Services

| Service | Port | Role | Dependencies |
|---|---|---|---|
| api-gateway | 8001 | Routes requests to User/Order services | user-service, order-service |
| user-service | 8002 | User CRUD + auth | PostgreSQL |
| order-service | 8003 | Order processing | PostgreSQL, Redis, user-service |
| PostgreSQL | 5432 | Shared database for demo services | — |
| Redis | 6379 | Session cache for demo services | — |

All services are instrumented with:
- `prometheus_fastapi_instrumentator` (auto-exposes `/metrics`)
- `opentelemetry-sdk` with OTLP exporter
- `structlog` for JSON structured logging

### Failure Scenario Implementations

| Scenario | Mechanism | Trigger |
|---|---|---|
| HTTP 500 spike | Feature flag in order-service forces 500 on /orders | POST `/api/v1/experiments/{id}/runs` |
| High latency | Artificial `await asyncio.sleep(N)` in service handlers | Experiment controller |
| DB connection exhaustion | Deliberately hold connections without releasing | Experiment script |
| DB latency | `pg_sleep(N)` injected via raw query in test mode | Experiment script |
| Redis failure | Stop Redis container via Docker API (docker-py) | Experiment script |
| Service unavailable | Stop demo service container via Docker API | Experiment script |
| Cascading failure | Stop user-service → order-service degrades | Experiment script |
| Memory pressure | Allocate large list in service memory | Experiment script |

---

## 10. Docker Architecture

### `docker-compose.yml` (Full Platform)

```yaml
services:
  # Infrastructure
  postgres:         # PostgreSQL 15-alpine
  redis:            # Redis 7-alpine

  # Observability
  prometheus:       # prom/prometheus — scrapes demo services + backend

  # OTel Collector
  otel-collector:   # otel/opentelemetry-collector-contrib

  # Demo environment
  api-gateway:      # demo-services/api-gateway
  user-service:     # demo-services/user-service
  order-service:    # demo-services/order-service

  # ReliAI Platform
  backend:          # ReliAI FastAPI backend
  worker:           # Celery worker (same image as backend)
  beat:             # Celery Beat scheduler (same image)
  frontend:         # React/Vite frontend (nginx in production)
```

**Health check chain:**
```
postgres → backend, demo services
redis → backend, worker, beat
backend → frontend (API_URL env var)
postgres + redis → worker, beat
```

---

## 11. Security Architecture

| Concern | Implementation |
|---|---|
| Password storage | bcrypt (cost factor 12) via `passlib` |
| JWT signing | HS256, secret from environment variable |
| Refresh tokens | Stored as SHA-256 hash in PostgreSQL; rotated on use |
| API keys (ingest) | Stored as SHA-256 hash; passed as `X-API-Key` header |
| CORS | FastAPI CORSMiddleware; origin list from environment variable |
| Input validation | Pydantic v2 strict mode on all request bodies |
| SQL injection | SQLAlchemy ORM / parameterised queries only |
| Secrets | All secrets via environment variables; `.env.example` provided, never committed |
| Rate limiting | `slowapi` on auth endpoints (login: 5/min, register: 3/min) |
| LLM API key | `LLM_API_KEY` environment variable; never logged, never in source code |

---

## 12. Viva Reference — Key Architectural Decisions

> This section summarises the 10 most important decisions for academic viva examination.
> For each: what was chosen, why, what alternative was rejected, and what trade-off was accepted.

---

### V1. Modular Monolith Backend

| | |
|---|---|
| **Chosen** | Single FastAPI process, structured into discrete Python packages |
| **Why** | Individual project; simpler debugging; each module independently explainable |
| **Rejected** | Full microservices backend (service discovery, distributed tracing overhead) |
| **Trade-off** | Less realistic distributed backend, but demo services are separate — demonstrating distributed systems concepts where it matters |

---

### V2. LLMProvider Abstraction (No Hard-Coded Model)

| | |
|---|---|
| **Chosen** | Abstract `LLMProvider` interface; model/provider set via environment variables |
| **Why** | Model names change; hard-coding `gemini-2.0-flash` makes the architecture fragile |
| **Rejected** | Direct SDK calls with specific model version; LangChain abstraction |
| **Trade-off** | Slightly more code (interface + implementations) for significantly better flexibility and maintainability |

---

### V3. Multi-Mode RCA Design

| | |
|---|---|
| **Chosen** | Multiple RCA engines where `RCA_BASELINE` and `RCA_AI` receive identical full `EvidencePackage` and all produce identical `RCAOutput` schema |
| **Why** | RQ2 requires a fair comparison; baseline must be genuine, not a strawman |
| **Rejected** | Using MockProvider as the baseline (too weak); no baseline at all |
| **Trade-off** | Implementing 9 deterministic rules takes time but produces academically valid results and a system that works without LLM |

---

### V4. Hybrid Detection: Two Modes on Same Codebase

| | |
|---|---|
| **Chosen** | `DetectionMode` enum with `THRESHOLD_ONLY` and `HYBRID_CORRELATION` paths in the same engine |
| **Why** | RQ1 requires controlled comparison with identical environment; separate implementations would introduce confounding variables |
| **Rejected** | Separate detection services; single mode only |
| **Trade-off** | Detection engine is slightly more complex; mode switching requires an env/config change, not a code change |

---

### V5. PostgreSQL Only — No TSDB

| | |
|---|---|
| **Chosen** | PostgreSQL for all durable state; Prometheus for raw metric time series; Redis for live log buffer |
| **Why** | Avoids deploying InfluxDB/TimescaleDB/VictoriaMetrics — one more system to maintain and explain |
| **Rejected** | TimescaleDB for metric storage; separate log database |
| **Trade-off** | Cannot store arbitrary long metric history in PostgreSQL; only periodic snapshots. Acceptable for demo scale where Prometheus retains history |

---

### V6. Configurable Detection Intervals

| | |
|---|---|
| **Chosen** | All timing values (`DETECTION_INTERVAL`, `CORRELATION_WINDOW_SECONDS`, etc.) from environment variables |
| **Why** | Hard-coded 30s interval makes demos slow and cannot be adjusted for experiments without code changes |
| **Rejected** | Hard-coded constants in source code |
| **Trade-off** | Requires documenting environment variables; adds to `.env.example` but is strictly better engineering |

---

### V7. Evidence-Grounded AI Prompting

| | |
|---|---|
| **Chosen** | LLM receives a structured, bounded `EvidencePackage` — not free-form text or a raw alert message |
| **Why** | Prevents hallucination; ensures AI conclusions are traceable to observed signals |
| **Rejected** | "Something failed, diagnose it" prompts; unstructured text blobs |
| **Trade-off** | Evidence collection and context building adds code complexity; `EvidencePackage` must be populated correctly for AI quality |

---

### V8. Celery for Background RCA (Async Job Queue)

| | |
|---|---|
| **Chosen** | Celery 5 with Redis broker for AI analysis tasks |
| **Why** | LLM API calls (5–30s) must not block REST API; Celery Beat needed for periodic metric collection |
| **Rejected** | FastAPI `BackgroundTasks` (no retry, no persistence); ARQ (less documentation) |
| **Trade-off** | Adds operational complexity (worker + beat processes); simpler for students to explain than Kafka |

---

### V9. Paired Experiment Design with Full Environment Reset

| | |
|---|---|
| **Chosen** | Each scenario run is preceded by automated full environment reset (container restart, Redis flush, 30s stabilisation wait) |
| **Why** | Prevents contamination between runs; ensures detection latency measurements are unaffected by prior state |
| **Rejected** | Sequential runs without reset (risks leftover incidents, stale logs, DB connection state) |
| **Trade-off** | Adds ~2–3 minutes to total experiment time per run; total runtime ~8–10 hours for 80 runs (overnight) |

---

### V10. React + TanStack Query + Recharts (No Heavy UI Framework)

| | |
|---|---|
| **Chosen** | React 18 + TypeScript + Vite + TanStack Query + Recharts + Radix UI + custom CSS |
| **Why** | Material UI/Ant Design produce generic-looking dashboards; Next.js SSR is unnecessary for a local tool |
| **Rejected** | Next.js (SSR overhead), Material UI (generic look), Tailwind (acceptable but adds build dependency) |
| **Trade-off** | Custom CSS design system takes initial time but produces a distinctive, professional-looking dashboard |

---

*Next: See [development-roadmap.md](development-roadmap.md) for phased implementation plan.*
*See [technical-decisions.md](technical-decisions.md) for full ADRs.*
*See [../research/evaluation-plan.md](../research/evaluation-plan.md) for experimental methodology.*
