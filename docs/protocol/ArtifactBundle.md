# MPCP Artifact Bundle

## Overview

An **artifact bundle** is a canonical JSON format that packages complete MPCP payment verification data for exchange between systems. It standardizes how settlement verification inputs are packaged for:

- dispute resolution workflows
- deterministic protocol test vectors
- developer tooling and debugging
- audit trails and compliance

## Bundle Format

The bundle is a JSON object with artifact-keyed fields. Required fields:

| Field | Type | Description |
|-------|------|--------------|
| `policyGrant` | object | Policy grant constraining the session |
| `sba` | object | SignedBudgetAuthorization artifact |
| `settlement` | object | Executed settlement result (XRPL txHash + memo) |

Optional fields:

| Field | Type | Description |
|-------|------|--------------|
| `ledgerAnchor` | object | On-chain attestation (HCS or XRPL NFT anchor ref) |
| `policyGrantPublicKeyPem` | string | PolicyGrant signing public key PEM — makes bundle self-contained |
| `sbaPublicKeyPem` | string | SBA signing public key PEM — makes bundle self-contained |

When `policyGrantPublicKeyPem` and `sbaPublicKeyPem` are present, verification can run without the corresponding environment variables.

## Example

```json
{
  "policyGrant": {
    "grantId": "grant-1",
    "policyHash": "a1b2c3",
    "expiresAt": "2030-12-31T23:59:59Z",
    "allowedRails": ["xrpl"],
    "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" }],
    "budgetMinor": "50000",
    "budgetEscrowRef": "xrpl:escrow:rGateway:12345",
    "authorizedGateway": "rGateway...",
    "issuer": "did:web:operator.example.com",
    "issuerKeyId": "policy-auth-key-1",
    "signature": "..."
  },
  "sba": {
    "authorization": {
      "grantId": "grant-1",
      "maxAmountMinor": "780",
      "budgetScope": "SESSION",
      "allowedRails": ["xrpl"],
      "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" }]
    },
    "issuer": "did:web:fleet.example.com",
    "issuerKeyId": "budget-auth-key-1",
    "signature": "..."
  },
  "settlement": {
    "txHash": "ABC123...",
    "rail": "xrpl",
    "amount": "780",
    "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" },
    "destination": "rDestination",
    "grantId": "grant-1",
    "nowISO": "2026-01-15T12:00:00Z"
  },
  "policyGrantPublicKeyPem": "-----BEGIN PUBLIC KEY-----\n...",
  "sbaPublicKeyPem": "-----BEGIN PUBLIC KEY-----\n..."
}
```

## Verifier Support

The MPCP CLI accepts artifact bundles as input:

```bash
mpcp verify settlement-bundle.json
mpcp verify settlement-bundle.json --append-log audit.jsonl
```

## Schema

The bundle format is defined by `artifactBundleSchema` in `src/schema/artifactBundle.ts`. Each nested artifact conforms to its respective MPCP schema (PolicyGrant, SignedBudgetAuthorization, SettlementResult).

**Note:** `ledgerAnchor` is currently loosely typed (generic object) in the schema. It will be formalized with a strict schema in a later update.
