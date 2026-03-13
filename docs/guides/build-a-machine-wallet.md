# Build a Machine Wallet

This guide walks through building a machine wallet that can spend within MPCP policy and budget bounds.

## Concepts

A **machine wallet** holds:

1. **PolicyGrant** — Permission envelope (rails, assets, expiration)
2. **SignedBudgetAuthorization (SBA)** — Spending envelope for the session
3. **Signing keys** — For producing SignedPaymentAuthorizations (SPA)

When a payment is requested, the wallet:

1. Checks the request against policy and budget
2. Signs an SPA if the payment is permitted
3. Returns the SPA (and optional SettlementIntent) to the payee

## Setup

```bash
npm install mpcp-service
```

## Generate Keys

The machine needs keys for signing SPAs. (SBA is typically signed by the fleet/issuer.)

```javascript
import crypto from "node:crypto";

const spaKeys = crypto.generateKeyPairSync("ed25519");
const privateKeyPem = spaKeys.privateKey.export({ type: "pkcs8", format: "pem" });
const publicKeyPem = spaKeys.publicKey.export({ type: "spki", format: "pem" });

// Store securely; use privateKeyPem for signing
```

## Create Policy Grant and Budget

```javascript
import {
  createPolicyGrant,
  createBudgetAuthorization,
  createSignedBudgetAuthorization,
} from "mpcp-service/sdk";

const policyGrant = createPolicyGrant({
  policyHash: "a1b2c3d4",
  allowedRails: ["xrpl"],
  allowedAssets: [{ symbol: "RLUSD", namespace: "rIssuer" }],
  expiresAt: "2030-12-31T23:59:59Z",
});

// SBA requires fleet/issuer keys (MPCP_SBA_SIGNING_PRIVATE_KEY_PEM)
// For demo, use createSignedBudgetAuthorization with env set
const sba = createSignedBudgetAuthorization({
  sessionId: "sess-123",
  vehicleId: "veh-456",
  policyHash: policyGrant.policyHash,
  currency: "USD",
  maxAmountMinor: "3000",
  allowedRails: ["xrpl"],
  allowedAssets: [{ symbol: "RLUSD", namespace: "rIssuer" }],
  destinationAllowlist: ["rParking"],
  expiresAt: "2030-12-31T23:59:59Z",
});
```

## Sign a Payment

When the payee requests payment:

```javascript
import {
  createSignedPaymentAuthorization,
  createSettlementIntent,
  computeSettlementIntentHash,
} from "mpcp-service/sdk";

// 1. Build settlement intent from the quote
const intent = createSettlementIntent({
  rail: "xrpl",
  amount: "1000",
  destination: "rParking",
  asset: { symbol: "RLUSD", namespace: "rIssuer" },
});

// 2. Create SPA (requires MPCP_SPA_SIGNING_PRIVATE_KEY_PEM)
const spa = createSignedPaymentAuthorization({
  decisionId: "dec-789",
  sessionId: sba.authorization.sessionId,
  policyHash: sba.authorization.policyHash,
  quoteId: "quote-17",
  rail: "xrpl",
  asset: { symbol: "RLUSD", namespace: "rIssuer" },
  amount: "1000",
  destination: "rParking",
  intentHash: computeSettlementIntentHash(intent),
  expiresAt: sba.authorization.expiresAt,
});
```

## Verify Before Signing

Before signing, the wallet should verify:

1. **Budget** — Amount ≤ maxAmountMinor; destination in allowlist
2. **Policy** — Rail and asset permitted
3. **Expiration** — Not expired

Use `verifySignedBudgetAuthorization` from the SDK to check the budget against the payment decision.

## Run the Example

The parking session example demonstrates the full flow:

```bash
npm run build
npm run example:parking
```

Or the guardrails demo with tamper detection:

```bash
npm run example:guardrails
```

## See Also

- [Examples: Parking](https://mpcp-protocol.github.io/mpcp-reference/examples/parking/)
- [Protocol: Artifacts](../protocol/artifacts.md)
- [Reference: SDK](https://mpcp-protocol.github.io/mpcp-reference/reference/sdk/)
