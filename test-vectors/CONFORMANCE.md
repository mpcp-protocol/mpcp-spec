# Conformance levels (test vectors)

This directory provides **deterministic hash vectors** for canonical JSON and domain-separated
prefixes. Conformance is layered: higher levels assume lower levels and add obligations from
[Verification](../docs/protocol/verification.md) and [mpcp.md — Verification Algorithm](../docs/protocol/mpcp.md#verification-algorithm).

## Level L0 — Canonical hash reproduction

**Requirement:** Recompute `SHA-256(UTF-8(prefix) || canonical_json(payload))` for each entry in
[`expected-hashes.json`](expected-hashes.json) and obtain the documented lowercase hex digest.

**Covers:** Stable serialization for policy documents, PolicyGrant signing payloads, and SBA inner
`authorization` inputs.

**Tooling:** [`verify_test_vectors.py`](verify_test_vectors.py) (exit code 0 on success).

## Level L1 — Structural sanity (informative)

**Requirement:** Parsed JSON objects include the fields required by the **minimal v1** examples in
this repo (see source files named `*-v1-minimal.json`). This level does **not** replace normative
schema definitions in the spec; it helps catch accidental edits to fixtures.

**Covers:** Basic shape of policy document, grant payload, and SBA authorization objects used for
L0 hashing.

## Level L2 — Full-chain verification (deployment)

**Requirement:** Verify **signatures**, **linkage**, **MPCP v1 XRPL conformance**, **policy**
constraints, **budget** enforcement, and optional **fleet** steps exactly as in the [Verification
pipeline](../docs/protocol/verification.md) and [mpcp.md Step 0–3](../docs/protocol/mpcp.md#settlement-verification).

**Covers:** Production Trust Gateway behavior. The minimal JSON files here use **placeholder**
signatures and are **not** sufficient alone to pass L2; implementations need signed fixtures or
generated keys in a controlled test harness.

## Machine-readable manifest

[`expected-verification.json`](expected-verification.json) summarizes which artifacts participate
in each level and cross-links to spec sections. It is **documentation for tooling authors**, not an
additional cryptographic test by itself.
