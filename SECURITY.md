# Security Policy

OpenOntologyLite treats ontology files as untrusted input.

## Supported Version

`0.1.0a3` is an alpha release. Security reports are welcome for the current alpha line.

## Threat Model

| Threat | Risk | Mitigation | Remaining limitation |
|---|---|---|---|
| Malicious YAML payload | Object construction, ambiguity, or code execution | Uses a `SafeLoader` subclass and rejects duplicate keys | Parser bugs remain possible |
| Oversized ontology file | Memory or CPU denial of service | Bounded reads plus file-size, parsed-node, nesting, and retained-issue limits | Limits are fixed in alpha |
| Recursive reference graph | Infinite recursion | Iterative-safe graph traversal and cycle reporting | Cycles may still confuse downstream tools |
| Terminal escape injection | Misleading CLI output | Control characters are stripped from human-readable diagnostics | Terminal-specific rendering varies |
| Mermaid injection | Diagram corruption | CLI exports validate before rendering and labels are escaped | Mermaid parser behavior may change |
| Markdown injection | Malformed docs | Table and control-sensitive characters are escaped | Markdown renderers differ |
| Malicious regex pattern | Regex denial of service downstream | Patterns are not executed by OpenOntologyLite | Consumers must handle patterns safely |
| Path traversal in output filename | Writing unexpected files | CLI writes only to explicitly supplied local paths | Caller controls path |
| External reference resolution | Network exfiltration or dependency confusion | No remote schema resolution | Exported schemas may contain local `$ref` values |
| Unsafe precondition execution | Code execution | Preconditions are declarative strings and never executed | Consumers must not execute them blindly |
| Dependency compromise | Supply-chain risk | Minimal dependencies and audit workflow | Audits are point-in-time |
| Package substitution | Installing wrong package | Metadata documents package name and repository | Users must verify install source |
| Tampered ontology file | Incorrect operational meaning | Canonical digest available | Digest is not a signature |
| Hash misunderstanding | False trust in digest | Docs state digest is integrity aid only | Signing is roadmap |
| Entity explosion | Resource exhaustion | Count limits for core declarations | Limits may need tuning |
| Malformed Unicode | Output confusion | UTF-8 loading and control character checks | Unicode confusables are not rejected |
| Archive contamination | Secrets or caches in packages | Build excludes caches, envs, dist outputs | Human review still required |
| Accidental secret inclusion | Publishing sensitive examples | Examples use synthetic data | Maintainers must review changes |
| Misleading diff classification | Release risk | Conservative classification and docs | It is not a formal compatibility proof |

## Reporting

Report vulnerabilities through the repository's
[private vulnerability reporting form](https://github.com/sekacorn/OpenOntologyLite/security/advisories/new).
If that form is unavailable, open a minimal public issue that avoids exploit details.
