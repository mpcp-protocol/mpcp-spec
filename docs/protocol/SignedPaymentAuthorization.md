# SignedPaymentAuthorization (SPA)

Artifact Type: MPCP:SPA

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

## Purpose

The **SignedPaymentAuthorization (SPA)** is a cryptographically signed authorization that permits a specific settlement transaction.

It binds the payment parameters (rail, asset, amount, destination) to a prior policy decision and optionally binds the authorization to a canonical settlement intent via `intentHash`.

SPA makes payment decisions:

- portable
- verifiable
- deterministic
- safe for autonomous agents

Instead of trusting UI state or API responses, the payer executes a payment that is bound to a **signed authorization artifact**.

SPA is a protocol artifact and is not tied to any specific application implementation.

---

## Structure

### PaymentAuthorization (inner payload)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | string | yes | MPCP semantic version (e.g. "1.0") |
| decisionId | string | yes | Payment policy decision identifier. Uniqueness is scoped to the issuer namespace — the replay key is `(issuer, decisionId)`. The SPA issuer MUST never issue two SPAs with the same `(issuer, decisionId)` pair. |
| sessionId | string | yes | Session identifier |
| policyHash | string | yes | SHA-256 hash of the canonical policy document under which this payment was authorized. Computed as `SHA256("MPCP:Policy:<version>:" \|\| canonicalJson(policyDocument))`. |
| budgetId | string | yes | References the `SBA.authorization.budgetId` that authorized the spending envelope for this payment. Verifiers use this to resolve the SBA and confirm policy chain linkage. |
| quoteId | string | yes | Settlement quote identifier |
| rail | Rail | yes | Payment rail (xrpl, evm, stripe, hosted) |
| asset | Asset | conditional | Required for on-chain rails (xrpl, evm); omitted for hosted rails |
| amount | string | yes | Amount in atomic units |
| destination | string | conditional | Required for on-chain rails; not required for hosted rails |
| intentHash | string | no | SHA256 hex of the canonical settlement intent payload. When present (Full profile), mutation of any canonical payload field invalidates the authorization binding. When omitted (Lite profile), protection is limited to the settlement fields explicitly carried in the SPA. See [Deployment Profiles](../profiles/lite-profile.md). |
| expiresAt | string | yes | ISO 8601 expiration timestamp |

### SignedPaymentAuthorization (envelope)

| Field | Type | Description |
|-------|------|-------------|
| authorization | PaymentAuthorization | The payment payload |
| issuer | string | Identifier for the payment authorization authority (e.g. DID, domain, or registry ID). Verifiers use this to resolve the signing key. |
| issuerKeyId | string | Identifies the specific key used to sign (alias: `keyId` retained for backward compatibility) |
| signature | string | Base64-encoded signature over SHA256("MPCP:SPA:1.0:" || canonicalJson(authorization)) |

---

## Example

```json
{
  "authorization": {
    "version": "1.0",
    "decisionId": "dec_123",
    "sessionId": "sess_456",
    "policyHash": "a1b2c3...",
    "budgetId": "budget_123",
    "quoteId": "quote_789",
    "rail": "xrpl",
    "asset": { "symbol": "USDC", "namespace": "rIssuer..." },
    "amount": "19440000",
    "destination": "rDest...",
    "intentHash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "expiresAt": "2026-03-08T14:00:00Z"
  },
  "issuer": "did:web:payments.example.com",
  "issuerKeyId": "payment-auth-key-1",
  "signature": "base64..."
}
```

---

## Rail Semantics

Different payment rails require different subsets of the authorization fields.

| Rail | asset | destination | Notes |
|-----|------|-------------|------|
| xrpl | required | required | XRPL payments require issuer/currency and destination address |
| evm | required | required | ERC‑20 or native asset transfer to a destination address |
| stripe | omitted | omitted | Stripe settlement determined by backend charge request |
| hosted | omitted | omitted | Hosted payment session resolves settlement parameters |

Implementations MUST enforce the field requirements appropriate for the selected rail.

For on‑chain rails (`xrpl`, `evm`) the verifier must check:

- asset matches the executed transaction
- destination matches the executed transaction
- amount matches the authorized amount

For hosted rails the verifier checks settlement against the backend payment record.

## Verification

All MPCP signatures use domain‑separated hashing before signing.

For SPA artifacts the domain prefix is:

MPCP:SPA:<version>:

Example hash computation:

hash = SHA256("MPCP:SPA:1.0:" || canonicalJson(authorization))

This prevents cross‑artifact and cross‑protocol hash collisions.

A verifier MUST:

1. Resolve the public key (as JWK) using `issuer` and `issuerKeyId` (or `keyId` if present) via the HTTPS well-known endpoint or pre-configured keys (see [Key Resolution](./key-resolution.md)), then validate the signature over SHA256("MPCP:SPA:<version>:" || canonicalJson(authorization))
2. Check `expiresAt` has not passed
3. When verifying against a SettlementResult: ensure decisionId, rail, amount, destination, and asset match
4. If `intentHash` is present: verify it equals `computeIntentHash(settlementIntent)` for the provided intent

---

## Relationship to Pipeline

```
SignedBudgetAuthorization (SBA)
    ↓
SignedPaymentAuthorization (SPA)
    ↓
Settlement Execution
    ↓
Settlement Verification
```

See [SettlementIntentHash](./SettlementIntentHash.md) for details on the optional intent binding.

---

## See Also

- [MPCP Reference Flow — EV Charging](../architecture/reference-flow.md) — Demonstrates how SPA is used during runtime authorization.
