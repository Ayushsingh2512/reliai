# ReliAI — Evaluation Plan

> Research & Experimental Methodology
> B.Tech CSE Major Project — Research Component
> Version: 0.2 — Updated per architecture review

---

## 1. Research Questions

**RQ1:** Does a hybrid signal-correlation approach detect incidents with lower latency and
fewer false alerts than traditional threshold-only detection, for the same set of controlled
failure scenarios?

**RQ2:** Does evidence-grounded LLM-assisted RCA (`RCA_AI`) produce more accurate root
cause diagnoses than a deterministic rule-based RCA baseline (`RCA_BASELINE`) when both
operate on the same `EvidencePackage`?

**RQ3:** What is the practical latency overhead of AI-assisted RCA compared to the
deterministic rule-based baseline, and is it operationally acceptable for a local
demo-scale deployment?

> **Scope note:** These three questions are achievable for a 3-person B.Tech CSE team within
> a single semester. No additional research questions are added. Depth on these three is
> preferable to breadth across many.

---

## 2. Experimental Setup

### 2.1 Controlled Environment

All experiments run against the ReliAI demo environment:
- api-gateway, user-service, order-service, PostgreSQL, Redis
- Deployed via Docker Compose on a single machine (no real production traffic)
- All services instrumented with OpenTelemetry, Prometheus metrics, structured logging
- Detection interval configurable via `DETECTION_INTERVAL` environment variable (default: 10s)
- All timing configuration is environment-variable-driven; no hard-coded intervals

### 2.2 Failure Scenarios (Ground Truth Dataset)

Eight deterministic failure scenarios are implemented in `experiments/scenarios/`.
Each scenario has a precisely known ground truth injection point.

| ID | Scenario | Injected At | Ground Truth Root Cause | Expected Affected Services |
|---|---|---|---|---|
| S1 | HTTP 500 spike | order-service | Forced 5xx error rate | order-service, api-gateway |
| S2 | High request latency | order-service | Injected processing delay | order-service, api-gateway |
| S3 | DB connection exhaustion | order-service | DB pool saturation | order-service |
| S4 | DB query latency | PostgreSQL | Slow query injection | user-service, order-service |
| S5 | Redis failure | Redis container | Cache dependency unavailable | order-service |
| S6 | User service unavailable | user-service | Service down | user-service, api-gateway, order-service |
| S7 | Cascading failure | user-service → order-service | Upstream failure propagation | all |
| S8 | Memory pressure | order-service | Resource exhaustion | order-service |

Each scenario is repeated **5 times per condition** (detection mode, RCA mode) to account
for timing variability.

### 2.3 Independent Variables (Experimental Conditions)

This evaluation crosses two independent variables:

**Variable 1 — Detection Mode** (for RQ1):
| Value | Description |
|---|---|
| `THRESHOLD_ONLY` | Each metric evaluated independently against static thresholds |
| `HYBRID_CORRELATION` | Threshold violations + Z-score anomaly + service dependency correlation |

**Variable 2 — RCA Mode** (for RQ2 and RQ3):
| Value | Description |
|---|---|
| `RCA_BASELINE` | Deterministic rule-based RCA using the same `EvidencePackage` — no LLM |
| `RCA_AI` | LLM-assisted RCA using the same `EvidencePackage` |

> **Critical design principle:** Both RCA modes receive **identical `EvidencePackage` inputs**.
> The comparison is purely on reasoning quality, not on evidence access.
> This ensures RQ2 is a fair test of reasoning capability, not evidence availability.

---

## 3. RCA Mode Specifications

### 3.1 RCA_BASELINE — Deterministic Rule-Based RCA

`RCA_BASELINE` is implemented in `core/ai_pipeline/rule_rca.py`. It must be a genuine,
non-trivial baseline — not an artificially weak straw man.

**Input:** `EvidencePackage` (identical to what `RCA_AI` receives)

**Algorithm:**

```
RuleBasedRCA.analyse(evidence: EvidencePackage) → RCAOutput

1. Extract primary signals from evidence:
   - Identify metric violations: error rate spike, latency spike, connection exhaustion,
     memory pressure (from metric_snapshots)
   - Identify error patterns in log entries: HTTP 5xx frequency, exception type,
     DB error messages, Redis connection errors
   - Identify service availability from health check signals
   - Read service dependency subgraph from evidence

2. Apply decision rules in priority order:

   Rule R1 (Service Down):
     IF health_check for service X is FAILING:
       → root_cause = "Service X is unavailable"
       → failure_type = SERVICE_UNAVAILABLE
       → affected_component = X
       → confidence = 0.90

   Rule R2 (Upstream Dependency Failure):
     IF service X is degraded AND dependency Y is FAILING:
       → root_cause = "Service X is degrading due to upstream dependency Y failure"
       → failure_type = DEPENDENCY_FAILURE
       → affected_component = Y
       → confidence = 0.85

   Rule R3 (DB Connection Exhaustion):
     IF db_connection_pool_available <= 2 AND error_rate > threshold:
       → root_cause = "Database connection pool exhausted on service X"
       → failure_type = RESOURCE_EXHAUSTION
       → affected_component = "postgresql"
       → confidence = 0.88

   Rule R4 (DB Query Latency):
     IF db_query_duration_seconds P99 > 1.0s AND latency spike present:
       → root_cause = "Database query latency causing service degradation"
       → failure_type = RESOURCE_EXHAUSTION
       → affected_component = "postgresql"
       → confidence = 0.82

   Rule R5 (Cache Failure):
     IF redis_operations error_rate spike AND service uses Redis:
       → root_cause = "Redis cache unavailable causing service errors"
       → failure_type = DEPENDENCY_FAILURE
       → affected_component = "redis"
       → confidence = 0.85

   Rule R6 (Memory Pressure):
     IF process_resident_memory_bytes > RSS_THRESHOLD:
       → root_cause = "Memory pressure on service X causing degradation"
       → failure_type = RESOURCE_EXHAUSTION
       → affected_component = X
       → confidence = 0.80

   Rule R7 (HTTP 5xx Spike, No Infrastructure Signal):
     IF error_rate spike AND no infrastructure anomaly:
       → root_cause = "Application-level error rate spike on service X"
       → failure_type = CODE_ERROR
       → affected_component = X
       → confidence = 0.70

   Rule R8 (Cascading — Multiple Services):
     IF multiple services degraded AND dependency chain present:
       → root_cause = "Cascading failure originating from most upstream degraded service"
       → failure_type = CASCADING
       → affected_component = most_upstream_failed_service
       → confidence = 0.75

   Rule R9 (Fallback — Unknown):
     IF no rule matches:
       → root_cause = "Insufficient evidence to determine root cause"
       → failure_type = UNKNOWN
       → confidence = 0.30

3. Populate RCAOutput with:
   - root_cause (from matched rule)
   - evidence_used (references to specific metrics/logs from EvidencePackage that triggered the rule)
   - alternative_hypotheses (rules that scored second-highest)
   - suggested_investigation (static per-rule investigation steps)
   - remediation_recommendations (rule-derived, static per failure_type)
   - analysis_metadata.is_mock = false, rca_mode = "RULE_BASED"
```

**Properties of this baseline:**
- Deterministic: same input always produces same output
- Evidence-grounded: every conclusion references a specific signal in the EvidencePackage
- Non-trivial: handles all 8 failure scenarios with distinct reasoning paths
- Transparent: the matched rule is recorded in `analysis_metadata`
- Comparable: produces the same `RCAOutput` schema as `RCA_AI`

### 3.2 RCA_AI — LLM-Assisted RCA

`RCA_AI` is implemented in `core/ai_pipeline/pipeline.py`.

**Input:** Same `EvidencePackage` as `RCA_BASELINE`

**Algorithm:** See Section 3.3 of `system-architecture.md` for full pipeline detail.

Key properties for fair comparison:
- Receives identical evidence to `RCA_BASELINE`
- Output validated to same `RCAOutput` schema
- `analysis_metadata.rca_mode = "LLM_ASSISTED"`
- LLM temperature fixed at 0 for reproducibility
- Model version recorded in `model_used` field

### 3.3 Shared RCAOutput Schema

Both modes produce this schema (defined in `schemas/analysis.py`):

```jsonc
{
  "root_cause": {
    "summary": "string",
    "affected_component": "string",
    "failure_type": "SERVICE_UNAVAILABLE | DEPENDENCY_FAILURE | RESOURCE_EXHAUSTION | CODE_ERROR | CASCADING | UNKNOWN",
    "confidence": "float 0.0–1.0",
    "is_inference": "bool"
  },
  "evidence_used": [
    { "type": "METRIC|LOG|TRACE|DEPENDENCY", "source": "string", "description": "string", "supports_hypothesis": "bool" }
  ],
  "alternative_hypotheses": [
    { "summary": "string", "confidence": "float", "reason_rejected": "string" }
  ],
  "suggested_investigation": ["string"],
  "remediation_recommendations": [
    { "action": "string", "reason": "string", "expected_impact": "string", "risk": "LOW|MEDIUM|HIGH", "requires_human_approval": true }
  ],
  "analysis_metadata": {
    "rca_mode": "RULE_BASED | LLM_ASSISTED",
    "model_used": "string | null",
    "evidence_count": "int",
    "analysis_duration_ms": "int",
    "is_mock": "bool",
    "matched_rule": "string | null"
  }
}
```

---

## 4. Evaluation Metrics — Precise Definitions

Let the following notation be used throughout:

- **N** = total number of experiment runs
- **TP** = True Positive: a real injected failure that the system correctly detected as an incident
- **FP** = False Positive: an incident created by the system when no failure was injected
- **FN** = False Negative (Miss): a real injected failure that was not detected within the observation window (10 min)
- **TN** = True Negative: no incident created during a clean (no injection) period

### 4.1 Incident Detection Metrics (RQ1)

#### Detection Rate (DR)
Also known as Recall or Sensitivity.

```
DR = TP / (TP + FN)
```
*Proportion of injected failures that were correctly detected. Range: [0, 1].*

#### Miss Rate (MR)
Complement of Detection Rate.

```
MR = FN / (TP + FN) = 1 - DR
```
*Proportion of injected failures that were not detected within the observation window.*

#### False Alert Rate (FAR)
The proportion of all alerts raised that were false alarms.

```
FAR = FP / (FP + TP)
```
*Not the same as False Positive Rate (FPR). FAR answers: "Of all alerts raised, how many were wrong?"
This is the operationally relevant metric for alert fatigue.*

> **Note:** Classical False Positive Rate (FPR = FP / (FP + TN)) requires a well-defined
> TN population, which is difficult to bound in a monitoring system. We use FAR instead,
> which is directly measurable from experiment records.

#### Detection Latency (DL)
Measured per successful detection (TP only).

```
DL_i = incident_detected_at_i − failure_injected_at_i   [milliseconds]
```

Reported as: median DL, P75 DL, P95 DL, and range across all runs per scenario × mode.

#### Alert Consolidation Ratio (ACR)
Measures whether the system groups related signals into single incidents vs. creating many.

```
ACR = total_incident_records_created / total_injected_failures
```
*Ideal: ACR = 1.0. ACR > 1.0 means some failures created multiple incidents (noisy).
Only applicable to HYBRID_CORRELATION mode, which should consolidate signals.*

### 4.2 RCA Accuracy Metrics (RQ2)

All RCA accuracy metrics are applied per-run. Ground truth for each scenario is defined
in Section 2.2.

#### Root Cause Identification Rate (RCIR)
Primary RQ2 metric.

```
RCIR = (runs where failure_type matches ground truth AND affected_component matches ground truth) / N_analysed
```
Scored binary per run: correct = 1, incorrect = 0. Reported as percentage.

#### Affected Component Accuracy (ACA)
```
ACA = (runs where affected_component matches ground truth) / N_analysed
```

#### Confidence Calibration (CC)
Measures whether self-reported confidence correlates with actual correctness.
Computed using Brier Score:

```
BS = (1/N) * Σ (confidence_i − outcome_i)²
```
where `outcome_i = 1` if RCIR correct, `0` otherwise.
*Lower Brier Score = better calibrated confidence. Range: [0, 1].*

#### Evidence Relevance Rate (ERR)
Human-graded. For each run, reviewer rates each `evidence_used` item as relevant (1) or irrelevant (0).

```
ERR = relevant_evidence_items / total_evidence_items_cited
```

### 4.3 Performance Metrics (RQ3)

#### RCA Latency (RL)
```
RL_i = rca_completed_at_i − rca_started_at_i   [milliseconds]
```
Reported per mode: median, P95, max.

#### End-to-End Time to Diagnosis (E2E-TTD)
```
E2E-TTD_i = rca_completed_at_i − failure_injected_at_i   [milliseconds]
```

### 4.4 Remediation Quality (Qualitative)

Scored on a 3-point rubric (1=Poor, 2=Acceptable, 3=Good) for:
- Actionability of recommended action
- Accuracy of expected impact description
- Appropriateness of risk level

Scored independently by two reviewers; mean score reported. Inter-rater agreement
(Cohen's Kappa) reported to quantify scoring consistency.

---

## 5. Experiment Protocol

### 5.1 Paired Run Design

Experiments use a **paired design**: each scenario is evaluated under both conditions
back-to-back with a full environment reset between runs. This minimises confounding from
environment state drift.

```
For each scenario S in {S1..S8}:
  For each repetition r in {1..5}:
    Randomise mode_order = shuffle([THRESHOLD_ONLY, HYBRID_CORRELATION])
    For each detection_mode in mode_order:
      [FULL ENVIRONMENT RESET]
      Run experiment(S, detection_mode)
      [Collect results]
      [Wait for environment to stabilise]
      
      Randomise rca_mode_order = shuffle([RCA_BASELINE, RCA_AI])
      For each rca_mode in rca_mode_order:
        Trigger RCA on detected incident using rca_mode
        [Collect results]
```

This yields: **8 scenarios × 5 reps × 2 detection modes × 2 RCA modes = 160 analysis points**
(80 detection evaluations + 80 RCA evaluations).

> **Practical note:** For a 3-person team, 80 detection runs and 80 RCA evaluations
> is achievable. RCA_BASELINE is fast (< 1s); RCA_AI adds latency but can run overnight.
> Human grading of 80 RCA outputs is feasible in 2–3 hours with the rubric.

### 5.2 Environment Reset Protocol

**Purpose:** Prevent contamination between runs. A run may leave: open database connections,
Redis state, log buffer entries, uncommitted transactions, Celery tasks in queue.

**Reset steps (automated, executed by `experiments/runner.py`):**

```
1. Stop failure injection (if still active)
2. Restart all demo service containers (docker-compose restart api-gateway user-service order-service)
3. Flush Redis (FLUSHDB on the log buffer database)
4. DELETE FROM incidents WHERE experiment_run_id = <previous_run_id>  [mark stale]
5. Wait 30 seconds for services to become healthy (poll /health endpoints)
6. Verify Prometheus shows all targets UP
7. Verify no open incidents in ReliAI (GET /api/v1/incidents?status=OPEN returns empty)
8. Record reset_completed_at timestamp
9. Proceed to next run
```

**Contamination prevention:**
- Steps 2–3 guarantee no in-memory or cache state from previous run
- Step 4 ensures previous incident does not influence next detection run
- Step 5 guarantees metric baseline is stable before injection
- Steps 6–7 provide a programmatic readiness check, not a manual one
- The 30-second wait is configurable via `EXPERIMENT_RESET_WAIT_SECONDS`

### 5.3 Per-Run Procedure

```
[Pre-run state: clean environment after reset]

1. Create ExperimentRun record:
   POST /api/v1/experiments/{id}/runs
   { scenario: "S1", detection_mode: "THRESHOLD_ONLY", rca_mode: "RCA_BASELINE" }
   → Returns run_id

2. Collect baseline (steady-state) metrics for BASELINE_WINDOW seconds (configurable, default 60s)
   → Snapshot stored as run baseline in experiment_runs.baseline_snapshot

3. Record failure_injected_at = now()

4. Trigger failure injection:
   POST /api/v1/experiments/{id}/runs/{run_id}/inject
   → Executes scenario script atomically
   → failure_injected_at recorded in DB

5. Poll for incident creation (poll interval = DETECTION_INTERVAL, max wait = OBSERVATION_WINDOW = 10 min)
   → On incident detected: record incident_detected_at, detection_latency_ms

6. If no incident within OBSERVATION_WINDOW:
   → Record as FN (missed detection); set false_negative = true

7. Stop failure injection:
   POST /api/v1/experiments/{id}/runs/{run_id}/stop

8. If incident was detected (TP), trigger RCA:
   POST /api/v1/analysis/{incident_id}/trigger?rca_mode={rca_mode}
   → Record rca_started_at, rca_completed_at, ai_diagnosis_latency_ms

9. Mark run complete:
   POST /api/v1/experiments/{id}/runs/{run_id}/complete

10. Human grader reviews RCA output:
    POST /api/v1/experiments/{id}/runs/{run_id}/grade
    {
      "rca_correct": true/false,      // RCIR
      "affected_component_correct": true/false,   // ACA
      "false_positive": false,
      "evidence_relevance_scores": [1, 1, 0, 1],  // per evidence item
      "remediation_scores": { "actionability": 3, "impact": 2, "risk": 3 },
      "notes": "..."
    }

11. Run environment reset (Section 5.2)
```

### 5.4 Randomisation

- Detection mode order is randomised per (scenario, repetition) pair using a pre-generated
  random seed recorded in the experiment definition — this makes experiments reproducible.
- RCA mode order is independently randomised.
- Scenario order within each repetition block is randomised.
- The random seed is stored in `experiments.random_seed` for auditability.

### 5.5 Observer Bias Control

- The human grader for RCA correctness scores from the rubric only — does not know which
  RCA mode produced the output during grading (outputs are identified by run_id, not mode label)
- After grading all runs, the mode label is revealed for analysis

---

## 6. Baseline Comparison Design

### 6.1 Threshold Configuration (THRESHOLD_ONLY)

| Metric | Condition | Severity |
|---|---|---|
| `http_requests_total` error rate | > 5% over 2 scrape intervals | HIGH |
| `http_request_duration_seconds` P99 | > 2000ms over 2 scrape intervals | HIGH |
| `http_request_duration_seconds` P99 | > 500ms over 2 scrape intervals | MEDIUM |
| `db_connection_pool_available` | ≤ 2 | HIGH |
| Service HTTP `/health` | Non-200 response | CRITICAL |
| `process_resident_memory_bytes` | > 500 MB | MEDIUM |

Each rule evaluated independently. Any single violation creates an incident immediately.
A single scenario may create multiple independent incidents (no deduplication in baseline mode).

### 6.2 Hybrid Configuration (HYBRID_CORRELATION)

In addition to threshold evaluation:
- **Anomaly detection:** Z-score on rolling window of last 10 metric snapshots (threshold: |z| > 3.0)
- **Correlation window:** configurable `CORRELATION_WINDOW_SECONDS` (default: 90s)
- **Correlation score:**

```
correlation_score = (
    0.4 × max_severity_weight(violations)    +
    0.3 × (|correlated_services| / |total_known_services|)  +
    0.2 × min(anomaly_count / 3.0, 1.0)     +
    0.1 × dependency_criticality_weight
)

severity_weight: CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5, LOW=0.25
```

- Incident created only when `correlation_score > CORRELATION_THRESHOLD` (default: 0.5, configurable)
- Deduplication: no new incident created if open incident covers the same service cluster within `DEDUP_WINDOW_SECONDS` (default: 300s)

---

## 7. Data Collection & Storage

All experiment data is stored in PostgreSQL `experiment_runs` table.
All timing fields stored as TIMESTAMPTZ for precision.

### 7.1 Export Format

```
GET /api/v1/experiments/{id}/results/export
→ CSV with columns:
run_id, scenario, repetition, detection_mode, rca_mode,
failure_injected_at, incident_detected_at, detection_latency_ms,
false_negative, false_positive,
rca_started_at, rca_completed_at, rca_latency_ms,
e2e_time_to_diagnosis_ms,
rca_correct, affected_component_correct,
llm_confidence, adjusted_confidence, brier_score_term,
evidence_relevance_rate, remediation_actionability, remediation_impact, remediation_risk,
rca_mode_used, model_used, matched_rule,
notes
```

Analysis performed in `experiments/analysis/results_analysis.py` using pandas and matplotlib.

---

## 8. Threats to Validity

| Threat | Category | Mitigation |
|---|---|---|
| Small N per cell (5 reps) | Statistical power | Acknowledge limitation; report confidence intervals; use non-parametric tests (Wilcoxon) |
| Single-machine deployment | External validity | Clearly scope as controlled local experiment; frame as proof-of-concept |
| Human grading subjectivity (RQ2) | Internal validity | Standardised rubric; blind grading (mode hidden during scoring); inter-rater agreement |
| LLM non-determinism | Reliability | Fix temperature=0; record model version and configuration |
| Scenario implementation bugs | Internal validity | Code review by second team member; supervisor review of scenario scripts |
| Environment drift between runs | Internal validity | Automated full reset protocol (Section 5.2); programmatic health verification |
| RCA_BASELINE rule coverage gaps | Construct validity | Rule set covers all 8 scenarios explicitly; R9 fallback handles unseen patterns |

---

## 9. Expected Results Structure (Dissertation Chapter 5)

1. **Table 5.1:** Detection metrics per scenario × detection mode: DR, FAR, median DL, P95 DL
2. **Figure 5.1:** Box plot — detection latency, THRESHOLD_ONLY vs HYBRID_CORRELATION
3. **Table 5.2:** Alert Consolidation Ratio per mode
4. **Table 5.3:** RCA accuracy metrics per scenario × RCA mode: RCIR, ACA, ERR
5. **Figure 5.2:** Scatter plot — confidence vs correctness for both RCA modes
6. **Table 5.4:** RCA latency statistics: median, P95 per mode
7. **Table 5.5:** Remediation quality rubric scores, inter-rater kappa
8. **Figure 5.3:** Brier score comparison (calibration): RCA_BASELINE vs RCA_AI
9. **Discussion 5.x:** Cases where RCA_BASELINE outperformed RCA_AI (and why)
10. **Discussion 5.x:** Cases where RCA_AI outperformed RCA_BASELINE (and why)
11. **Discussion 5.x:** Statistical tests (Wilcoxon signed-rank on detection latency; McNemar's test on RCIR)

---

## 10. Literature Review Anchors

1. **AIOps survey:** Lim et al., "AI-Driven IT Operations," IEEE Software, 2021
2. **LLM for RCA:** Chen et al., "Automatic Root Cause Analysis via Large Language Models for Cloud Incidents," EuroSys 2024
3. **Anomaly detection in microservices:** Wu et al., "Microservice Incident Prediction," ASE 2021
4. **Signal correlation:** Nair et al., "Chronicle: Linked Archive for Postmortem Analysis," SREcon 2019
5. **Chaos engineering:** Basiri et al., "Chaos Engineering," IEEE Software 2016
6. **SRE practices:** Beyer et al., "Site Reliability Engineering," O'Reilly 2016
7. **Brier score:** Brier, G.W., "Verification of Forecasts Expressed in Terms of Probability," Monthly Weather Review, 1950
8. **Evaluation methodology:** Hossin & Sulaiman, "A Review on Evaluation Metrics for Data Classification," IJDMS, 2015

*Full citations to be completed in dissertation Chapter 2.*

---

## 11. Ethical Considerations

- No real user data is used; all data is synthetic (generated by demo services).
- The LLM API is used only for analysis of synthetic incident data.
- No personally identifiable information is processed.
- API keys stored as environment variables; never committed to repository.
- Experiment results are reproducible: random seeds are recorded.
