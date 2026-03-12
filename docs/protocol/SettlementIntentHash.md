# SettlementIntentHash

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

The **intentHash** is an optional field in the SignedPaymentAuthorization (SPA) that binds the authorization to a canonical settlement intent.

When present, it ensures the executed settlement matches the authorized intent.

---

## Definition

```
intentHash = SHA256(
  "MPCP:SettlementIntent:1.0:" || canonicalJson(canonicalIntent)
)
```

- **canonicalJson**: Deterministic JSON serialization (sorted keys, omit null/undefined)
- **SHA256**: Output as hex string

## Canonical Hash Payload

The intent hash MUST be computed from a **canonical payload** that includes only the fields defining the settlement semantics.

Metadata fields present in the artifact MUST be excluded from the hash input.

Default canonical payload fields:

- version
- rail
- asset (if present)
- amount
- destination (if present)
- referenceId (if present)

The following fields MUST NOT participate in hashing under the default MPCP profile:

- createdAt

Example canonical payload:

```json
{
  "version": "1.0",
  "rail": "xrpl",
  "asset": { "kind": "IOU", "currency": "USDC", "issuer": "rIssuer..." },
  "amount": "19440000",
  "destination": "rDest...",
  "referenceId": "quote_17"
}
```


See also: [SettlementIntent.md](./SettlementIntent.md) §Canonical Hash Payload.

---

## Purpose

1. **Binding** — The SPA authorizes a specific settlement. The intentHash commits to the exact intent structure.
2. **Verification** — A verifier can check that the executed settlement corresponds to the intent by recomputing the hash.
3. **Replay protection** — The intent is uniquely bound to the authorization.

---

## Canonical JSON Rules

Per the MPCP spec, canonicalJson is applied to the canonical payload defined above:

- Sorts object keys lexicographically
- Omits fields with `null` or `undefined` values
- Recursively canonicalizes nested objects and arrays

---

## Example

### Settlement intent (rail-specific)

```json
{
  "version": "1.0",
  "rail": "xrpl",
  "destination": "rDest...",
  "amount": "19440000",
  "asset": { "kind": "IOU", "currency": "USDC", "issuer": "rIssuer..." },
  "createdAt": "2026-03-08T13:55:00Z"
}
```

### Computation

```text
canonicalIntent = canonicalJson({
  version,
  rail,
  asset,
  amount,
  destination
})
intentHash = sha256Hex("MPCP:SettlementIntent:1.0:" || canonicalIntent)
```

### SPA with intentHash

```json
{
  "authorization": {
    "version": "1.0",
    "decisionId": "dec_123",
    "sessionId": "sess_456",
    "rail": "xrpl",
    "asset": { "kind": "IOU", "currency": "USDC", "issuer": "rIssuer..." },
    "amount": "19440000",
    "destination": "rDest...",
    "intentHash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "expiresAt": "2026-03-08T14:00:00Z"
  },
  "signature": "...",
  "keyId": "mpcp-spa-signing-key-1"
}
```

---

## Verification

When an SPA includes `intentHash`:

1. The verifier MUST be given the `settlementIntent` used at authorization time (or the executed settlement in intent form).
2. The verifier computes `computeIntentHash(settlementIntent)`.
3. The verifier MUST reject if the computed hash does not match `authorization.intentHash`.

If `intentHash` is absent, the verifier checks only the explicit fields (amount, rail, asset, destination) against the settlement.

---

## Optional vs Required

- **Optional** — SPAs may omit `intentHash` when the intent structure is not needed or when verification is done by policy-only matching.
- **Recommended** — When the settlement intent is known at authorization time, include `intentHash` for stronger binding and replay protection.
