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
| policyHash | string | yes | SHA-256 hash of the canonical policy document from which this grant was issued. Computed as `SHA256("MPCP:Policy:<version>:" \|\| canonicalJson(policyDocument))`. Downstream artifacts (SBA, SPA) MUST carry the same value. |
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
  "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." }],
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

## Policy Hashing

`policyHash` is the SHA-256 hash of the canonical policy document from which the PolicyGrant was issued.

The policy document is the structured representation of the rules evaluated to produce the grant (operator policy, fleet policy, regulatory constraints, etc.). It MUST be serialized using MPCP canonical JSON before hashing.

Computation:

```
policyHash = SHA256("MPCP:Policy:<version>:" || canonicalJson(policyDocument))
```

Example:

```
policyHash = SHA256("MPCP:Policy:1.0:" || '{"allowedAssets":[...],"allowedRails":[...],...}')
```

The `policyHash` is not a hash of the PolicyGrant artifact itself — it is a hash of the **source policy** that the grant was derived from.

Downstream artifacts (SBA and SPA) MUST carry the same `policyHash`. During settlement verification, the verifier checks that `PolicyGrant.policyHash`, `SBA.policyHash`, and `SPA.policyHash` are all equal, confirming the entire authorization chain derives from the same policy snapshot.

---

## Signing Requirements

PolicyGrant MUST be cryptographically signed by the policy authority. Verifiers that have a public key configured MUST verify the signature and MUST reject unsigned grants.

### Domain Hash

The signed payload uses domain-separated hashing:

```
hash = SHA256("MPCP:PolicyGrant:1.0:" || canonicalJson(grantPayload))
signature = sign(hash, policyAuthorityPrivateKey)
```

where `grantPayload` is all grant fields except `signature`, serialized as canonical JSON.

### Reference Implementation — Environment Variables

The reference implementation (`policyGrant.ts`) exposes signing and verification via environment variables:

| Variable | Purpose |
|----------|---------|
| `MPCP_POLICY_GRANT_SIGNING_PRIVATE_KEY_PEM` | Private key for signing PolicyGrants |
| `MPCP_POLICY_GRANT_SIGNING_PUBLIC_KEY_PEM` | Public key for verifying PolicyGrant signatures. When set, unsigned grants are rejected. |
| `MPCP_POLICY_GRANT_SIGNING_KEY_ID` | Key identifier (default: `mpcp-policy-grant-signing-key-1`) |

Functions:
- `createSignedPolicyGrant(grant)` — signs the grant, returns `SignedPolicyGrant`
- `verifyPolicyGrantSignature(envelope)` — verifies the signature

### Enforcement

If `MPCP_POLICY_GRANT_SIGNING_PUBLIC_KEY_PEM` is set:
- Grants without `issuerKeyId` and `signature` are rejected with `invalid_policy_grant_signature`
- Grants with an invalid signature are rejected with `invalid_policy_grant_signature`

If the env var is not set, signature verification is skipped (backward-compatible mode for environments using pre-validated grants).

If signature verification fails, the verifier MUST reject the grant.

### Key Resolution

Verifiers resolve the public key (as JWK) using `issuer` and `issuerKeyId` via the HTTPS well-known endpoint or pre-configured keys. See [Key Resolution](./key-resolution.md).

---

## Summary

PolicyGrant establishes the **policy boundary** for machine payments.

It ensures that downstream artifacts (SBA and SPA) are always derived from a **validated policy evaluation**.

---

## See Also

- [MPCP Reference Flow — EV Charging](../architecture/reference-flow.md) — Demonstrates how PolicyGrant is used during runtime authorization.
