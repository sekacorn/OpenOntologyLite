# AI System Maps

An AI System Map is a portable, declarative inventory of AI workloads and their intended controls. It preserves business meaning across model or orchestration changes without claiming to execute those controls.

## Contents

The `1.0` schema records:

- system identity, purpose, environment, and overall risk profile;
- business entities and their sensitivity;
- named AI tasks and task categories;
- allowed routes: `candidate_model`, `baseline_model`, `human_review`, and `blocked_or_escalate`;
- risk levels: `low`, `medium`, `high`, `regulated`, and `unknown`;
- human-review and escalation requirements;
- expected audit events and cost metrics;
- data sources, retrieval boundaries, models, fallbacks, agent roles, and tool access;
- review points, failure modes, retention, deployment and geographic restrictions;
- policy, integration-contract, ontology, and provenance references;
- portable integration-pattern meaning; and
- explicit limitations.

Escalation paths are `human_review`, `security_review`, `legal_review`, `compliance_review`, `do_not_answer`, and `baseline_model_only`.

## Validate

```powershell
openontology ai-map validate examples/ai_system_map/customer_support_ai.yaml
openontology ai-map validate examples/ai_system_map/customer_support_ai.yaml --json
openontology ai-map validate examples/ai_system_map/customer_support_ai.yaml --strict
```

Validation checks stable names and references, known risk and route values, sensitive-task
controls and handling expectations, review and escalation paths, high-risk candidate routes,
declared audit and cost expectations, and optional ontology entity, action, and permission
references. High or unknown-risk candidate routing without review or justification produces a
warning; regulated candidate routing without those controls is an error.

## Report

```powershell
openontology ai-map report examples/ai_system_map/customer_support_ai.yaml `
  --format markdown `
  --output build/customer-support-ai.md
```

The report includes data, model, tool, deployment, and handling boundaries in addition to the
system summary, tasks, routes, review, audit, cost, integrations, warnings, limitations, and
canonical SHA-256 digest. No generation timestamp is added.

## Render

```powershell
openontology ai-map render examples/ai_system_map/customer_support_ai.yaml `
  --format mermaid `
  --output build/customer-support-ai.mmd
```

The renderer emits Mermaid source only. Labels are escaped and node identifiers are generated rather than derived from untrusted names.

## Integration Meaning

Integration entries describe how another tool could consume or support the map. For example, ModelSwapBench can represent candidate-versus-baseline comparison meaning, AgentPolicyPack can represent policy checks, AIAuditLog can represent audit events, and AIMeter OSS can represent cost/outcome metrics. These are integration patterns, not evidence of installed, configured, or verified live integrations.

## Limits

AI System Maps do not route requests, call models, authorize actions, guarantee regulatory compliance, verify reviewer qualifications, enforce logging, or measure cost. Deployments must implement and test those controls in their own runtime and jurisdiction.
