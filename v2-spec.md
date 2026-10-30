# App-inmo-framework-v2

> **Status:** Proposed / Implementation-ready specification  
> **Version:** 1.0-draft  
> **Date:** 2026-10-30  
> **Owner:** Deployment / MLOps Platform Team  
> **Target platform:** GitHub + Google Cloud Platform (GCP)  
> **Initial topology:** Monorepo with embedded model folders; designed for later multi-repository adoption

## 1. Executive Summary

Repo is a centralized **self-service MLOps validation and deployment framework** for multiple Data Science (DS) model repositories (Repo A). DS teams own feature engineering, model logic, model-specific test cases, and a declarative `manifest.yaml`. The Platform/Deployment Team owns the standardized contracts, independently enforced test gates, isolated cloud execution, artifact promotion, release orchestration, observability, and security controls.

**Primary objective:** DS teams can independently develop, test, and submit model changes; once the prescribed technical checks, model validations, and risk-based approvals are satisfied, a trusted pipeline can promote the **same immutable artifact** to Production without routine manual deployment work by the Platform Team.

**MVP design:** Models live under `models/<model_id>/` in Repo B's Git repository for fast co-development and debugging. Every model is treated as an external, replaceable component accessed only through a stable interface and path/manifest. Later, move `models/<model_id>` to independent Repo A repositories without rewriting validators, model contracts, or deployment logic.

### 1.1 Goals

- Standardize how models and feature code are submitted, executed, tested, packaged, released, monitored, and rolled back.
- Provide a consistent DS developer experience: **local quick tests → optional on-demand cloud validation → PR validation → approved release**.
- Support multiple heterogeneous models with **one shared Repo B**, versioned adapters/profiles, and model-specific manifests.
- Separate DS-supplied tests from **Platform-owned, non-bypassable validation gates**.
- Produce auditable, reproducible release evidence tied to code commit, policy version, test data version, environment, and artifact digest.
- Enforce least privilege, data protection, model governance, and risk-based approvals suitable for a regulated organization.
- Minimize manual handoffs and per-model CI/CD customization.

### 1.2 Non-goals (initial release)

- A full custom web portal, feature store, model-training system, or experiment tracker.
- Automatically certifying a model's business suitability or regulatory compliance solely from green unit tests.
- Giving DS production deploy, secret access, or production database permissions.
- Building support for arbitrary languages or execution modes in the first MVP.
- Treating `manifest.yaml` as an authorization source.

## 2. Personas, Ownership, and Trust Boundaries

| Role | Owns | Cannot unilaterally do |
|---|---|---|
| Data Scientist (DS) | `src/` model/feature code; model-owned tests; model documentation; requested manifest settings; performance evidence | Change central platform gates/policies; access prod secrets; deploy to prod |
| Model Owner | Intended use, metrics, baseline criteria, business acceptance, risk classification inputs | Override hard security controls |
| Platform / Deployment Team | Repo B framework/SDK; runners; global policies; CI/CD; artifacts; platform runtime; alerting; rollback | Substitute for independent model validation when required |
| Security / Risk / Model Validation | Security policies; independent model validation and approvals for in-scope changes | Silently modify submitted DS code |
| Trusted Release Controller | Verify attestations, approvals and artifact identity; authorize target-environment promotion | Accept PR-controlled release decisions without policy checks |

**Trust boundary:** Any DS-authored Python and dependency is untrusted executable code at validation time, including imports, tests, setup/build scripts, and manifest-referenced hooks. Paths and repository separation alone are **not** sandboxes.

## 3. Target Architecture

```text
DS workstation / approved cloud workstation
    │  edit + local pytest + optional `mlplatform validate --local`
    ▼
Repo A source (MVP: models/<id>/ in monorepo; future: separate Git repos)
    │  PR / commit
    ▼
GitHub CI orchestration (read-only, minimal permissions)
    │
    ├── static checks (manifest/schema, source scanning, dependencies)
    └── isolated Cloud Test Runner (GCP non-production project)
         ├── model-owned unit tests
         ├── platform-owned contract/golden/negative/regression tests
         ├── integration / model metrics / runtime tests as applicable
         └── immutable validation evidence
    ▼
Artifact build → registry (pinned image digest + provenance)
    ▼
Staging / pre-production tests (same artifact)
    ▼
Trusted release gate (policy + required approvals + signed evidence)
    ▼
Progressive Production rollout (canary if supported) + monitoring
    └── rollback / halt on failure
```

**Principles:** Shared **platform code**, not shared model execution identity. Each model/environment has isolated artifact, deployment resources, IAM identities, configuration, runtime logs, and release history as needed.

## 4. Repository Layout (MVP Monorepo)

```text
App-inmo-platform/                         # repository (MVP)
├── src/mlops_platform/
│   ├── cli.py                          # `mlplatform` entry point
│   ├── manifest/                       # parse/schema/semantic validation
│   ├── contracts/                      # versioned model APIs and schemas
│   ├── validation/                     # test orchestration + result aggregation
│   ├── runners/                        # local runner, cloud runner adapters
│   ├── policies/                       # policy evaluation engine
│   ├── evidence/                       # report/attestation creation and verification
│   ├── artifacts/                      # build, SBOM, digest resolution
│   ├── deployments/                    # staging/prod adapters and rollout
│   └── observability/                  # metrics/logging/alert integrations
├── policies/
│   ├── global.yaml                     # protected, minimum mandatory gates
│   ├── profiles/{standard,high_risk}.yaml
│   └── model_registry.yaml             # protected model-to-risk/owner mappings
├── contracts/v1/                       # standardized interfaces
├── tests/platform/                     # B's own tests
├── test_assets/                        # platform-owned golden/negative cases
├── models/                              # temporary Repo A folders ONLY
│   ├── thematic-impact/
│   │   ├── manifest.yaml
│   │   ├── pyproject.toml
│   │   ├── src/thematic-impactl/{features,model,runner,schemas}.py
│   │   └── tests/{test_features,test_model,golden_cases}.py_or_json
│   └── ach-forecast/...
├── gcp/                                 # infra/examples, env configs (no secrets)
├── .github/workflows/
│   ├── pr-validation.yml
│   ├── reusable-validation.yml          # used by future Repo A repos
│   └── release.yml                     # trusted gated workflow
├── docs/{developer-guide,operator-guide,security,runbooks}.md
├── pyproject.toml
└── spec.md
```

Do **not** name a top-level Python package `platform` (stdlib conflict). Keep model project packaging/dependencies separate from Repo B; do not load all models in a single shared interpreter by default.

### 4.1 Multi-Repo Migration

- Future `thematic-impact` / `model-fraud-detection` repos retain identical internal `manifest.yaml`, `src/`, `tests/` layouts.
- Platform CLI accepts a **model source path + immutable commit reference** rather than hard-coded `models/<id>` paths.
- GitHub reusable workflows may call a **pinned** Repo B workflow (`@<commit-sha>` or protected immutable release), but enforcement of critical gates belongs in separately controlled jobs/runners; a caller cannot disable them through PR changes.
- Support gradual platform versions per model while enforcing a central minimum supported/security-patched version.

## 5. Model Contract (Repo A ↔ Repo B)

### 5.1 Core Execution API (v1)

Each model package implements a versioned adapter matching an approved contract, conceptually:

```python
# conceptual API; actual schema types are versioned by Repo B
from typing import Mapping, Any

def transform_features(validated_input: Mapping[str, Any]) -> Mapping[str, Any]:
    """Deterministic per-record feature calculation (where applicable)."""
    ...

def predict(features: Mapping[str, Any], model_context: Any) -> Mapping[str, Any]:
    """Return output matching the declared prediction schema."""
    ...
```

An adapter may bridge an existing `build_features(Applicant)` / `predict(features)` API (as in the earlier Repo A prototype) to the standard contract. This avoids forcing an immediate refactor. Contract v1 includes schema validation, explicit model version, error semantics, and serialization rules. Every incompatible change requires a new contract version and compatibility tests.

### 5.2 Manifest (`models/<model_id>/manifest.yaml`)

```yaml
schema_version: "1"
model:
  id: fraud-detection
  owner: fraud-ds-team
  version: "1.2.0"              # informational; build identity uses commit + digest
  contract: "v1"
  risk_classification_request: standard
runtime:
  type: online                 # enum: online | batch (batch added by adapter/profile)
  python: "3.11"
  entrypoint: "fraud_model.runner:run"
features:
  input_schema: "config/input_schema.json"
  output_schema: "config/feature_schema.json"
validation:
  profile_request: standard
  ds_golden_dataset: "tests/golden_cases.json"
  metrics:
    roc_auc:
      minimum_requested: 0.87
    recall:
      minimum_requested: 0.80
deployment:
  target_request: cloud_run
  rollout_request: canary
  production_requested: true
```

Manifest conventions:

1. All keys are defined in a **strict, versioned schema**; reject unknown keys and invalid types.
2. Strings such as `entrypoint`, file paths, runtime, and deployment target are **allowlisted/validated**. Resolve paths inside the model root; reject traversal, symlink escape, arbitrary shell commands, and external URLs unless explicitly policy-approved.
3. A manifest may **request** profile, risk class, thresholds, target, and rollout. Central protected policy/registry determines the *effective* values; DS cannot downgrade mandatory gates or authorize prod deployment.
4. Model-specific metrics and thresholds are approved by Model Owner/risk governance and stored or attested in protected policy; unapproved changes require review.
5. No credentials, PII, connection strings, or secret values in manifest.
6. Policy evaluation emits `requested`, `effective`, `source`, and explanation for every release-affecting setting.

## 6. DS Developer Experience

### 6.1 Normal Workflow

1. `mlplatform init --model <id>` generates an A template and version-compatible manifest.
2. DS develops in VS Code/Jupyter or approved cloud workstation; maintains `src/`, own tests, input/output schemas, and golden examples.
3. `mlplatform test --local --model models/<id>`: fast unit/contract tests with mock or synthetic data, no production connectivity.
4. `mlplatform test --cloud --model models/<id>` (optional before PR): submits immutable snapshot to controlled cloud validation, returns build URL/report; cannot deploy.
5. DS opens PR; required CI runs the authoritative **platform-controlled** gates against the exact proposed commit.
6. DS views PR checks: failed cases, actionable errors, schema diffs, regression metrics, and report location.
7. After required reviews/approvals, trusted pipeline builds/promotes verified immutable artifact through staging to production.

### 6.2 CLI Requirements

| Command | Scope | Output |
|---|---|---|
| `mlplatform init --model ID` | scaffold new model folder | files, template version |
| `mlplatform manifest validate --model PATH` | schema + policy dry-run | requested/effective values; errors |
| `mlplatform test --local --model PATH` | quick deterministic tests | terminal summary + JUnit |
| `mlplatform test --cloud --model PATH` | isolated remote validation | job ID + result link |
| `mlplatform validate --model PATH --report PATH` | authoritative validation runner (CI context) | JSON evidence + failure exit code |
| `mlplatform report --run RUN_ID` | test summary | metrics, failures, logs links |
| `mlplatform release-plan --artifact DIGEST --evidence ID` | read-only eligibility computation | allowed/blocked + missing approvals |

The first MVP **must implement** manifest validation, local testing, platform validation, machine-readable reports, and a dry-run release-plan. Remote cloud execution and real releases are later phases.

### 6.3 Local vs Cloud Tests

| Test | Local | Cloud CI | Staging |
|---|---|---|---|
| Syntax, lint, unit and fast contract tests | Yes | Yes | No |
| DS golden examples | Yes | Yes | Optional |
| Platform-owned golden/negative/schema tests | Fast subset | Full | Relevant subset |
| Security/dependency scans | Optional feedback | Required | Image verification |
| Approved-data integration / point-in-time correctness | No sensitive data | Required where applicable | Required as needed |
| Regression / model metrics | Small sample | Approved baseline | Full production-like |
| Service/API, load, egress, runtime permissions | Mock | Some | Required for online models |
| Deployment readiness, rollback rehearsal | No | Precheck | Required per risk class |

## 7. Validation and Quality Gates

Each gate must have: stable `gate_id`, owner, version, inputs, pass/fail criteria, runtime, evidence URI, severity, and bypass/waiver policy. A required gate failing or missing evidence blocks release.

### 7.1 Mandatory Platform-Owned Gates

- **G01 Contract:** declared entrypoints exist and execute; versioned input/output schema; correct error behavior.
- **G02 Code:** syntax, lint/type checks (policy-controlled), model-owned unit tests, platform smoke tests.
- **G03 Security:** secrets scanning, dependency/SBOM/license/vulnerability checks, prohibited imports/egress rules, container scan; execution isolation.
- **G04 Features:** nulls/NaNs/infinities, types, ranges, missing and edge cases; deterministic behavior where required; feature schema compatibility.
- **G05 Golden/Negative:** Platform-owned expectations independent from DS test assertions; invalid input and failure-path tests.
- **G06 Regression:** candidate vs approved baseline on the same versioned dataset; document intended prediction differences; thresholds are model/risk-specific.
- **G07 Data Integrity:** train/serve feature parity, time-window semantics, point-in-time correctness, leakage checks where relevant.
- **G08 Model Metrics:** approved model quality, calibration/fairness/segment metrics and drift baselines where applicable; independent validation evidence when required.
- **G09 Integration:** upstream/downstream API/feature store compatibility, credentials/permissions, schema and serialization compatibility.
- **G10 Runtime:** latency P50/P95/P99 as required, memory/CPU, concurrency/throughput, timeout and cost budgets.
- **G11 Release Readiness:** immutable artifact/digest, provenance, required approvals, monitoring/alerts, rollback plan.

**Caveat:** Statistical model validation cannot be reduced to deterministic unit tests. Green technical gates mean *technically eligible*, not *business-approved*.

### 7.2 Golden Dataset and Regression

- DS maintains example golden cases in A for rapid feedback.
- Platform/Governance maintains separate controlled golden/regression datasets, isolated from DS write access; versions and access are auditable.
- Compare features and predictions with type-appropriate tolerance; avoid exact float equality.
- Expected model changes require approved deltas/thresholds; do not demand identical predictions for intentional model upgrades.
- Reports include sample count, breakdown by segment where authorized, confidence intervals if applicable, and baseline identifiers.

### 7.3 Test Result State Machine

`QUEUED → RUNNING → PASSED | FAILED | ERROR | CANCELED`

A missing/timeout/errored mandatory gate is **not a pass**. Results are invalidated when source commit, model artifact, platform runner version, effective policy, or relevant test data versions change.

## 8. Isolation, Supply Chain, and Governance

### 8.1 Execution

- Run all untrusted DS code, dependency installation, import and tests in isolated short-lived containers/jobs, non-prod GCP project, per-run identity or tightly scoped service accounts.
- No production database, secrets, deploy permissions or privileged build credentials in test jobs.
- Prefer read-only test datasets (synthetic/masked/approved) with dataset-level access control and no unapproved export; restrict outbound network and metadata access.
- Apply CPU/memory/time/quotas, file system constraints, dependency allowlists/private package indexes where feasible.
- Secure cloud tests against PRs from untrusted sources: never expose secrets or privileged credentials to unreviewed code paths.

### 8.2 Source, Artifact and Evidence Integrity

- Verify exact commit SHA and protected platform/policy version before validation.
- Build once, use immutable container digest for staging and production; do not rebuild from moving branch tips.
- Generate SBOM and verifiable provenance/attestation; store validation evidence with tamper resistance and retention policy.
- Trusted Release Controller re-verifies source SHA, tested artifact digest, policy/version, approval records, and target environment before promotion.
- Plain JSON from a DS-controlled workspace is **not** sufficient production authorization.

### 8.3 Authorization and Audit

- GitHub CODEOWNERS/branch protections are useful review controls; independently enforced privileged gates must not depend on workflows modifiable by DS PRs.
- Distinct identities for validation, artifact build, staging deploy, and production deploy.
- Required approvers mapped to model risk; no self-approval where prohibited by policy; record exceptions with expiry and justification.
- Persist who proposed, reviewed, approved, tested, and deployed each version, when, and which exact artifacts/data/policies were used.

## 9. CI/CD and Release Policy

### 9.1 CI Flow

1. PR opened/updated → validate manifest syntax and allowed changes.
2. Execute model tests and independently controlled platform gates in isolated runner.
3. Publish PR check summary + detailed report; block merge on required failed checks.
4. On protected merge and successful required gates, create signed/versioned release candidate artifact with provenance.
5. Run staging integration/performance/security checks against **same digest**.
6. Evaluate risk-based release policy and collect required approvals.
7. Trusted deployment service performs canary/progressive production rollout, monitors, and automatically halts/rolls back based on approved thresholds where safe.

### 9.2 Risk-Based Release Matrix

| Class | Typical examples | Production gate |
|---|---|---|
| Low | Non-semantic refactor, allowlisted config changes, pre-approved low-risk model change | Automated after all mandatory checks and pre-authorized policy |
| Medium | New feature, meaningful output change, important model update | Automated execution **after** Model Owner/required approvals |
| High | Credit decisioning, fraud or regulated use, material data/model/decision change | Independent model validation + security/risk approvals, then controlled automated deployment |

Risk class determined by protected registry/organization policy, **not by DS-selected manifest value**. Human approval is a gate in the automated pipeline, not a manual shell deployment step.

### 9.3 GCP Reference Mapping

| Requirement | Candidate technology |
|---|---|
| Source/PR | GitHub; protected branches; reusable workflows |
| Cloud validation | Cloud Build and/or isolated Cloud Run Jobs; private pools as appropriate |
| Image/package registry | Artifact Registry |
| CI identity | Workload Identity Federation / dedicated short-lived identities where supported |
| Online runtime | Cloud Run or Vertex AI Endpoints (adapter-specific) |
| Batch runtime | Cloud Run Jobs, Vertex AI Pipelines, or approved scheduler |
| Promotion | Cloud Deploy for supported targets, or trusted controlled deploy orchestration |
| Secrets/security | IAM, Secret Manager, image scanning, Binary Authorization where supported |
| Logs/metrics/audit | Cloud Logging, Monitoring, Audit Logs; model-quality monitoring as appropriate |

Platform adapters, service identities, artifact permissions and infrastructure must be specified per environment; none of these integrations is assumed to exist in the MVP.

## 10. Observability and Rollback

- Standard structured logs: `model_id`, `model_version`, `artifact_digest`, `request_id`/job ID, feature schema version, latency and failure category; no raw sensitive feature values in logs by default.
- Technical metrics: availability, errors, latency, throughput, memory, queue depth, cost and service-level objectives.
- ML/data metrics: feature nulls/distribution, input drift, training-serving skew, output drift, quality/fairness metrics if ground truth exists and appropriately delayed.
- Canary compares candidate and baseline on authorized metrics; automatically halt/rollback upon critical technical guardrail breach.
- **Rollback limitations:** reverting a service image does not automatically revert feature-store, data, schema, or upstream state. Require compatibility and separate data migration/rollback playbooks.
- Alerts route to model owner for model quality, platform on-call for serving/infra issues, and security for violations.

## 11. Evidence Contract and Reporting

Minimal JSON report schema (illustrative):

```json
{
  "schema_version": "1",
  "run_id": "run-123",
  "model_id": "fraud-detection",
  "source_commit_sha": "<full commit SHA>",
  "platform_version": "1.4.0",
  "policy_digest": "sha256:...",
  "test_data_versions": ["golden-v3", "regression-2026-10"],
  "artifact_digest": "sha256:...",
  "environment": "isolated-ci",
  "gates": [
    {"gate_id": "G01", "status": "PASSED", "evidence_uri": "gs://..."},
    {"gate_id": "G06", "status": "PASSED", "evidence_uri": "gs://..."}
  ],
  "technical_validation": "PASSED",
  "production_release_authorized": false
}
```

`production_release_authorized` must be computed by the trusted release service after verifying approvals and attestations. A DS-written file must never grant itself that state. Reports should redact secrets/PII, have bounded retention, and link to detailed controlled-access logs.

## 12. API / CLI Behavior and Error Codes

- Exit `0`: requested command completed successfully / relevant tests passed.
- Exit `1`: validation failure / required gate failed.
- Exit `2`: invalid manifest, configuration, unsupported contract, or usage error.
- Exit `3`: infrastructure/runtime error (must not be counted as pass).
- Avoid global `sys.path` mutation in production runners to import arbitrary model trees; use isolated per-model package installation or explicit adapters.
- Structured JSON output for automation and human-readable concise terminal output for DS.
- Validation jobs are idempotent for a given source/policy/data version; retry infra failures without reclassifying them as test passes.

## 13. Implementation Phases and Deliverables

### Phase 1 — Monorepo Local MVP (must-have)

- [ ] Set up Repo B modules and **two** demo models (`thematic-impact`, `fraud_detection`).
- [ ] Versioned manifest JSON Schema / Pydantic model and semantic validator.
- [ ] Stable model contract v1 + compatibility adapter for prototype Repo A.
- [ ] CLI: `init`, `manifest validate`, `test --local`, `validate`, `report`, `release-plan` (dry run).
- [ ] Platform-owned contract, golden, negative, regression (small fixture) tests.
- [ ] Clear pass/fail evidence including source/policy identity when in Git.
- [ ] Unit/integration tests for Repo B itself; failure/timeout/unknown manifest tests.
- [ ] Docs: local quick start, how to add model, gate explanation, migration notes.
- [ ] No production credentials or deploy implementation enabled in MVP.

### Phase 2 — Cloud Validation & PR Developer Experience

- [ ] Short-lived isolated GCP test runner, approved test datasets, scoped identities/egress.
- [ ] PR trigger integration and non-bypassable platform-run required checks.
- [ ] `test --cloud` and `report --run`, actionable PR comments/check summaries.
- [ ] Expanded integration, regression, model metrics, resource/performance gates.
- [ ] Protected policy registry and formal ownership / review controls.
- [ ] Signed provenance and tamper-resistant audit evidence.

### Phase 3 — Controlled Staging / Production Releases

- [ ] Artifact Registry immutable builds, SBOM, vulnerability scans and attestations.
- [ ] Staging promotion by digest; deployment adapter for selected online/batch target.
- [ ] Approval workflow integration, independent trusted Release Controller.
- [ ] Progressive rollout, alerts, rollback and audited runbooks.
- [ ] Risk-tier policies tested with simulated approve/deny/change/rollback cases.

### Phase 4 — Multi-Repo Self-Service

- [ ] Extract model folders into independent Git repositories without changing model internals.
- [ ] Publish pinned `mlplatform` package and centrally controlled reusable workflow.
- [ ] Model catalog, onboarding, contract deprecation policy, cross-model reporting.
- [ ] Roll platform changes gradually by version with minimum-version enforcement.

## 14. Acceptance Criteria

### Phase 1 acceptance

1. A new model can be scaffolded under `models/` and validated without changing platform validation source code.
2. Both sample models can run independent local tests and common platform gates through the same CLI.
3. Changing feature output to violate a platform-owned expectation causes a nonzero CI result even if DS-owned tests are green.
4. A malformed/unknown-key manifest is rejected with actionable error and exit code `2`.
5. A changed risk setting in model manifest cannot weaken protected gate requirements.
6. Evidence identifies commit (if available), effective policy version, model ID, test suite, outcomes, and execution environment; no false production authorization.
7. A validation infrastructure failure is reported as `ERROR`, not `PASSED`.
8. No production credentials, production data access or production deploy permissions are needed to run all MVP examples.

### Phase 2 acceptance

1. A DS can submit a PR and receive validation results without managing platform infrastructure.
2. The authoritative cloud validation is isolated from production permissions and cannot be bypassed by editing model PR workflow files.
3. Each result is reproducibly linked to an exact source commit, runner/policy version, and approved test dataset version.
4. Platform reports contain useful failures and protect sensitive data.

### Phase 3 acceptance

1. Production cannot be deployed without valid verified evidence and required approvals.
2. The production deployment uses exactly the digest tested in staging, not a rebuilt image.
3. Canary failures block or revert traffic; deployment and rollback actions are auditable.
4. Release pathways for low-, medium-, and high-risk models satisfy their respective policies.

### Phase 4 acceptance

1. One model can be moved out of Monorepo into its own Git repo with no changes to core B validators/contracts.
2. Multiple A repos use the same pinned platform version while retaining separate manifests, test results, permissions, and deployment histories.

## 15. Operational KPIs

Track: PR-to-test feedback time; PR-to-production lead time; percent of releases without manual platform execution; test flakiness; change failure rate; rollback time; platform onboarding time; policy bypass/waiver rate; number of models per platform engineering FTE; cloud validation cost per run. Set numeric SLOs only after baseline measurements.

## 16. Risks and Decisions Needed

| Decision | Proposed default | Decision owner |
|---|---|---|
| Initial runtime | Python 3.11, one online model adapter first | Platform + DS |
| First deployment backend | Cloud Run for simple online inference; add batch later | Platform |
| Where DS develops | Local for synthetic data, managed workstations for restricted data | Security + DS |
| Test datasets | Synthetic local; controlled approved datasets in cloud | Data Owner / Security |
| Model risk classification | Protected central registry; manifest request only | Model Risk / Governance |
| CI workflow ownership | Platform-owned mandatory checks; caller PR cannot weaken | Platform + Security |
| Approval workflow | Existing change-management/model-validation system | Governance |
| Platform version distribution | Pinned package/workflow and minimum policy version | Platform |
| Shared runner tenant isolation | Per-job isolated workloads, per-model identities if needed | Security + Platform |

Key risks: untrusted code execution; train/serve skew; silent model regression; insufficient golden coverage; tests not representing actual data; policy bypass; unstable shared dependencies; unauthorized data egress; artifact/test mismatch; model monitoring blind spots; irreversible feature/data migrations. Treat each as a design and acceptance-test item, not documentation only.

## 17. Minimum Demonstration Scenario

1. Initialize `models/thematic-impact` and `models/ach-forecast` with distinct manifests and package names.
2. DS edits `thematic-impact` feature calculation and runs `mlplatform test --local --model models/thematic-impact`.
3. Platform validates the model using independent fixture; deliberately introduce bug to show gate fails even when DS's own test is weakened.
4. Run `mlplatform manifest validate` against a manifest requesting a lower risk profile; show central effective profile remains unchanged.
5. Generate JSON report and `release-plan` demonstrating **technically eligible but not production-authorized**.
6. Trigger representative PR cloud validation (Phase 2) and inspect report/evidence.
7. Demonstrate a staged release by immutable digest and a simulated canary rollback (Phase 3).
8. Move one model folder to independent Repo A (Phase 4), re-run the same validator unchanged.

---

## Appendix A — Illustrative Reusable GitHub Workflow (future multi-repo)

```yaml
# Repo A: .github/workflows/model-validation.yml
name: Model Validation
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  validate:
    uses: company/App-inmo-platform/.github/workflows/reusable-validation.yml@<pinned-sha>
    with:
      manifest_path: manifest.yaml
```

The reusable workflow must **not** inherit privileged secrets for executing arbitrary DS code. An independently protected required check is used for mandatory release gates. The exact setup is organization-specific.

## Appendix B — Related References (design inspiration, not dependencies)

- Cookiecutter Data Science — https://github.com/drivendataorg/cookiecutter-data-science
- Kedro — https://github.com/kedro-org/kedro
- CML — https://github.com/iterative/cml
- Google Vertex AI samples — https://github.com/GoogleCloudPlatform/vertex-ai-samples
- GitHub Actions reusable workflows — https://docs.github.com/en/actions/sharing-automations/reusing-workflows
