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
| `spa` | object | SignedPaymentAuthorization artifact |
| `settlement` | object | Executed settlement result |

Optional fields:

| Field | Type | Description |
|-------|------|--------------|
| `settlementIntent` | object | Settlement intent (required when SPA has intentHash) |
| `paymentPolicyDecision` | object | Payment policy decision (derived from SPA if omitted) |
| `ledgerAnchor` | object | Optional ledger attestation for disputed settlements |
| `sbaPublicKeyPem` | string | SBA signing public key PEM — makes bundle self-contained |
| `spaPublicKeyPem` | string | SPA signing public key PEM — makes bundle self-contained |

When `sbaPublicKeyPem` and `spaPublicKeyPem` are present, verification can run without `MPCP_SBA_SIGNING_PUBLIC_KEY_PEM` and `MPCP_SPA_SIGNING_PUBLIC_KEY_PEM` environment variables.

## Example

```json
{
  "policyGrant": {
    "grantId": "grant-1",
    "policyHash": "a1b2c3",
    "expiresAt": "2030-12-31T23:59:59Z",
    "allowedRails": ["xrpl"],
    "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" }]
  },
  "sba": { "authorization": {...}, "signature": "...", "keyId": "..." },
  "spa": { "authorization": {...}, "signature": "...", "keyId": "..." },
  "settlement": {
    "amount": "19440000",
    "rail": "xrpl",
    "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" },
    "destination": "rDestination",
    "nowISO": "2026-01-15T12:00:00Z"
  },
  "settlementIntent": { "version": "1.0", "rail": "xrpl", "amount": "19440000", ... },
  "sbaPublicKeyPem": "-----BEGIN PUBLIC KEY-----\n...",
  "spaPublicKeyPem": "-----BEGIN PUBLIC KEY-----\n..."
}
```

## Verifier Support

The MPCP CLI accepts artifact bundles as input:

```bash
mpcp verify settlement-bundle.json
mpcp verify settlement-bundle.json --append-log audit.jsonl
```

Bundles are distinguished from full `SettlementVerificationContext` by the presence of `sba`/`spa` keys (artifact-keyed) rather than `signedBudgetAuthorization`/`signedPaymentAuthorization` (context-keyed).

## Schema

The bundle format is defined by `artifactBundleSchema` in `src/schema/artifactBundle.ts`. Each nested artifact conforms to its respective MPCP schema (PolicyGrant, SignedBudgetAuthorization, SignedPaymentAuthorization, SettlementIntent, SettlementResult).

**Note:** `paymentPolicyDecision` and `ledgerAnchor` are currently loosely typed (generic object) in the schema. They will be formalized with strict schemas in a later update.
