# ReliAI

**ReliAI: An Intelligent Platform for Automated Incident Detection, Root Cause Analysis and Reliability Management**

> B.Tech CSE Major Project · Full-Stack AI-Assisted SRE Platform · Locally Deployable via Docker Compose
> Architecture v0.2 is approved — All 14 ADRs are accepted — Phase 0 and Phase 1 (Repository & Dev Infrastructure) are complete — Phase 2 has not started yet

---

## Problem Statement

Modern software systems are increasingly distributed, making manual incident diagnosis slow,
error-prone, and costly. On-call engineers face an overwhelming volume of alerts, logs, and
metrics that must be correlated quickly under pressure. Traditional threshold-based monitoring
generates noise without context. Large-scale AIOps platforms exist but are commercial, opaque,
and require real production infrastructure.

**ReliAI** addresses these problems by providing a locally deployable, open, and explainable
AI-assisted reliability platform that:

- Monitors a realistic controlled microservice environment
- Correlates observability signals (logs, metrics, traces) into meaningful incidents
- Applies structured, evidence-grounded LLM reasoning to perform root cause analysis
- Recommends human-approved remediation actions
- Provides a professional SRE dashboard for full incident lifecycle management

---

## Objectives

1. Design and implement a full-stack AI-assisted SRE platform demonstrating backend engineering,
   distributed systems concepts, observability, and AI/LLM integration.
2. Build a realistic controlled demo microservice environment capable of generating real failures.
3. Implement a hybrid incident detection engine combining rule-based thresholds and signal correlation.
4. Design and implement a structured evidence-driven AI RCA pipeline using an LLM API (Gemini / OpenAI-compatible).
5. Deliver a professional React/TypeScript dashboard for incident management and reliability monitoring.
6. Conduct a rigorous comparative evaluation of the proposed hybrid approach vs. traditional
   threshold-only detection, producing real measurable results.
7. Produce complete academic documentation supporting all dissertation chapters.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Demo Environment                          │
│  API Gateway · User Service · Order Service · PostgreSQL · Redis │
└───────────────────────────┬─────────────────────────────────────┘
                            │  Logs · Metrics · Traces
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Observability Layer                            │
│          OpenTelemetry SDK · Prometheus · Structured Logs        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              ReliAI Backend  (FastAPI · Python)                  │
│                                                                  │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Ingestion Layer│  │ Detection Engine │  │  Incident Store │  │
│  │ (logs/metrics) │─▶│ (rules + correl.)│─▶│  (PostgreSQL)   │  │
│  └────────────────┘  └──────────────────┘  └───────┬─────────┘  │
│                                                     │            │
│  ┌─────────────────────────────────────────────────▼──────────┐  │
│  │                  AI RCA Pipeline                           │  │
│  │  Evidence Collection → Context Build → LLM Call →         │  │
│  │  Structured Output → Validation → Confidence Score         │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌──────────────────┐                        │
│  │  REST API Layer│  │  Background Jobs │                        │
│  │  (FastAPI)     │  │  (Celery + Redis)│                        │
│  └────────────────┘  └──────────────────┘                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │  REST / JSON
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│             React / TypeScript Frontend (Vite)                   │
│  Dashboard · Incidents · Logs · Metrics · AI Analysis · Reports  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Target Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Recharts / Visx, React Query |
| UI System | Custom design system (Radix UI primitives + CSS variables) |
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Primary DB | PostgreSQL 15 |
| Cache / Queue | Redis 7 |
| Background Jobs | Celery 5 |
| AI / LLM | `LLMProvider` abstraction: GeminiProvider, OpenAICompatibleProvider, MockProvider |
| AI Output | Pydantic-validated structured JSON; evidence-grounded `RCAOutput` schema |
| RCA Modes | <ul><li>`RCA_BASELINE` — deterministic rule-based baseline</li><li>`RCA_AI` — controlled single-call evidence-grounded LLM RCA</li><li>`RCA_AI_NO_EVIDENCE` — evidence-grounding ablation</li><li>`RCA_AI_NO_GRAPH` — dependency-graph-context ablation</li><li>`RCA_AGENT` — experimental bounded tool-calling RCA variant (NOT a replacement for `RCA_AI`)</li></ul> |
| Observability | OpenTelemetry, Prometheus, structured JSON logs |
| Containerisation | Docker, Docker Compose |
| Testing | Pytest, HTTPX, Vitest, Playwright (E2E) |
| Docs | Markdown, draw.io / Mermaid diagrams |

---

## Repository Structure (Planned)

```
reliai/
├── frontend/           # React/TypeScript/Vite SRE dashboard
├── backend/            # FastAPI modular monolith
├── demo-services/      # Controlled microservice environment
├── observability/      # Prometheus config, OTel collector config
├── experiments/        # Evaluation framework & failure scripts
├── tests/              # Integration & E2E tests
├── docker/             # Dockerfiles & compose files
├── docs/               # Architecture, research, API docs
│   ├── architecture/
│   └── research/
└── README.md
```

---

## Development Phases

| Phase | Title | Status |
|---|---|---|
| 0 | Architecture & Blueprint | ✅ Complete |
| 1 | Repository & Dev Infrastructure | ✅ Complete |
| 2 | Backend Foundation + PostgreSQL | ⬜ Planned |
| 3 | Demo Microservices | ⬜ Planned |
| 4 | Observability Pipeline | ⬜ Planned |
| 5 | Incident Detection Engine | ⬜ Planned |
| 6 | Incident Management API | ⬜ Planned |
| 7 | AI RCA Pipeline (All Modes) | ⬜ Planned |
| 8 | React Dashboard | ⬜ Planned |
| 9 | Topology Visualization & Graph Analytics | ⬜ Planned |
| 10 | Failure Injection + Evaluation (280 evaluations) | ⬜ Planned |
| 11 | Testing Suite | ⬜ Planned |
| 12 | Docker / Deployment | ⬜ Planned |
| 13 | Documentation & Demo Polish | ⬜ Planned |

---

## Getting Started (Post-Implementation)

```bash
# Clone and start entire platform
git clone <repo>
cd reliai
docker compose up
```

## Local Development (Phase 1)

1. **Environment Setup**
   ```bash
   cp .env.example .env
   ```

2. **Run with Docker Compose**
   ```bash
   make up
   ```
   This will start PostgreSQL, Redis, Backend (port 8001), and Frontend (port 5173).

3. **Run Locally without Docker**
   - **Backend**: 
     ```bash
     cd backend
     pip install -e .[dev]
     make dev-backend  # or uvicorn app.main:app --reload
     ```
   - **Frontend**:
     ```bash
     cd frontend
     npm install
     make dev-frontend # or npm run dev
     ```


Frontend will be available at `http://localhost:5173`
Backend API at `http://localhost:8001`

*(Note: Prometheus and OpenTelemetry are not part of the current Phase 1 stack and will be introduced in the later Observability phase.)*

---

## Academic Context

This project is submitted as a B.Tech CSE Major Project.

- **Institution:** JECRC UNIVERSITY
- **Academic Year:** 2026-2027
- **Team:** AYUSH SINGH
- **Supervisor:** MRS. SHIPRA KHANDELWAL

---

*See `docs/architecture/` for full system architecture, API design, and database schema.*
*See `docs/research/` for the evaluation plan and experimental methodology.*
