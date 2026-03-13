# Fleet EV Charging — MPCP Reference Flow

This document describes a **complete end‑to‑end reference scenario** for using the Machine Payment Control Protocol (MPCP) in an autonomous EV fleet charging environment.

**Chain overview:** [Authorization Chain](authorization-chain.md) — the canonical visual diagram.

The goal is to illustrate:

- who the actors are
- which MPCP artifacts are issued
- when each artifact is created
- where artifacts are stored
- how verification occurs
- how settlement is executed

This scenario is intended as a **reference implementation narrative** for developers, integrators, and auditors.

---

# Actors

See: [Actors](actors.md) for a standalone overview.

## Fleet Operator

The fleet operator owns and manages the autonomous EV fleet.

Responsibilities:

- defines vehicle payment policies
- sets spending limits
- restricts allowed vendors and locations
- issues PolicyGrant artifacts

Examples:

- robotaxi fleet
- delivery fleet
- autonomous logistics fleet

In this reference flow, the fleet operator is identified by an **XRPL DID** and issues fleet charging policy credentials signed under that DID.

## Identity & Credential Layer

This scenario assumes an optional **identity and credential layer** based on:

- XRPL DID
- Verifiable Credentials (VCs)

In this model:

- the fleet operator has a DID
- the charging network operator has a DID
- the vehicle wallet may have its own DID
- selected MPCP policy artifacts may be issued as VCs

MPCP remains the **runtime payment authorization protocol**.

DIDs and VCs provide:

- issuer identity
- public key discovery
- portable trust metadata
- credential verification across organizations

They do **not** replace MPCP artifacts such as `SignedBudgetAuthorization`, `SignedPaymentAuthorization`, or `SettlementIntent`.

## Vehicle Wallet

Each EV contains a **machine wallet** responsible for:

- enforcing MPCP policy constraints
- managing charging budgets
- issuing payment authorization artifacts
- executing settlement transactions

The wallet is the MPCP actor that signs:

- SignedBudgetAuthorization (SBA)
- SignedPaymentAuthorization (SPA)

---

## Route / Dispatch System

The dispatch system determines the route and charging requirements.

Responsibilities:

- determine charging locations along route
- identify approved charging networks
- provide trip metadata to the vehicle

This system may influence the **PolicyGrant** constraints.

---

## Charging Network Operator

The charging network operator manages a network of EV charging stations.

Responsibilities:

- provide price quotes
- specify settlement destination
- verify MPCP authorization artifacts
- allow or deny charging sessions

In this reference flow, the charging network operator may also publish an **XRPL DID** and issue verifiable credentials describing approved station identity, operator identity, and payment endpoints.

---

## Charging Station

The physical charger interacting with the EV.

Responsibilities:

- request payment authorization
- verify MPCP artifact chain
- begin charging once verification passes

---

## Settlement Rail

The settlement layer executes the payment.

Examples:

- XRPL + RLUSD
- stablecoin rails
- blockchain settlement systems
- traditional payment networks

MPCP does not replace settlement systems.

It **controls authorization above them**.

---

## MPCP Verifier

The verifier checks the full authorization chain.

Verification may occur:

- inside the charging operator backend
- inside a dedicated MPCP verification service
- during post‑transaction auditing

---

# Fleet Charging Policy

Before vehicles begin operating, the fleet operator defines a charging policy.

Example constraints:

```
Allowed vendors:
    ChargeNet
    FastVolt

Allowed geography:
    Stations along active route

Allowed settlement rail:
    XRPL

Allowed asset:
    RLUSD

Daily charging limit:
    $80

Maximum single session:
    $25

Allowed charging hours:
    06:00–23:00 UTC
```

This policy is translated into a **PolicyGrant** artifact.

In this DID/VC-enabled version of the flow, the PolicyGrant is issued as an MPCP-native policy artifact that may also be wrapped or represented as a **Verifiable Credential**.

This allows the EV wallet and charging infrastructure to verify:

- who issued the policy
- which public key is authoritative
- whether the credential is still valid

---

# MPCP Artifacts Used in This Scenario

The EV charging flow uses the following MPCP artifacts.

| Artifact | Issued By | Purpose |
|--------|--------|--------|
| PolicyGrant | Fleet policy service | Defines global payment constraints |
| PolicyGrant VC (optional) | Fleet policy service | Encodes issuer identity and verifiable policy metadata |
| SignedBudgetAuthorization | Vehicle wallet | Defines session‑level spending limits |
| SignedPaymentAuthorization | Vehicle wallet | Authorizes a specific payment |
| SettlementIntent | Vehicle wallet | Defines settlement parameters |
| Settlement Result | Settlement rail | Confirms payment execution |


These artifacts form the **authorization chain**.

---

# High‑Level Sequence Diagram

The following diagram summarizes the **runtime interaction flow** between the EV, charging station, and settlement rail.

```
Fleet Policy Service
        │
        │ 1. Issue PolicyGrant (signed)
        ▼
Vehicle Wallet
        │
        │ 2. Store PolicyGrant
        │
        │ 3. Request quote
        ▼
Charging Station
        │
        │ 4. Provide charging quote
        ▼
Vehicle Wallet
        │
        │ 5. Validate policy
        │ 6. Create SignedBudgetAuthorization
        │ 7. Create SettlementIntent
        │ 8. Create SignedPaymentAuthorization
        ▼
Charging Station / Operator Backend
        │
        │ 9. Verify MPCP artifact chain
        │
        │   - resolve issuer DID
        │   - verify PolicyGrant
        │   - verify SignedBudgetAuthorization
        │   - verify SPA
        │
        ▼
Charging Station
        │
        │ 10. Begin charging session
        ▼
Settlement Rail
        │
        │ 11. Execute payment
        ▼
Charging Operator Backend
        │
        │ 12. Store audit bundle
```

This diagram highlights the **separation of roles**:

- fleet policy authority
- vehicle runtime authorization
- charging infrastructure verification
- settlement execution

---

# Artifact Storage Matrix

The following table summarizes **where each artifact typically resides**.

| Artifact | Fleet Backend | Vehicle Wallet | Charging Operator | Settlement Rail |
|---|---|---|---|---|
| PolicyGrant | Authoritative copy | Operational copy | Optional reference | — |
| PolicyGrant VC | Optional | Optional | Optional | — |
| SignedBudgetAuthorization | Optional audit | Active session artifact | Received during authorization | — |
| SignedPaymentAuthorization | Optional audit | Created and signed | Received and verified | — |
| SettlementIntent | Optional audit | Runtime artifact | Optional (for verification) | — |
| Settlement Result | Reconciliation | Stored receipt | Stored receipt | Authoritative record |

This matrix helps implementers understand **where artifacts should be persisted and where they are transient**.

---

# Artifact Lifecycle

## PolicyGrant

Issued by:

```
Fleet Policy Service (identified by XRPL DID)
```

Contains:

- allowed rails
- allowed assets
- vendor restrictions
- expiration time
- policy hash

Stored by:

- fleet backend
- vehicle wallet
- audit systems

The PolicyGrant is typically issued:

```
Before vehicle deployment
or
Before a trip session
```

### PolicyGrant Storage and Signature Model

A PolicyGrant is a **signed JSON authorization artifact** issued by the fleet operator's policy service.

It is **not an NFT and does not require a blockchain token**. MPCP treats the PolicyGrant as a verifiable authorization credential that can be validated using the fleet operator's public key.

In this reference flow, the fleet operator is identified by an **XRPL DID**.

Example issuer:

```
issuer: did:xrpl:rFleetOperator...
issuerKeyId: did:xrpl:rFleetOperator...#key-1
```

The EV wallet resolves the fleet DID to obtain the current public verification key.

Verification model:

```
resolve DID
↓
get issuer public key
↓
verify signature on PolicyGrant
```

This allows the EV wallet to confirm that the policy was issued by an authorized fleet authority.

Example structure:

```
{
  "artifact": "PolicyGrant",
  "version": "1.0",
  "grantId": "pg-983745",
  "issuer": "did:xrpl:rFleetOperator...",
  "issuerKeyId": "did:xrpl:rFleetOperator...#key-1",
  "allowedRails": ["xrpl"],
  "allowedAssets": [
    { "symbol": "RLUSD", "namespace": "rIssuer" }
  ],
  "vendorAllowlist": ["ChargeNet","FastVolt"],
  "capPerSessionMinor": "2500",
  "capPerDayMinor": "8000",
  "expiresAt": "2026-03-13T23:59:00Z",
  "policyHash": "abc123...",
  "signature": "ed25519:..."
}
```

A VC representation may also be used for issuer portability.

Example conceptual VC envelope:

```
{
  "@context": ["https://www.w3.org/2018/credentials/v1"],
  "type": ["VerifiableCredential", "MPCPPolicyGrant"],
  "issuer": "did:xrpl:rFleetOperator...",
  "issuanceDate": "2026-03-12T00:00:00Z",
  "expirationDate": "2026-03-13T23:59:00Z",
  "credentialSubject": {
    "vehicleId": "EV-847",
    "policyHash": "abc123...",
    "allowedRails": ["xrpl"],
    "vendorAllowlist": ["ChargeNet","FastVolt"],
    "capPerSessionMinor": "2500"
  },
  "proof": {
    "type": "Ed25519Signature2020",
    "verificationMethod": "did:xrpl:rFleetOperator...#key-1",
    "signature": "..."
  }
}
```

In this model, the **MPCP artifact remains canonical**, while the VC representation provides an optional identity and trust envelope.

### Where the PolicyGrant Lives

In a typical deployment the PolicyGrant exists in **three locations**:

1. **Fleet Backend (authoritative copy)**  
   Stored in the fleet operator's policy service database for auditing, policy management, and revocation tracking.

2. **Vehicle Wallet (operational copy)**  
   Stored locally in the EV wallet so the vehicle can enforce payment constraints while offline.

3. **Payment Authorization Bundle (optional)**  
   During charging authorization the EV may transmit either:
   - the full PolicyGrant, or
   - the `policyHash` reference

   allowing the charging operator to verify that the payment authorization follows the fleet policy.

If a VC form is used, the vehicle may store both:

- the canonical MPCP `PolicyGrant`
- the VC envelope containing issuer DID metadata

The runtime authorization logic should continue to use the MPCP-native artifact fields.

Example vehicle wallet storage model:

```
EV Wallet
 ├─ keys
 ├─ budgets
 ├─ paymentAuthorizations
 └─ policyGrants
       └─ grantId
           policyHash
           expiresAt
           issuer
           signature
```

The PolicyGrant can be stored in a lightweight embedded database such as:

- SQLite
- LevelDB
- secure key-value store
- encrypted filesystem

### Optional Ledger Anchoring

Some deployments may choose to anchor the `policyHash` on a public ledger for audit purposes.

Examples:

- XRPL memo
- Hedera Consensus Service
- Ethereum event log

Only the **hash of the policy** would be anchored, not the full artifact.

This provides:

- timestamped audit proofs
- dispute resolution evidence
- tamper-detection guarantees

However, anchoring is **optional** and not required for MPCP operation.

---

## SignedBudgetAuthorization

Issued by:

```
Vehicle Wallet
```

Purpose:

Define the maximum spend allowed for a session and bind that budget to permitted payment rails, assets, and destinations.

Example:

```
sessionId: charging-session-847
maxAmountMinor: 2500
currency: USD
allowedDestination:
    ChargeNet
expiresAt: session end
```

Stored by:

- vehicle wallet
- charging session bundle
- fleet audit system

---

## SettlementIntent

Issued by:

```
Vehicle Wallet
```

Created after the charging station provides a quote.

Contains:

- rail
- asset
- destination
- amount
- optional connector metadata

SettlementIntent may produce an **intentHash** used in the SPA.

The SettlementIntent remains an MPCP-native runtime artifact and is **not typically modeled as a Verifiable Credential**, because it is ephemeral and optimized for deterministic hashing and lightweight transport.

---

## SignedPaymentAuthorization (SPA)

Issued by:

```
Vehicle Wallet
```

Purpose:

Authorize a specific payment request.

Contains:

- session reference
- settlement parameters
- optional intentHash
- decision ID
- signature

Stored by:

- vehicle wallet
- charging network backend
- audit logs

The SPA is also an MPCP-native runtime artifact and is usually verified directly against the vehicle wallet's signing key rather than wrapped as a VC.

---

## Settlement Result

Issued by:

```
Settlement Rail
```

Examples:

- XRPL transaction
- stablecoin transfer
- payment processor receipt

Contains:

- transaction reference
- amount
- destination
- timestamp

---

# End‑to‑End Charging Timeline

## T‑24h — Fleet Policy Definition

Fleet operator defines charging policy.

The policy is converted into a **PolicyGrant**.

PolicyGrant is distributed to vehicles.

---

## T‑5m — Trip Session Begins

Vehicle receives:

- active route
- approved charging stations
- remaining daily charging budget

Vehicle prepares to issue a **SignedBudgetAuthorization** if needed.

---

## T0 — Vehicle Arrives at Charging Station

The EV connects to the charger.

Charging station sends a **payment quote**.

Example:

```
Charging estimate: $7.80
Destination: ChargeNet operator account
Quote expiry: 5 minutes
```

---

## T+10s — Vehicle Policy Validation

Vehicle checks:

- station operator is allowed vendor
- destination is allowed
- settlement rail is allowed
- asset is allowed
- amount fits session budget
- amount fits daily limit
- fleet issuer DID resolves correctly
- policy credential signature verifies successfully

---

## T+15s — Budget Authorization

Vehicle creates or loads an active **SignedBudgetAuthorization**.

Example:

```
maxAmount: $25
session: charging-session-847
```

---

## T+20s — Settlement Intent

Vehicle constructs a **SettlementIntent**:

```
rail: XRPL
asset: RLUSD
amount: 7.80
destination: ChargeNet account
```

An **intentHash** may be generated.

---

## T+22s — Payment Authorization

Vehicle signs a **SignedPaymentAuthorization**.

This authorization binds:

- session ID
- settlement parameters
- optional intent hash

---

## T+25s — Authorization Sent to Charger

The charger receives:

- SignedPaymentAuthorization
- SignedBudgetAuthorization
- PolicyGrant (or reference)
- SettlementIntent (optional)

---

## T+27s — Charger Verification

Charging network verifies:

1. fleet issuer DID resolves correctly
2. PolicyGrant or PolicyGrant VC is valid
3. SignedBudgetAuthorization is valid
4. SPA signature is valid
5. SPA parameters match the quote
6. settlement parameters match allowed policy

If verification passes:

```
Charging session begins
```

---

## T+N minutes — Charging Session

Energy delivery occurs.

Payment may be:

- pre‑authorized
- settled immediately
- settled at session end

---

## T+Session End — Settlement

Settlement occurs.

Example:

```
XRPL payment
vehicle_wallet → ChargeNet account
```

Settlement result is stored.

---

# Data Storage Model

## Fleet Backend Stores

- fleet charging policies
- PolicyGrant history
- SignedBudgetAuthorization records
- vehicle charging audit logs
- reconciliation records

---

## Vehicle Wallet Stores

- active PolicyGrant
- active SignedBudgetAuthorization
- SettlementIntent
- SignedPaymentAuthorization
- settlement receipts

---

## Charging Operator Stores

- payment quote
- MPCP artifact bundle
- optional PolicyGrant VC / issuer DID metadata
- verification results
- settlement reference
- charging session logs

---

# Verification Points

Verification happens in several places.

## Trust Model and DID Resolution

When XRPL DID integration is used, MPCP verification includes **issuer identity validation**.

Typical resolution process:

```
PolicyGrant issuer DID
      ↓
DID resolver
      ↓
XRPL DID document
      ↓
public verification keys
```

The verifier then confirms:

- the DID document is valid
- the referenced verification key exists
- the PolicyGrant signature matches that key

This allows the charging operator to confirm that:

- the fleet operator actually issued the policy
- the authorization chain originates from a trusted authority

If DID resolution fails, the charging operator should treat the PolicyGrant as **untrusted** and reject the authorization.

## Vehicle Verification

Before authorizing payment:

- vendor allowed
- station allowed
- destination allowed
- budget sufficient
- quote valid

---

## Charging Operator Verification

Before charging begins:

- issuer DID resolves and credential proof is valid
- PolicyGrant valid
- SignedBudgetAuthorization valid
- SPA signature valid
- payment parameters match quote
- authorization not expired

---

## Fleet Reconciliation Verification

After settlement:

- settlement matches authorization
- station vendor allowed
- policy constraints respected
- budgets not exceeded

---

# Failure Scenarios

## Vendor Not Allowed

Vehicle refuses to authorize payment.

---

## Quote Exceeds Budget

Vehicle rejects charging request.

---

## Destination Mismatch

Charging operator rejects authorization.

---

## Settlement Mismatch

Verifier flags payment as invalid.

---

# Audit Bundle

For audit or dispute resolution, the following bundle may be stored:

- PolicyGrant
- optional PolicyGrant VC
- issuer DID metadata or resolution record
- SignedBudgetAuthorization
- SignedPaymentAuthorization
- SettlementIntent
- charging quote metadata
- settlement receipt
- optional intent anchor

This bundle allows full replay of the authorization chain.

---

# Full Artifact Bundle Example

The following example shows the kind of **self-contained authorization bundle** a charging operator could receive and store for verification, audit, or dispute replay.

This example is intentionally simplified, but it illustrates how the full MPCP chain may be packaged.

> Note: The example below uses display-friendly amounts (e.g., "7.80") for readability.  
> Real MPCP artifacts typically encode amounts in atomic units.

```json
{
  "bundleType": "MPCPChargingAuthorizationBundle",
  "version": "1.0",

  "issuerDid": "did:xrpl:rFleetOperator...",
  "vehicleDid": "did:xrpl:rVehicleWallet...",
  "chargingOperatorDid": "did:xrpl:rChargeNet...",

  "policyGrant": {
    "artifact": "PolicyGrant",
    "version": "1.0",
    "grantId": "pg-983745",
    "issuer": "did:xrpl:rFleetOperator...",
    "issuerKeyId": "did:xrpl:rFleetOperator...#key-1",
    "allowedRails": ["xrpl"],
    "allowedAssets": [
      { "symbol": "RLUSD", "namespace": "rIssuer" }
    ],
    "vendorAllowlist": ["ChargeNet", "FastVolt"],
    "capPerSessionMinor": "2500",
    "capPerDayMinor": "8000",
    "expiresAt": "2026-03-13T23:59:00Z",
    "policyHash": "abc123...",
    "signature": "ed25519:..."
  },

  "policyGrantVc": {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "type": ["VerifiableCredential", "MPCPPolicyGrant"],
    "issuer": "did:xrpl:rFleetOperator...",
    "issuanceDate": "2026-03-12T00:00:00Z",
    "expirationDate": "2026-03-13T23:59:00Z",
    "credentialSubject": {
      "vehicleId": "EV-847",
      "policyHash": "abc123...",
      "allowedRails": ["xrpl"],
      "vendorAllowlist": ["ChargeNet", "FastVolt"],
      "capPerSessionMinor": "2500"
    },
    "proof": {
      "type": "Ed25519Signature2020",
      "verificationMethod": "did:xrpl:rFleetOperator...#key-1",
      "signature": "..."
    }
  },

  "signedBudgetAuthorization": {
    "artifact": "SignedBudgetAuthorization",
    "issuer": "did:xrpl:rVehicleWallet...",
    "issuerKeyId": "did:xrpl:rVehicleWallet...#key-1",
    "version": "1.0",
    "sessionId": "charging-session-847",
    "vehicleId": "EV-847",
    "policyHash": "abc123...",
    "currency": "USD",
    "maxAmountMinor": "2500",
    "allowedRails": ["xrpl"],
    "allowedAssets": [
      { "symbol": "RLUSD", "namespace": "rIssuer" }
    ],
    "destinationAllowlist": ["rChargeNetDestination"],
    "expiresAt": "2026-03-12T15:00:00Z",
    "signature": "ed25519:..."
  },

  "chargingQuote": {
    "quoteId": "quote-4421",
    "stationId": "station-17",
    "operator": "ChargeNet",
    "connectorId": "DC-FAST-2",
    "destination": "rChargeNetDestination",
    "asset": { "symbol": "RLUSD", "namespace": "rIssuer" },
    "priceFiat": {
      "amountMinor": "780",
      "currency": "USD"
    },
    "expiresAt": "2026-03-12T14:35:00Z"
  },

  "settlementIntent": {
    "artifact": "SettlementIntent",
    "version": "1.0",
    "rail": "xrpl",
    "amount": "7.80",
    "destination": "rChargeNetDestination",
    "asset": { "symbol": "RLUSD", "namespace": "rIssuer" },
    "createdAt": "2026-03-12T14:30:20Z"
  },

  "signedPaymentAuthorization": {
    "artifact": "SignedPaymentAuthorization",
    "issuer": "did:xrpl:rVehicleWallet...",
    "issuerKeyId": "did:xrpl:rVehicleWallet...#key-1",
    "version": "1.0",
    "sessionId": "charging-session-847",
    "decisionId": "dec-9001",
    "intentHash": "intenthash123...",
    "settlement": {
      "rail": "xrpl",
      "destination": "rChargeNetDestination",
      "amount": "7.80",
      "asset": { "symbol": "RLUSD", "namespace": "rIssuer" }
    },
    "signature": "ed25519:..."
  },

  "settlementResult": {
    "rail": "xrpl",
    "txHash": "ABCDEF123456...",
    "amount": "7.80",
    "destination": "rChargeNetDestination",
    "asset": { "symbol": "RLUSD", "namespace": "rIssuer" },
    "nowISO": "2026-03-12T14:31:10Z"
  },

  "intentAnchor": {
    "rail": "hedera-hcs",
    "topicId": "0.0.123456",
    "sequenceNumber": "88",
    "intentHash": "intenthash123...",
    "anchoredAt": "2026-03-12T14:30:25Z"
  },

  "verificationMaterial": {
    "fleetDidResolution": {
      "did": "did:xrpl:rFleetOperator...",
      "resolvedAt": "2026-03-12T14:30:21Z",
      "verificationMethod": "did:xrpl:rFleetOperator...#key-1"
    },
    "chargingOperatorDidResolution": {
      "did": "did:xrpl:rChargeNet...",
      "resolvedAt": "2026-03-12T14:30:23Z",
      "verificationMethod": "did:xrpl:rChargeNet...#key-1"
    },
    "vehicleDidResolution": {
      "did": "did:xrpl:rVehicleWallet...",
      "resolvedAt": "2026-03-12T14:30:22Z",
      "verificationMethod": "did:xrpl:rVehicleWallet...#key-1"
    }
  }
}
```

## Notes on the Example Bundle

This bundle illustrates several important modeling choices:

- the **canonical MPCP artifacts** remain the primary runtime objects
- the `policyGrantVc` is optional and exists to carry issuer identity and trust metadata
- DID resolution metadata for the fleet issuer, vehicle wallet, and charging operator may be stored alongside the bundle to support later audit or dispute replay
- the `chargingQuote` is not itself an MPCP artifact, but it is operationally important because the charging operator must verify that the SPA matches the quote
- the `intentAnchor` is optional and provides additional auditability without changing the core MPCP authorization chain

In a production deployment, the exact bundle shape may vary, but it should preserve the same key property:

**a verifier must be able to reconstruct and validate the full authorization chain from policy issuance to settlement.**

# Summary

This scenario demonstrates how MPCP enables **safe autonomous charging payments**.

In this version of the flow, MPCP authorization can be anchored in a portable trust model using **XRPL DID** and optional **Verifiable Credentials**, while keeping runtime payment control artifacts lightweight and MPCP-native.

Infrastructure can answer the critical question:

```
Was this vehicle actually allowed to make this payment?
```

MPCP provides the cryptographic proof required to answer that question.
