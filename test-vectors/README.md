# MPCP v1.0 test vectors

Deterministic **SHA-256** digests for conformance testing. Inputs use **UTF-8** encoding.

## Canonical JSON

Per [MPCP canonical JSON](../docs/protocol/mpcp.md#canonical-json-definition):

1. Object keys sorted **lexicographically** (recursively).
2. No insignificant whitespace (files in this directory use **minified** JSON).
3. Monetary amounts as strings where the protocol uses strings.
4. Omit `null` / undefined fields.

## Vectors

| Input file | Hash domain | Purpose |
|------------|-------------|---------|
| `policy-document-v1-minimal.json` | `MPCP:Policy:1.0:` + canonical JSON | `PolicyGrant.policyHash` source document |
| `policy-grant-payload-v1-minimal.json` | `MPCP:PolicyGrant:1.0:` + canonical JSON | PolicyGrant signing payload (**excludes** `signature`) |
| `sba-authorization-v1-minimal.json` | `MPCP:SBA:1.0:` + canonical JSON | SBA inner `authorization` signing input |

Expected hexadecimal digests (lowercase) are in `expected-hashes.json`.

**Conformance levels** (L0 hash, L1 structure, L2 full-chain verification) and how they map to the
spec verification pipeline are documented in [CONFORMANCE.md](./CONFORMANCE.md). A machine-readable
summary is in [`expected-verification.json`](./expected-verification.json).

## Verification script

```bash
python3 test-vectors/verify_test_vectors.py
```

The script recomputes hashes and exits non-zero on mismatch.

## Signatures

Artifact files may include placeholder `signature` values for human readability. **Hash vectors** above cover only the **canonical JSON payloads** documented in the spec, not valid cryptographic signatures.
