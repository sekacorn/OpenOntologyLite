# Python API

```python
from open_ontology_lite import (
    build_migration_plan,
    check_action_contract,
    generate_audit_context,
    generate_benchmark_fixture,
    generate_meter_attribution,
    generate_policy_context,
    generate_rag_metadata,
    generate_tool_contract,
    load_ontology,
    ontology_digest,
    resolve_local_modules,
    validate_entity_instance,
)
```

The public API returns typed immutable Pydantic models where practical.

Runtime validation never mutates the caller's mapping. Action checks report semantic contract
status as `satisfied`, `unsatisfied`, or `indeterminate`; they do not return an authorization
allow/deny decision. Every neutral handoff contract includes the same ontology ID, version,
namespace, and canonical digest.

See `examples/customer_support_contracts.py` for a complete offline walkthrough.
