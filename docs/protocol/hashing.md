# Hashing

MPCP uses deterministic, domain-separated hashing for signatures and intent binding.

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
| SBA | `MPCP:SBA:1.0:` |
| SPA | `MPCP:SPA:1.0:` |
| SettlementIntent | `MPCP:SettlementIntent:1.0:` |

Example for SBA:

```
hash = SHA256("MPCP:SBA:1.0:" || canonicalJson(authorization))
```

The version in the prefix matches the artifact `version` field.

## SettlementIntentHash

The **intentHash** binds an SPA to a canonical settlement intent:

```
intentHash = SHA256("MPCP:SettlementIntent:1.0:" || canonicalJson(canonicalIntent))
```

The canonical payload includes only semantic fields:

- version
- rail
- asset (if present)
- amount
- destination (if present)
- referenceId (if present)

Metadata (e.g., `createdAt`) is excluded from the hash.

## Purpose

- **Deterministic verification** — Same input → same hash across implementations
- **Replay protection** — intentHash binds authorization to a specific settlement
- **Dispute resolution** — Intent can be anchored to a ledger; disputes verify anchor against intentHash
- **Future versions** — Domain prefixes isolate 1.0 from 1.1, 2.0, etc.

## See Also

- [SettlementIntentHash spec](SettlementIntentHash.md)
- [Verification](verification.md)
- [Anchoring](anchoring.md)
