# Lite Profile — SPA-Only Settlement Binding

Part of the [Machine Payment Control Protocol (MPCP)](../protocol/mpcp.md).

## Overview

The **Lite profile** is an MPCP deployment configuration in which the `intentHash` field is omitted from the SignedPaymentAuthorization (SPA).

Settlement verification proceeds on the fields explicitly carried in the SPA:

- `rail`
- `asset`
- `amount`
- `destination`

Fields outside the SPA — such as memo content, ancillary metadata, or other settlement intent fields — are not cryptographically bound.

---

## When to Use the Lite Profile

The Lite profile is appropriate when one or more of the following conditions apply:

### Closed-Loop Infrastructure

A single operator controls both the payment authorization service and the settlement execution layer. Because both ends of the transaction are under the same authority, the risk of memo or metadata substitution between authorization and execution is eliminated by operational controls rather than cryptographic binding.

Examples: proprietary tolling systems, single-vendor EV charging networks, captive fleet payment infrastructure.

### Rail-Native Parameter Binding

Some payment rails provide their own cryptographic binding of transaction parameters at the protocol level. In these environments, the rail itself guarantees that the executed transaction matches the authorized parameters; `intentHash` would be redundant.

### High-Volume Micropayments

In environments with very high transaction frequency and constrained payload budgets (bandwidth-limited IoT networks, high-throughput robotic logistics), omitting `intentHash` reduces SPA size and verifier processing cost. The SPA-bound fields still enforce the core payment constraints.

---

## Protection Provided

| Check | Protected |
|-------|-----------|
| Rail | Yes — SPA.rail checked against executed transaction |
| Asset | Yes — SPA.asset checked against executed transaction |
| Amount | Yes — SPA.amount checked against executed transaction |
| Destination | Yes — SPA.destination checked against executed transaction |
| Memo / metadata | No — not cryptographically bound |
| Full payload mutation | No — only SPA-carried fields are verified |

---

## Protection Not Provided

When `intentHash` is absent, an attacker who can intercept or substitute the settlement instruction between authorization issuance and execution could modify:

- memo fields
- ancillary metadata
- any field not explicitly carried in the SPA

Deployments using the Lite profile MUST evaluate whether these vectors are relevant to their threat model.

---

## SPA Structure

A Lite profile SPA omits `intentHash`:

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
    "expiresAt": "2026-03-08T14:00:00Z"
  },
  "issuer": "did:web:payments.example.com",
  "issuerKeyId": "payment-auth-key-1",
  "signature": "base64..."
}
```

---

## Verification Behavior

Step 3 of the MPCP verification algorithm (intent binding) is skipped when `intentHash` is absent. All other verification steps apply in full.

---

## See Also

- [Full Profile](./full-profile.md) — SPA + intentHash binding
- [SignedPaymentAuthorization](../protocol/SignedPaymentAuthorization.md)
- [SettlementIntentHash](../protocol/SettlementIntentHash.md)
