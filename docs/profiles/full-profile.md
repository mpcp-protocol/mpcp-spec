# Full Profile — SPA + IntentHash Binding

Part of the [Machine Payment Control Protocol (MPCP)](../protocol/mpcp.md).

## Overview

The **Full profile** is an MPCP deployment configuration in which the `intentHash` field is required in the SignedPaymentAuthorization (SPA).

The `intentHash` is the SHA-256 hash of the canonical settlement intent payload, computed as:

```
intentHash = SHA256("MPCP:SettlementIntent:1.0:" || canonicalJson(canonicalPayload))
```

This binds the SPA to a specific, deterministic description of the settlement transaction. Mutation of any field in the canonical payload — destination, amount, asset, memo, or other fields — invalidates the authorization binding and causes verification to fail.

---

## When to Use the Full Profile

The Full profile is appropriate when one or more of the following conditions apply:

### Open Settlement Environments

Multiple vendors, operators, or intermediaries participate in the settlement pipeline. Without `intentHash` binding, a party in the middle could substitute or modify settlement instructions without invalidating the authorization.

### Dispute-Sensitive Deployments

When payment disputes require cryptographic proof that the executed transaction matches the authorized intent, the `intentHash` provides an irrefutable binding between the SPA and the settlement. Combined with optional Intent Attestation Layer (IAL) anchoring, the commitment can be proven to have existed prior to settlement.

### Multi-Vendor Infrastructure

A fleet operator, infrastructure operator, and payment service are distinct parties. Each stage of the pipeline is operated independently, increasing the surface area for substitution attacks. `intentHash` ensures that the settlement intent issued by one party cannot be modified by another.

### Audit-Required Environments

Regulatory or contractual requirements demand a complete audit trail linking each payment authorization to the specific settlement transaction parameters, including fields beyond rail/asset/amount/destination.

---

## Protection Provided

| Check | Protected |
|-------|-----------|
| Rail | Yes — SPA.rail checked against executed transaction |
| Asset | Yes — SPA.asset checked against executed transaction |
| Amount | Yes — SPA.amount checked against executed transaction |
| Destination | Yes — SPA.destination checked against executed transaction |
| Memo / metadata | Yes — included in canonical payload, mutation invalidates intentHash |
| Full payload mutation | Yes — any deviation from the canonical intent fails verification |

---

## SPA Structure

A Full profile SPA includes `intentHash`:

```json
{
  "authorization": {
    "version": "1.0",
    "decisionId": "dec_123",
    "sessionId": "sess_456",
    "policyHash": "a1b2c3...",
    "quoteId": "quote_789",
    "rail": "xrpl",
    "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." },
    "amount": "19440000",
    "destination": "rDest...",
    "intentHash": "e3b0c44298fc1c149afbf4c8996fb924...",
    "expiresAt": "2026-03-08T14:00:00Z"
  },
  "issuer": "did:web:payments.example.com",
  "issuerKeyId": "payment-auth-key-1",
  "signature": "base64..."
}
```

---

## Verification Behavior

Step 3 of the MPCP verification algorithm (intent binding) is executed when `intentHash` is present.

The verifier reconstructs the canonical payload from the settlement intent and confirms:

```
SHA256("MPCP:SettlementIntent:1.0:" || canonicalJson(canonicalPayload)) == SPA.intentHash
```

If the hashes do not match, verification fails and the settlement is rejected.

---

## Optional: Intent Attestation Layer (IAL)

Full profile deployments may additionally publish the `intentHash` to the Intent Attestation Layer (IAL) before settlement execution. This creates a timestamped, tamper-evident public record that the commitment existed prior to the transaction, enabling third-party dispute resolution.

See [Anchoring](../protocol/anchoring.md) for the IAL integration specification.

---

## See Also

- [Lite Profile](./lite-profile.md) — SPA-only settlement binding
- [SignedPaymentAuthorization](../protocol/SignedPaymentAuthorization.md)
- [SettlementIntentHash](../protocol/SettlementIntentHash.md)
- [Anchoring](../protocol/anchoring.md)
