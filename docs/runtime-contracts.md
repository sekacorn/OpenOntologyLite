# Runtime Contracts

## Entity Instances

`validate_entity_instance` validates a mapping without mutating it. It supports required and
unknown properties, aliases, defaults, nullable values, primitives, exact decimals, enums,
numeric and length limits, bounded patterns, arrays, nested objects, references, UUIDs, dates,
and datetimes. A reference can be an identifier or an expanded target-shaped mapping.

Strict mode reports unknown properties as errors; non-strict mode reports warnings and omits
them from the canonical value. Supplying an alias and canonical name together is an error.
Invalid declared defaults are reported rather than silently applied.

## Action Checks

`check_action_contract` validates inputs and an optional output, reports required and missing
permissions, and carries risk, review, escalation, audit, and evidence metadata. Preconditions
remain declarative text: each one makes the result indeterminate unless another error already
makes it unsatisfied. The caller's policy and authorization runtime remains responsible for
decisions and enforcement.

Diagnostics are bounded and sanitized. Raw values are not echoed into errors.
