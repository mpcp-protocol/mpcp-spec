# PolicyGrant

Artifact Type: MPCP:PolicyGrant

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

---

## Purpose

A **PolicyGrant** represents the result of a policy evaluation performed before a machine is allowed to initiate payment activity.

The PolicyGrant defines the **initial permission envelope** for a session or payment scope. It constrains which rails, assets, and spending limits may later be authorized via MPCP artifacts such as:

- **SignedBudgetAuthorization (SBA)**
- **SignedPaymentAuthorization (SPA)**

PolicyGrant is typically produced by a policy engine during an **entry phase** when a machine, vehicle, or agent attempts to access a service.

The PolicyGrant is a **signed artifact**. It is signed by the policy authority; verifiers use `issuer` and `issuerKeyId` to resolve the policy authority public key for signature verification.

---

## Problem

In autonomous payment environments (vehicles, robots, AI agents), a system must determine **whether payment activity is allowed before any transaction is authorized**.

Without a formal grant artifact:

- agents may bypass policy
- payment decisions may not be traceable to policy evaluation
- downstream authorizations cannot prove they were derived from policy

PolicyGrant solves this by creating a **verifiable policy snapshot** that later artifacts must reference.

---

## Policy Lifecycle Context

Policy evaluation typically occurs in three phases:

```
PolicyGrant
     ↓
SignedBudgetAuthorization (SBA)
     ↓
SignedPaymentAuthorization (SPA)
     ↓
Settlement verification
```

PolicyGrant establishes the **upper policy boundary** that subsequent artifacts must respect.

For example:

- allowed rails
- allowed assets
- spending caps
- policy expiration

Downstream artifacts must be **subsets of the PolicyGrant constraints**.

---

## Structure

### PolicyGrant (payload)

| Field | Type | Required | Description |
|------|------|----------|-------------|
| version | string | yes | MPCP semantic version (e.g. "1.0") |
| grantId | string | yes | Unique identifier for the grant |
| policyHash | string | yes | Hash of the evaluated policy snapshot |
| subjectId | string | yes | Identifier of the entity receiving the grant (vehicle, agent, wallet, etc.) |
| operatorId | string | optional | Service operator identifier |
| scope | string | yes | Scope of the grant (SESSION, VEHICLE, FLEET, etc.) |
| allowedRails | Rail[] | yes | Payment rails permitted by policy |
| allowedAssets | Asset[] | conditional | Allowed assets for on-chain rails |
| maxSpend | object | optional | Spending caps defined by policy |
| expiresAt | string | yes | ISO 8601 expiration timestamp |
| requireApproval | boolean | optional | Indicates that further approval is required before payment |
| reasons | string[] | optional | Policy evaluation reasons |
| issuer | string | yes | Identifier for the policy authority (e.g. DID, domain, or registry ID). Verifiers use this to resolve the signing key. |
| issuerKeyId | string | yes | Identifies the specific key used to sign (for deployments with multiple keys per issuer). |
| signature | string | yes | Cryptographic signature over the canonical JSON of the grant payload (all fields except `signature`). |

---

## Example

```json
{
  "version": "1.0",
  "grantId": "grant_7ab3",
  "policyHash": "9f3a0d...",
  "subjectId": "vehicle_1284",
  "operatorId": "operator_12",
  "scope": "SESSION",
  "allowedRails": ["xrpl", "stripe"],
  "allowedAssets": [
    {
      "kind": "IOU",
      "currency": "RLUSD",
      "issuer": "rIssuer..."
    }
  ],
  "maxSpend": {
    "perTxMinor": "5000",
    "perSessionMinor": "20000"
  },
  "expiresAt": "2026-03-08T14:00:00Z",
  "requireApproval": false,
  "reasons": ["OK"],
  "issuer": "did:web:operator.example.com",
  "issuerKeyId": "policy-auth-key-1",
  "signature": "..."
}
```

---

## Policy Intersection Model

PolicyGrant may represent the intersection of multiple policy sources.

Example policy layers:

- operator policy
- fleet policy
- user policy
- regulatory policy

The effective policy becomes:

```
effectivePolicy =
    operatorPolicy
 ∩  fleetPolicy
 ∩  userPolicy
 ∩  regulatoryPolicy
```

The PolicyGrant stores the **resulting effective constraints**.

---

## Relationship to SBA

A **SignedBudgetAuthorization** must always be a subset of the PolicyGrant.

For example:

```
SBA.allowedRails ⊆ PolicyGrant.allowedRails
SBA.allowedAssets ⊆ PolicyGrant.allowedAssets
SBA.maxAmount ≤ PolicyGrant.maxSpend
```

The SBA must reference the same **policyHash** used to produce the PolicyGrant.

---

## Relationship to SPA

A **SignedPaymentAuthorization** must ultimately derive from a policy decision that was allowed by the PolicyGrant.

Therefore:

```
SPA.rail ∈ PolicyGrant.allowedRails
SPA.asset ∈ PolicyGrant.allowedAssets
SPA.amount ≤ PolicyGrant.maxSpend
```

---

## Expiration

PolicyGrant defines the **maximum validity window** for downstream artifacts.

Implementations MUST ensure:

- SBA expiration does not exceed PolicyGrant expiration
- SPA expiration does not exceed PolicyGrant expiration

---

## Signing

PolicyGrant MUST be cryptographically signed. The policy authority signs the grant; verifiers resolve `policyAuthorityPublicKey` using `issuer` and `issuerKeyId` (from configuration, DID resolution, or a registry).

The signed payload is the canonical JSON of all grant fields except `signature`:

```
hash = SHA256("MPCP:PolicyGrant:<version>:" || canonicalJson(grantPayload))
signature = sign(hash, policyAuthorityPrivateKey)
```

If signature verification fails, the verifier MUST reject the grant.

---

## Summary

PolicyGrant establishes the **policy boundary** for machine payments.

It ensures that downstream artifacts (SBA and SPA) are always derived from a **validated policy evaluation**.

---

## See Also

- [MPCP Reference Flow — EV Charging](../architecture/reference-flow.md) — Demonstrates how PolicyGrant is used during runtime authorization.
