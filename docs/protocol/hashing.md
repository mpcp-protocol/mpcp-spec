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

## ECDSA secp256k1 (low-S)

For **secp256k1**, ECDSA signatures are **malleable**: for a given message and public key, both
`(r, s)` and `(r, n - s)` (where `n` is the curve order) may verify unless implementations restrict
the form.

**MUST:** Verifiers MUST reject signatures where the `s` component is in the **high-S** half of the
curve order. Only **low-S** signatures (as standardized for Bitcoin and XRPL — see
[BIP-146](https://github.com/bitcoin/bips/blob/master/bip-0146.mediawiki) / Bitcoin **low-S**
policy) MUST be accepted.

**MUST:** Signers MUST produce **low-S** signatures so that verification is deterministic and
malleability cannot be used to duplicate transaction IDs or artifact hashes across deployments.

This requirement applies to all MPCP artifacts and to any JWK with `kty` EC and `crv` secp256k1
listed in [Key Resolution](./key-resolution.md).

## See Also

- [Verification](verification.md)
