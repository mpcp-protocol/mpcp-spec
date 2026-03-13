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

In this reference flow, the fleet operator issues signed PolicyGrant artifacts. Optionally, the fleet operator may be identified by an **XRPL DID** for portable issuer identity.

## Identity & Credential Layer

This scenario optionally uses an **identity and credential layer** for issuer key discovery.

The **baseline key resolution mechanism** is HTTPS well-known:

```
https://{issuerDomain}/.well-known/mpcp-keys.json
```

This allows any MPCP verifier to look up the issuer's public key using a stable HTTPS URL without any dependency on DID infrastructure.

An optional **DID/VC layer** may supplement this in deployments that require:

- portable issuer identity across organizations
- verifiable credential metadata
- decentralized key discovery via XRPL DID or similar

DIDs and VCs do **not** replace MPCP artifacts such as `SignedBudgetAuthorization`, `SignedPaymentAuthorization`, or `SettlementIntent`.

MPCP remains the **runtime payment authorization protocol** regardless of which key resolution method is used.

## Vehicle Wallet

Each EV contains a **machine wallet** responsible for:

- enforcing MPCP policy constraints
- managing charging budgets
- issuing payment authorization artifacts
- executing settlement transactions

The wallet is the MPCP actor that signs:

- SignedBudgetAuthorization (SBA)
- SignedPaymentAuthorization (SPA)

In this autonomous deployment model, the vehicle wallet **embeds both the session authority and the payment decision service roles**:

- **session authority**: creates and signs the SBA, defining the session-level budget and permitted destinations
- **payment decision service**: evaluates each quote against the policy, assigns a `decisionId`, and signs the SPA

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

- request payment authorization from the vehicle
- relay the authorization bundle to the operator backend
- begin energy delivery once the operator backend confirms verification

Note: MPCP artifact verification is performed by the **Charging Operator Backend**, not the physical station. The station acts as a relay and executes the outcome (begin or deny charging) based on the backend's decision.

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

The PolicyGrant is issued as an MPCP-native policy artifact. In deployments using the optional DID/VC layer, it may also be wrapped or represented as a **Verifiable Credential**.

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
| SignedBudgetAuthorization | Vehicle wallet (session authority role) | Defines session‑level spending limits |
| SignedPaymentAuthorization | Vehicle wallet (payment decision service role) | Authorizes a specific payment |
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
        │ 8. Apply payment decision logic
        │    Create SignedPaymentAuthorization
        ▼
Charging Operator Backend
        │
        │ 9. Verify MPCP artifact chain
        │
        │   - resolve issuer public keys
        │     (HTTPS well-known or DID)
        │   - verify PolicyGrant
        │   - verify SignedBudgetAuthorization
        │   - verify SPA
        │
        ▼
Charging Station
        │
        │ 10. Begin energy delivery
        ▼
Vehicle Wallet
        │
        │ 11. Submit payment to XRPL / settlement rail
        ▼
Charging Operator Backend
        │
        │ 12. Verify settlement tx
        │     Bind tx to decisionId
        │     Mark authorization consumed
        │     Store audit bundle
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
Fleet Policy Service
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

Example issuer key identifiers:

```
issuer: fleet-operator.example.com          (baseline: HTTPS well-known)
issuerKeyId: fleet-policy-key-1

-- or with DID (optional) --

issuer: did:xrpl:rFleetOperator...
issuerKeyId: did:xrpl:rFleetOperator...#key-1
```

The EV wallet resolves the public verification key using the baseline HTTPS well-known endpoint, or optionally via DID resolution.

Verification model:

```
resolve issuerKeyId
↓ (via HTTPS well-known or DID)
get issuer public key
↓
verify signature on PolicyGrant
```

This allows the EV wallet to confirm that the policy was issued by an authorized fleet authority.

Example `PolicyGrant` structure:

```json
{
  "grantId": "pg-983745",
  "policyHash": "abc123...",
  "allowedRails": ["xrpl"],
  "allowedAssets": [
    { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" }
  ],
  "expiresAt": "2026-03-13T23:59:00Z"
}
```

The `issuer`, `issuerKeyId`, and `signature` fields belong to the **signed envelope** that wraps the grant payload, not the grant itself.

A VC representation may also be used for issuer portability in DID/VC-enabled deployments.

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
- policy issuer public key resolves (via HTTPS well-known, or DID if configured)
- PolicyGrant signature verifies successfully

---

## T+15s — Budget Authorization

The vehicle wallet **creates** a fresh `SignedBudgetAuthorization` for this session (or **loads** an existing one if this session is already active).

Example:

```
maxAmountMinor: 2500   (USD, minor units)
budgetScope: SESSION
session: charging-session-847
grantId: pg-983745
```

---

## T+20s — Settlement Intent

Vehicle constructs a **SettlementIntent**:

```
rail: XRPL
asset: RLUSD
amount: 780000   (atomic units, 6 decimal places = 0.78 RLUSD)
destination: ChargeNet account
```

An **intentHash** may be generated.

---

## T+22s — Payment Decision and Authorization

The vehicle wallet's payment decision logic evaluates the quote:

- confirms the destination is on the SBA `destinationAllowlist`
- confirms the amount fits within the session budget
- assigns a `decisionId` and links it to the `quoteId`

The wallet then signs a **SignedPaymentAuthorization** (SPA) binding:

- `decisionId` and `quoteId`
- session ID and budget ID
- settlement parameters (rail, asset, amount, destination)
- optional `intentHash` (SHA-256 of the SettlementIntent)

---

## T+25s — Authorization Sent to Charger

The charger receives:

- SignedPaymentAuthorization
- SignedBudgetAuthorization
- PolicyGrant (or reference)
- SettlementIntent (optional)

---

## T+27s — Charging Operator Verification

The **charging operator backend** verifies:

1. issuer public key resolves (via HTTPS well-known, or DID if configured)
2. PolicyGrant is valid and not expired
3. SignedBudgetAuthorization signature and constraints are valid
4. SPA signature is valid
5. SPA parameters match the quote
6. settlement parameters match the allowed policy

If verification passes, the backend signals the physical charging station to begin.

---

## T+30s — Energy Delivery Begins

The charging station begins delivering energy to the vehicle.

The payment is pre-authorized and will be settled at session end.

---

## T+N minutes — Charging Session

Energy delivery occurs.

Payment may be:

- pre‑authorized
- settled immediately
- settled at session end

---

## T+Session End — Settlement

Vehicle wallet submits payment to the settlement rail:

```
XRPL payment
vehicle_wallet → ChargeNet account
```

Charging operator backend then:

- verifies the settlement transaction
- binds the tx to the `decisionId`
- marks the authorization consumed
- stores the audit bundle

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

## Key Resolution and Trust Model

MPCP verifiers must resolve the issuer's public key to verify signed artifacts.

**Baseline mechanism — HTTPS well-known:**

```
https://{issuerDomain}/.well-known/mpcp-keys.json
```

The verifier fetches the key document and looks up the key by `issuerKeyId`.

**Optional — DID resolution:**

```
issuerKeyId (DID URL fragment)
      ↓
DID resolver
      ↓
DID document
      ↓
public verification key
```

When `issuerKeyId` is a DID URL fragment, the verifier may use DID resolution instead of or in addition to HTTPS well-known.

The verifier confirms:

- the signing key matches the `issuerKeyId` declared in the artifact
- the artifact signature is valid under that key

If the key cannot be resolved by any available method, the authorization should be rejected as **unverifiable**.

## Vehicle Verification

Before authorizing payment:

- destination is on the SBA `destinationAllowlist`
- settlement rail and asset are allowed
- amount is within session budget
- quote has not expired
- PolicyGrant signature is valid

---

## Charging Operator Verification

Before charging begins:

- issuer public key resolved and PolicyGrant signature is valid
- PolicyGrant not expired and constraints match
- SignedBudgetAuthorization signature and constraints are valid
- SPA signature valid
- payment parameters match the quote
- authorization not expired

---

## Fleet Reconciliation Verification

After settlement:

- settlement matches authorization
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
- SignedBudgetAuthorization
- SignedPaymentAuthorization
- SettlementIntent
- charging quote metadata
- settlement receipt
- optional intent anchor (ledger hash for tamper-detection)
- optional issuer DID resolution record (when DID/VC layer is used)

This bundle allows full replay of the authorization chain.

---

# Full Artifact Bundle Example

The following example shows the kind of **self-contained authorization bundle** a charging operator could receive and store for verification, audit, or dispute replay.

This example is intentionally simplified, but it illustrates how the full MPCP chain may be packaged.

> Note: Amounts are encoded in atomic units. For example, `"780000"` represents 0.78 RLUSD with 6 decimal places, consistent with XRPL IOU conventions.

```json
{
  "policyGrant": {
    "grantId": "pg-983745",
    "policyHash": "abc123...",
    "allowedRails": ["xrpl"],
    "allowedAssets": [
      { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" }
    ],
    "expiresAt": "2026-03-13T23:59:00Z"
  },

  "sba": {
    "authorization": {
      "version": "1.0",
      "budgetId": "bud-session-847",
      "grantId": "pg-983745",
      "sessionId": "charging-session-847",
      "vehicleId": "EV-847",
      "policyHash": "abc123...",
      "currency": "USD",
      "minorUnit": 2,
      "budgetScope": "SESSION",
      "maxAmountMinor": "2500",
      "allowedRails": ["xrpl"],
      "allowedAssets": [
        { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" }
      ],
      "destinationAllowlist": ["rChargeNetDestination"],
      "expiresAt": "2026-03-12T15:00:00Z"
    },
    "issuerKeyId": "mpcp-sba-signing-key-1",
    "signature": "base64encodedSignature..."
  },

  "chargingQuote": {
    "quoteId": "quote-4421",
    "stationId": "station-17",
    "operator": "ChargeNet",
    "connectorId": "DC-FAST-2",
    "destination": "rChargeNetDestination",
    "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" },
    "amount": { "amount": "780000", "decimals": 6 },
    "priceFiat": { "amountMinor": "780", "currency": "USD" },
    "expiresAt": "2026-03-12T14:35:00Z"
  },

  "settlementIntent": {
    "version": "1.0",
    "rail": "xrpl",
    "amount": "780000",
    "destination": "rChargeNetDestination",
    "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" },
    "createdAt": "2026-03-12T14:30:20Z"
  },

  "spa": {
    "authorization": {
      "version": "1.0",
      "decisionId": "dec-9001",
      "sessionId": "charging-session-847",
      "policyHash": "abc123...",
      "budgetId": "bud-session-847",
      "quoteId": "quote-4421",
      "rail": "xrpl",
      "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" },
      "amount": "780000",
      "destination": "rChargeNetDestination",
      "intentHash": "sha256ofSettlementIntent...",
      "expiresAt": "2026-03-12T14:35:00Z"
    },
    "issuerKeyId": "mpcp-spa-signing-key-1",
    "signature": "base64encodedSignature..."
  },

  "settlement": {
    "rail": "xrpl",
    "amount": "780000",
    "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" },
    "destination": "rChargeNetDestination",
    "nowISO": "2026-03-12T14:31:10Z"
  }
}
```

## Notes on the Example Bundle

This bundle illustrates the canonical MPCP artifact structure:

- `policyGrant` contains only the MPCP-native grant fields (`grantId`, `policyHash`, `allowedRails`, `allowedAssets`, `expiresAt`)
- `sba` uses the signed envelope format: `{ authorization: {...}, issuerKeyId, signature }` — the `authorization` object is what gets hashed and signed
- `spa` uses the same signed envelope format; `authorization.budgetId` links to `sba.authorization.budgetId`; `authorization.grantId` in the SBA links to `policyGrant.grantId`
- `chargingQuote` is not an MPCP artifact but is operationally important — the operator must verify that the SPA `amount` and `destination` match the quote
- amounts are encoded in atomic units (e.g., `"780000"` for 0.78 RLUSD with 6 decimal places)
- `settlement` records what was actually submitted to the settlement rail; the operator verifies it matches the SPA

In a production deployment, the exact bundle shape may vary, but it should preserve the same key property:

**a verifier must be able to reconstruct and validate the full authorization chain from policy issuance to settlement.**

Optional additions (not shown above):
- `issuer` field on `sba` or `spa` envelopes (HTTPS domain or DID for key discovery)
- intent anchor (ledger hash of the `settlementIntent`)
- DID resolution records (when DID/VC layer is used)

# Summary

This scenario demonstrates how MPCP enables **safe autonomous charging payments**.

Runtime payment control artifacts remain lightweight and MPCP-native. Key resolution uses HTTPS well-known as the baseline, with optional DID/VC support for deployments that require portable issuer identity or verifiable credential metadata.

Infrastructure can answer the critical question:

```
Was this vehicle actually allowed to make this payment?
```

MPCP provides the cryptographic proof required to answer that question.
