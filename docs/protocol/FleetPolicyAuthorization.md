# Fleet Policy Authorization (FPA)

Artifact Type: MPCP:FPA

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

---

# 1. Purpose

Fleet Policy Authorization (FPA) introduces **fleet‑side policy authority** into MPCP.

While MPCP already defines operator-issued controls such as:

- PolicyGrant
- SignedBudgetAuthorization (SBA)

large autonomous fleets require **their own governance layer** over machine payments.

Examples:

- robotaxi fleets (Waymo, Tesla, Uber AV)
- delivery fleets
- logistics robots
- autonomous trucking

Fleet operators must ensure that vehicles only spend funds **within fleet‑defined risk and compliance boundaries**.

FPA enables this capability by allowing fleets to issue **signed policy artifacts** that constrain all MPCP spending decisions.

---

# 2. Problem Statement

Without fleet authority, payment policy is controlled solely by service operators:

```
Operator Policy
      ↓
PolicyGrant
      ↓
SBA → Trust Gateway → XRPL Settlement
```

This model is insufficient for enterprise fleets because:

- fleets must enforce **spending limits**
- fleets must enforce **vendor allowlists**
- fleets must enforce **geographic restrictions**
- fleets must enforce **rail/asset restrictions**
- fleets must retain **audit control**

FPA introduces a **fleet policy layer** that intersects with operator policy.

---

# 3. Policy Intersection Model

Under FPA, the effective payment policy is the **intersection of fleet policy and operator policy**.

```
Fleet Policy (FPA)
        ∩
Operator Policy (PolicyGrant)
        ↓
Effective Grant
        ↓
SBA → Trust Gateway → XRPL Settlement
```

Rules:

- **Lowest cap wins**
- **Allowed rails intersect**
- **Allowed assets intersect**
- **Operator must be fleet-approved**
- **Geographic restrictions must satisfy both sides**

This ensures that both the service provider and the fleet operator maintain governance.

---

# 4. FleetPolicyAuthorization Artifact

The FleetPolicyAuthorization artifact is issued and signed by the **fleet authority**.

Example:

```json
{
  "authorization": {
    "version": "1.0",
    "fleetPolicyId": "fp_123",
    "fleetId": "fleet_waymo_sf",
    "actorId": "veh_456",
    "scope": "DAY",
    "currency": "USD",
    "minorUnit": 2,
    "maxAmountMinor": "50000000",
    "allowedRails": ["xrpl"],
    "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." }],
    "allowedOperators": ["operator_42", "operator_77"],
    "geoFence": ["sf_zone_a"],
    "expiresAt": "2026-03-09T23:59:59Z"
  },
  "signature": "base64(signature)",
  "keyId": "fleet-signing-key-1"
}
```

Fields:

| Field | Description |
|------|-------------|
| version | MPCP semantic version |
| fleetPolicyId | unique identifier |
| fleetId | issuing fleet |
| actorId | actor identifier |
| scope | SESSION / DAY / SHIFT |
| currency | reference currency |
| minorUnit | decimal scale |
| maxAmountMinor | maximum spend allowed |
| allowedRails | permitted payment rails |
| allowedAssets | permitted payment assets — array of structured `Asset` objects; see [Asset type](./mpcp.md#asset) |
| allowedOperators | service operators allowed |
| geoFence | optional geographic restrictions |
| expiresAt | expiration timestamp |

FleetPolicyAuthorization uses the MPCP signed envelope pattern.
The signature protects the inner `authorization` payload.

---

## Signature Model

FleetPolicyAuthorization signatures use MPCP domain‑separated hashing.

```
hash = SHA256(
  "MPCP:FPA:1.0:" || canonicalJson(authorization)
)
```

The fleet authority signs the hash using its signing key.

This ensures the artifact cannot collide with other MPCP artifacts.

---

# 5. Effective Policy Computation

When an MPCP verifier processes a transaction, it computes the **effective policy**.

Example pseudocode:

```
effectiveRails = intersect(FPA.allowedRails, PolicyGrant.allowedRails)

 effectiveAssets = intersect(FPA.allowedAssets, PolicyGrant.allowedAssets)

 effectiveCap = min(FPA.maxAmountMinor, PolicyGrant.maxSpend)

 operatorAllowed = PolicyGrant.operatorId in FPA.allowedOperators
```

If any constraint fails, the settlement must be rejected.

---

# 6. Verification Rules

The verifier must check:

1. **FPA signature validity**
2. **FPA expiration**
3. **actorId consistency**
4. **operator allowlist compliance**
5. **rail compatibility**
6. **asset compatibility**
7. **spending cap compliance**

Then proceed with standard MPCP verification:

```
FPA
 ↓
PolicyGrant
 ↓
SBA → Trust Gateway → XRPL Settlement
```

---

# 7. Security Properties

FPA introduces several important security guarantees:

### Fleet Governance

Fleet operators can enforce payment policy independent of vendors.

### Delegated Autonomy

Vehicles can autonomously pay while still operating under fleet risk limits.

### Vendor Neutrality

The same fleet policy can apply across:

- parking
- charging
- tolling
- depot access
- logistics infrastructure

### Auditability

Fleet operators can later prove:

- that a payment was allowed
- that it remained within fleet limits
- that operator policies were respected.

---

# 8. Relationship to MPCP Artifacts

FPA sits **above PolicyGrant** in the MPCP lineage model.

```
FleetPolicyAuthorization (FPA)
        ↓
PolicyGrant
        ↓
SignedBudgetAuthorization (SBA)
        ↓
Trust Gateway
        ↓
XRPL Settlement
```

Each artifact must remain compliant with the constraints of the artifacts above it.

---

# 9. Enterprise Use Cases

### Robotaxi Fleets

Robotaxis may only spend:

- within a city
- at approved charging stations
- within a daily spending envelope.

### Delivery Fleets

Delivery robots may pay for:

- micro‑parking
- depot access
- loading dock reservations.

### Autonomous Trucking

Trucks may pay for:

- toll roads
- charging stations
- logistics hubs.

---

# 10. Future Extensions

Possible enhancements include:

- multi‑fleet policy federation
- regional fleet authorities
- zero‑knowledge fleet policy proofs
- on‑chain policy anchors
- delegated policy keys

---

# 11. Summary

FleetPolicyAuthorization introduces **enterprise fleet governance** into MPCP.

It allows fleets to maintain policy authority over autonomous machine payments while preserving interoperability with MPCP service providers.

This extension enables MPCP to support **large-scale autonomous fleets and agent economies**.
