# MPCP Policy Model

## Overview

The MPCP Policy Model defines how spending and transaction constraints are expressed, enforced, and verified across the protocol.

A policy answers a single fundamental question:

> Under what conditions is a machine allowed to execute a payment?

Policies are authored by a **policy authority** (e.g., fleet operator, enterprise controller) and are materialized into a **PolicyGrant** that can be enforced by machine wallets and verified by vendors.

The Policy Model is intentionally:

- **Deterministic** – all constraints must be verifiable from artifacts
- **Composable** – policies can combine multiple constraint dimensions
- **Extensible** – profiles may add domain-specific constraints

---

## Roles

### Policy Authority (Policy Author)

Entity that **defines and signs** the policy.

Examples:
- **Fleet operator** — defines which vendors a fleet may pay
- Enterprise IT / finance system
- Wallet provider

PolicyAuthority MUST be associated with a verifiable signing key.

Key resolution is defined in the trust layer.

### Vendors

The vendors the machine is allowed to pay.

Examples:
- EV charging networks
- Parking vendors
- Toll vendors
- API providers

### Machine Wallet

Holds PolicyGrant and enforces constraints at execution time.

### Verifier

Validates the payment chain.

---

## Core Policy Dimensions

### 1. Vendor Constraints

Defines **who the machine is allowed to pay**.

Examples:
- allowed vendors (e.g., Ionity, ChargePoint)
- merchant identifiers
- destination allowlists

Vendor constraints MUST ultimately resolve to concrete payment endpoints.

Policies MUST NOT rely solely on vendor identifiers for enforcement.

---

### 2. Rail Constraints

Defines **how payment may be executed**.

---

### 3. Asset Constraints

Defines **what assets may be used**.

---

### 4. Value Constraints

Defines **how much may be spent**.

Cumulative constraints (e.g., maxPerSessionMinor) require state tracking.

The entity responsible for tracking MUST be defined by the deployment profile.

---

### 5. Temporal Constraints

Defines **when payments are allowed**.

---

### 6. Geographic Constraints

Defines **where payments are allowed**.

---

### 7. Risk Constraints

Defines **additional safeguards**.

---

### Category

Category defines the commerce context of the policy.

Examples:
- ev-charging
- parking
- api-access
- tolls

Category MAY be used by:
- policy enforcement
- trust bundle selection
- profile-specific validation

---

## Vendor Identity Model

A vendor is the **counterparty receiving payment**.

### Structure

```json
{
  "vendorId": "did:web:ionity.eu",
  "displayName": "Ionity",
  "paymentEndpoints": [
    {
      "rail": "xrpl",
      "destinations": ["rIonityDestination1"]
    }
  ]
}
```

### Notes

- `vendorId` SHOULD be a DID or domain-based identifier
- destinations are **rail-specific**
- DID MAY be used for discovery, but enforcement MUST rely on explicit endpoints
- vendorId MAY be used to resolve additional metadata (e.g., endpoints via DID), but MUST NOT be relied on for enforcement without explicit endpoints

### Vendor Matching Rules

A settlement MUST match an allowed vendor by:

1. Matching the selected rail
2. Matching the destination against vendor.paymentEndpoints for that rail

If no match is found:
→ MUST reject with VENDOR_NOT_ALLOWED

VendorId MAY be used for identity and audit purposes but MUST NOT be the sole enforcement mechanism.

---

## Canonical Policy Schema

```json
{
  "version": "1.0",
  "policyId": "policy-1",
  "policyAuthority": {
    "authorityId": "did:web:fleet.example.com"
  },
  "category": "ev-charging",
  "allowedVendors": [
    {
      "vendorId": "did:web:ionity.eu",
      "paymentEndpoints": [
        {
          "rail": "xrpl",
          "destinations": ["rIonityDestination1"]
        }
      ]
    }
  ],
  "allowedRails": ["xrpl"],
  "allowedAssets": [
    { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" }
  ],
  "valueConstraints": {
    "maxPerPaymentMinor": "2000",
    "maxPerSessionMinor": "5000"
  },
  "timeConstraints": {
    "expiresAt": "2026-03-10T00:00:00Z"
  },
  "geography": {
    "region": "EU"
  },
  "riskConstraints": {
    "requireIntentHash": true
  }
}
```

Policies MUST define at least one allowed vendor.

---

## PolicyGrant Representation

```json
{
  "policyAuthority": {
    "authorityId": "did:web:fleet.example.com",
    "keyId": "key-1"
  },
  "policyHash": "...",
  "category": "ev-charging",
  "allowedVendors": [
    {
      "vendorId": "did:web:ionity.eu",
      "paymentEndpoints": [
        {
          "rail": "xrpl",
          "destinations": ["rIonityDestination1"]
        }
      ]
    }
  ],
  "allowedRails": ["xrpl"],
  "allowedAssets": [
    { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" }
  ],
  "maxPerSessionMinor": "5000",
  "maxPerPaymentMinor": "2000",
  "geography": {
    "region": "EU"
  },
  "riskConstraints": {
    "requireIntentHash": true
  },
  "expiresAt": "2026-03-10T00:00:00Z"
}
```

## PolicyGrant Signing

PolicyGrant MUST be signed by the PolicyAuthority.

The signature binds:
- policyHash
- allowedVendors
- allowedRails
- allowedAssets
- value constraints
- temporal constraints

Signature format and verification rules are defined in the core MPCP protocol.

---

## Policy → PolicyGrant Projection Rules

PolicyGrant MUST include all fields required for deterministic enforcement.

At minimum:
- allowedVendors (including paymentEndpoints)
- allowedRails
- allowedAssets
- value constraints
- time constraints (expiresAt)

PolicyGrant MAY omit:
- display-only metadata
- internal policy annotations

Projection MUST preserve:
- vendor identity
- payment endpoints
- enforceable constraints

---

## Policy vs Trust

- **Policy** → what is allowed
- **Trust** → whose signatures are trusted

Vendor ≠ issuer.

Policy defines WHAT is allowed.
Trust defines WHO is authorized to sign artifacts.

---

## Summary

The policy model defines **who can be paid, how, under what constraints, and how those constraints are enforced deterministically at verification time**.