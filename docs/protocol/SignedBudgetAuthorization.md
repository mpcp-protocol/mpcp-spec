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
| grantId | string | yes | References the `PolicyGrant.grantId` from which this budget was derived. Verifiers use this to resolve the grant and confirm policy chain linkage. |
| sessionId | string | yes | Session this budget applies to |
| vehicleId | string | yes | Vehicle identifier |
| scopeId | string | no | Optional scope identifier |
| policyHash | string | yes | SHA-256 hash of the canonical policy document under which this budget was authorized. Computed as `SHA256("MPCP:Policy:<version>:" \|\| canonicalJson(policyDocument))`. |
| currency | string | yes | Informational: the fiat reference currency from which this budget was derived (e.g. `"USD"`). Not used in verification arithmetic. |
| minorUnit | number | yes | Informational: decimal scale of the fiat reference currency (e.g. `2` for USD cents). Not used in verification arithmetic. |
| budgetScope | string | yes | SESSION \| DAY \| VEHICLE \| FLEET |
| maxAmountMinor | string | yes | Maximum authorized spend expressed in the **on-chain asset's atomic units** — the same denomination as `SPA.amount`. The session authority converts the fiat budget to on-chain units at SBA issuance time. |
| allowedRails | Rail[] | yes | Permitted payment rails (xrpl, evm, stripe, hosted) |
| allowedAssets | Asset[] | yes | Permitted assets |
| destinationAllowlist | string[] | no | Optional allowed destination addresses |
| expiresAt | string | yes | ISO 8601 expiration timestamp |

### SignedBudgetAuthorization (envelope)

| Field | Type | Description |
|-------|------|-------------|
| authorization | BudgetAuthorization | The budget payload |
| issuer | string | Identifier for the budget authority (e.g. DID, domain, or registry ID). Verifiers use this to resolve the signing key. |
| issuerKeyId | string | Identifies the specific key used to sign (alias: `keyId` retained for backward compatibility) |
| signature | string | Base64-encoded signature over SHA256("MPCP:SBA:1.0:" || canonicalJson(authorization)) |

---

## Scope Model

SBA supports multiple budget scopes. All scopes are cumulative — `maxAmountMinor` represents the total authorized spending across all payments (SPAs) within the scope, regardless of how many individual payments are made.

| Scope | Meaning |
|-------|---------|
| SESSION | Budget applies to a single session |
| DAY | Budget applies across sessions for a calendar day |
| VEHICLE | Budget applies across sessions for a specific vehicle |
| FLEET | Budget applies across vehicles within a fleet authority |

When present, `scopeId` identifies the entity the budget applies to.

Examples:

- `budgetScope: "SESSION"` with `scopeId` = session identifier
- `budgetScope: "VEHICLE"` with `scopeId` = vehicle identifier
- `budgetScope: "FLEET"` with `scopeId` = fleet identifier

## Stateless Verification Model

MPCP verifiers are stateless. They do not track cumulative spending across payments.

This ensures that MPCP verification is deployable across independent, parallel, or ephemeral verifier instances without shared state.

Budget enforcement is split between two roles:

| Role | Responsibility |
|------|----------------|
| Session authority | Tracks cumulative spending per scope. Only issues SPAs within the remaining authorized envelope for the scope. |
| Verifier | Checks that the current SPA amount does not exceed `maxAmountMinor`. Does not track prior payments. |

The verifier's stateless check is:

```
SPA.amount ≤ SBA.maxAmountMinor
```

Both values are in the **on-chain asset's atomic units** — the comparison is a direct numeric check with no currency conversion required. The session authority is responsible for converting the fiat budget into on-chain units at SBA issuance time, using the exchange rate and asset precision applicable at that moment.

This confirms the current payment fits within the authorized envelope. The session authority's signature on each SPA is the cryptographic attestation that cumulative spending remains within bounds — the verifier trusts this by validating the signature.

Verifiers MUST NOT attempt to track or reconstruct cumulative session spending.

## Cumulative Enforcement

To enable accurate cumulative budget enforcement within a session, callers MAY pass the running total of prior spending to the verifier via `cumulativeSpentMinor`.

When provided, the verifier applies:

```
cumulativeSpentMinor + currentPayment <= maxAmountMinor
```

instead of the bare single-payment check. This allows a stateless verifier to correctly reject payments that would exceed the cumulative budget even if each individual payment would fit.

**Session authority responsibility:**
- MUST track cumulative spending per scope (SESSION, DAY, VEHICLE, FLEET)
- MUST pass `cumulativeSpentMinor` to the verifier for correct enforcement
- MUST NOT issue new SPAs when cumulative spending would exceed `maxAmountMinor`

**Offline trust assumption:**
In offline or air-gapped environments (e.g., vehicles without real-time connectivity), cumulative enforcement relies on the session authority (typically the vehicle wallet) maintaining the spending counter in trusted local storage. The verifier cannot independently verify the counter's accuracy in offline mode; this is an accepted trust assumption for offline deployments.

## Example

```json
{
  "authorization": {
    "version": "1.0",
    "budgetId": "550e8400-e29b-41d4-a716-446655440000",
    "grantId": "grant_abc123",
    "sessionId": "sess_456",
    "vehicleId": "veh_001",
    "policyHash": "a1b2c3...",
    "currency": "USD",
    "minorUnit": 2,
    "budgetScope": "SESSION",
    "maxAmountMinor": "30000000",
    "allowedRails": ["xrpl"],
    "allowedAssets": [{ "kind": "IOU", "currency": "USDC", "issuer": "rIssuer..." }],
    "destinationAllowlist": ["rDest..."],
    "expiresAt": "2026-03-08T14:00:00Z"
  },
  "issuer": "did:web:fleet.example.com",
  "issuerKeyId": "budget-auth-key-1",
  "signature": "base64..."
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

1. Resolve the public key (as JWK) using `issuer` and `issuerKeyId` (or `keyId` if present) via the HTTPS well-known endpoint or pre-configured keys (see [Key Resolution](./key-resolution.md)), then validate the signature over SHA256("MPCP:SBA:<version>:" || canonicalJson(authorization))
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
