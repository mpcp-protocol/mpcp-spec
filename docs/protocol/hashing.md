# Hashing

MPCP uses deterministic, domain-separated hashing for signatures.

## Canonical JSON

All hash inputs use **canonical JSON**:

- Sorted keys (lexicographic)
- No whitespace
- UTF-8 encoding
- Consistent handling of optional/null fields

This ensures identical hashes across implementations and environments.

## Domain-Separated Prefixes

MPCP prefixes hash inputs with a domain string to prevent cross-artifact and cross-protocol collisions:

| Artifact | Domain Prefix |
|----------|---------------|
| PolicyGrant | `MPCP:PolicyGrant:1.0:` |
| SBA | `MPCP:SBA:1.0:` |

Example for SBA:

```
hash = SHA256("MPCP:SBA:1.0:" || canonicalJson(authorization))
```

The version in the prefix matches the artifact `version` field.

## Purpose

- **Deterministic verification** — Same input → same hash across implementations
- **Future versions** — Domain prefixes isolate 1.0 from 1.1, 2.0, etc.

## See Also

- [Verification](verification.md)
