# SignedBudgetAuthorization (SBA)

Artifact Type: MPCP:SBA

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

## Purpose

The **SignedBudgetAuthorization (SBA)** defines a signed spending envelope for a machine payment scope.

It is a protocol-level MPCP artifact that constrains subsequent **SignedPaymentAuthorization (SPA)** artifacts.

Unlike application-specific budget concepts, SBA is generic and may be used across parking, charging, tolling, robotics, AI agents, and other machine-payment environments.

The **SignedBudgetAuthorization (SBA)** establishes the maximum spending envelope available to a machine for a defined payment scope.

It is issued after a PolicyGrant and constrains subsequent SignedPaymentAuthorizations (SPAs).

---

## Structure

### BudgetAuthorization (inner payload)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | string | yes | MPCP semantic version (e.g. "1.0") |
| budgetId | string | yes | Unique identifier for this budget |
| sessionId | string | yes | Session this budget applies to |
| vehicleId | string | yes | Vehicle identifier |
| scopeId | string | no | Optional scope identifier |
| policyHash | string | yes | Hash of the policy that authorized this budget |
| currency | string | yes | Reference currency (e.g. "USD") |
| minorUnit | number | yes | Decimal scale (e.g. 2) |
| budgetScope | string | yes | SESSION \| DAY \| VEHICLE \| FLEET |
| maxAmountMinor | string | yes | Maximum spend in minor units |
| allowedRails | Rail[] | yes | Permitted payment rails (xrpl, evm, stripe, hosted) |
| allowedAssets | Asset[] | yes | Permitted assets |
| destinationAllowlist | string[] | no | Optional allowed destination addresses |
| expiresAt | string | yes | ISO 8601 expiration timestamp |

### SignedBudgetAuthorization (envelope)

| Field | Type | Description |
|-------|------|-------------|
| authorization | BudgetAuthorization | The budget payload |
| signature | string | Base64-encoded signature over SHA256("MPCP:SBA:1.0:" || canonicalJson(authorization)) |
| keyId | string | Signing key identifier for verification |

---

## Scope Model

SBA supports multiple budget scopes.

| Scope | Meaning |
|------|---------|
| SESSION | Budget applies to a single session |
| DAY | Budget applies across sessions for a day |
| VEHICLE | Budget applies across sessions for a specific vehicle |
| FLEET | Budget applies across vehicles within a fleet authority |

When present, `scopeId` identifies the entity the budget applies to.

Examples:

- `budgetScope: "SESSION"` with `scopeId` = session identifier
- `budgetScope: "VEHICLE"` with `scopeId` = vehicle identifier
- `budgetScope: "FLEET"` with `scopeId` = fleet identifier

## Example

```json
{
  "authorization": {
    "version": "1.0",
    "budgetId": "550e8400-e29b-41d4-a716-446655440000",
    "sessionId": "sess_456",
    "vehicleId": "veh_001",
    "policyHash": "a1b2c3...",
    "currency": "USD",
    "minorUnit": 2,
    "budgetScope": "SESSION",
    "maxAmountMinor": "3000",
    "allowedRails": ["xrpl"],
    "allowedAssets": [{ "kind": "IOU", "currency": "USDC", "issuer": "rIssuer..." }],
    "destinationAllowlist": ["rDest..."],
    "expiresAt": "2026-03-08T14:00:00Z"
  },
  "signature": "base64...",
  "keyId": "mpcp-sba-signing-key-1"
}
```

---

## Verification

All MPCP signatures MUST use domain-separated hashing before signing.

For SBA artifacts the domain prefix is:

```
MPCP:SBA:<version>:
```

Example hash computation:

```
hash = SHA256("MPCP:SBA:1.0:" || canonicalJson(authorization))
```

This prevents cross-protocol and cross-artifact hash collisions and ensures compatibility with MPCP verifier implementations.

A verifier MUST:

1. Validate the signature over SHA256("MPCP:SBA:<version>:" || canonicalJson(authorization)) using the public key for `keyId`
2. Check `expiresAt` has not passed
3. When verifying against a payment decision or settlement context: ensure sessionId, policyHash, budgetScope, allowedRails, allowedAssets, optional destination constraints, and amount constraints match

---

## Relationship to Pipeline

```
PolicyGrant
    ↓
SignedBudgetAuthorization (SBA)
    ↓
SignedPaymentAuthorization (SPA)
    ↓
Settlement
```

---

## See Also

- [MPCP Reference Flow — EV Charging](../architecture/reference-flow.md) — Demonstrates how SBA is used during runtime authorization.
