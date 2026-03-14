# SettlementIntent

Artifact Type: MPCP:SettlementIntent

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

---

## Purpose

A **SettlementIntent** defines the canonical description of a payment that an agent intends to execute.

It represents the **deterministic settlement parameters** that must match the eventual payment transaction. A hash of the intent (`intentHash`) may be embedded in higher‑level artifacts such as **SignedPaymentAuthorization (SPA)**.

SettlementIntent allows MPCP implementations to:

- bind a payment authorization to a deterministic settlement description
- verify that a payment matches the intended parameters
- prevent parameter tampering
- enable cross‑rail verification

SettlementIntent itself is typically **not signed**. Instead, its hash is referenced and protected by signatures of higher‑level artifacts.

---

## Problem

In autonomous payment environments, clients executing payments may attempt to alter parameters such as:

- payment amount
- destination address
- payment rail
- asset

If those parameters are not deterministically bound to the authorization artifact, a payment could diverge from the policy decision.

SettlementIntent solves this by defining a **canonical payment description** whose hash can be embedded in signed artifacts.

---

## Structure

### SettlementIntent (payload)

| Field | Type | Required | Description |
|------|------|----------|-------------|
| version | string | yes | MPCP semantic version (e.g. "1.0") |
| rail | Rail | yes | Payment rail (xrpl, evm, stripe, hosted) |
| asset | Asset | conditional | Required for on‑chain rails |
| amount | string | yes | Amount in atomic units |
| destination | string | conditional | Destination address for on‑chain rails |
| referenceId | string | optional | Identifier linking intent to decision or quote |
| createdAt | string | optional | ISO 8601 timestamp. Metadata for audit/debugging; excluded from canonical hashing unless a temporal profile explicitly requires it. |

---

## Example

```json
{
  "version": "1.0",
  "rail": "xrpl",
  "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." },
  "amount": "19440000",
  "destination": "rDestination...",
  "referenceId": "quote_17",
  "createdAt": "2026-03-08T13:55:00Z"
}
```

---

## Intent Hash

The **intentHash** is the deterministic identifier derived from a SettlementIntent.

Hash computation uses **domain‑separated hashing** consistent with MPCP artifacts.

```
intentHash = SHA256(
  "MPCP:SettlementIntent:1.0:" || canonicalJson(canonicalIntent)
)
```

Domain separation ensures the hash cannot collide with other MPCP artifact hashes.

---

## Canonical Hash Payload

The intent hash MUST be computed from a **canonical payload** containing only fields that define the **settlement semantics**.

Metadata fields MUST be excluded.

Default canonical payload fields:

- version
- rail
- asset (if present)
- amount
- destination (if present)
- referenceId (if present)

The following fields MUST NOT participate in canonical hashing under the default MPCP profile:

- createdAt

Example canonical payload:

```json
{
  "version": "1.0",
  "rail": "xrpl",
  "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." },
  "amount": "19440000",
  "destination": "rDestination...",
  "referenceId": "quote_17"
}
```

This ensures that two semantically identical intents produce the same `intentHash` even if metadata such as `createdAt` differs.

Implementations MAY define extended profiles where metadata fields participate in hashing, but such profiles MUST be explicitly documented and versioned.

---

## Canonical JSON

Implementations MUST compute the hash using a canonical JSON representation of the canonical payload defined above (not the full artifact).

Requirements:

- stable key ordering
- no whitespace variation
- UTF‑8 encoding

Example (conceptual):

```
canonicalJson(intent)
```

---

## Relationship to SPA

A **SignedPaymentAuthorization (SPA)** may include `intentHash`.

When present, the SPA verifier must ensure:

```
intentHash == SHA256("MPCP:SettlementIntent:<version>:" || canonicalJson(intent))
```

This binds the SPA to a specific settlement intent.

---

## Verification

A settlement verifier must ensure that the executed payment matches the SettlementIntent.

Checks typically include:

- rail matches
- asset matches (if applicable)
- destination matches (if applicable)
- amount matches

If the SPA contains an `intentHash`, the verifier must also recompute the hash and ensure it matches the SPA.

---

## Rail Semantics

Different rails use different subsets of the intent fields.

| Rail | asset | destination |
|-----|------|-------------|
| xrpl | required | required |
| evm | required | required |
| stripe | omitted | omitted |
| hosted | omitted | omitted |

Implementations must enforce the correct field requirements for the selected rail.

---

## Summary

SettlementIntent defines the canonical payment description used to bind authorizations to deterministic settlement parameters.

By hashing the intent and embedding the hash into signed artifacts, MPCP ensures that the executed payment cannot diverge from the authorized parameters.

---

## See Also

- [MPCP Reference Flow — EV Charging](../architecture/fleet-ev-reference-flow.md) — Demonstrates how SettlementIntent is used during runtime authorization.
