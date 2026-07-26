# Getting Started

Install the package, validate an ontology, inspect it, and export derived artifacts:

```powershell
python -m pip install openontologylite
openontology validate examples/customer_support.yaml
openontology inspect examples/customer_support.yaml
openontology export-json-schema examples/customer_support.yaml
```

Validate and document the included AI workload example:

```powershell
openontology ai-map validate examples/ai_system_map/customer_support_ai.yaml
openontology ai-map report examples/ai_system_map/customer_support_ai.yaml --output build/customer-support-ai.md
openontology ai-map render examples/ai_system_map/customer_support_ai.yaml --format mermaid --output build/customer-support-ai.mmd
```
