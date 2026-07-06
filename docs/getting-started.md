# Getting Started

Install the package, validate an ontology, inspect it, and export derived artifacts:

```powershell
python -m pip install openontologylite
openontology validate examples/customer_support.yaml
openontology inspect examples/customer_support.yaml
openontology export-json-schema examples/customer_support.yaml
```
