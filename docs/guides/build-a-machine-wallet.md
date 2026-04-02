# Build a Machine Wallet

This guide walks through building a machine wallet that can spend within MPCP policy and budget bounds.

## Concepts

A **machine wallet** holds:

1. **PolicyGrant** — Permission envelope signed by the Policy Authority (PA); includes budget ceiling, escrow reference, and authorized gateway
2. **Signing key** — For producing per-payment SignedBudgetAuthorizations (SBA)

When a payment is requested, the wallet:

1. Checks the request against policy (rail, asset, purpose, destination)
2. Checks revocation status (optional, via `revocationEndpoint`)
3. Signs a per-payment SBA (amount + destination for this payment)
4. Sends the SBA to the Trust Gateway for settlement

The Trust Gateway enforces the cumulative budget ceiling and submits the XRPL Payment.

## Setup

```bash
npm install mpcp-service
```

## Generate Signing Keys

The machine needs a key for signing SBAs.

```javascript
import crypto from "node:crypto";

const sbaKeys = crypto.generateKeyPairSync("ed25519");
const privateKeyPem = sbaKeys.privateKey.export({ type: "pkcs8", format: "pem" });
const publicKeyPem = sbaKeys.publicKey.export({ type: "spki", format: "pem" });

// Store securely; export publicKeyPem to the PA so it can be included in Trust Bundles
```

## Receive and Verify PolicyGrant

The PolicyGrant is issued by the fleet operator's PA server and delivered to the wallet before operation:

```javascript
import { verifyPolicyGrant } from "mpcp-service/sdk";

// Verify signature before storing
const isValid = await verifyPolicyGrant(policyGrant);
if (!isValid) throw new Error("Invalid PolicyGrant");

// Store locally
wallet.setPolicyGrant(policyGrant);
```

## Sign a Per-Payment SBA

When the merchant/infrastructure sends a payment quote:

```javascript
import { createSignedSessionBudgetAuthorization } from "mpcp-service/sdk";

// SBA signs this specific payment — NOT the full trip/shift budget
const sba = createSignedSessionBudgetAuthorization({
  grantId: policyGrant.grantId,
  sessionId: "sess-vehicle-123",
  actorId: "vehicle-123",
  policyHash: policyGrant.policyHash,
  issuer: "vehicle-123.fleet.example.com",   // required for Trust Bundle resolution
  currency: "USD",
  maxAmountMinor: "780",                      // this payment (USD cents = $7.80)
  allowedRails: ["xrpl"],
  allowedAssets: [{ kind: "IOU", currency: "RLUSD", issuer: "rIssuer" }],
  destinationAllowlist: ["rParkingMeter"],
  budgetScope: "SESSION",
  expiresAt: policyGrant.expiresAt,
});

// Send {policyGrant, sba} to the merchant for verification
// Send sba to the Trust Gateway for settlement
```

## Validate Before Signing

Before signing, the wallet MUST verify:

1. **Rail and asset** — Permitted by PolicyGrant `allowedRails` and `allowedAssets`
2. **Destination** — Expected recipient (cross-check with quote)
3. **Expiration** — PolicyGrant not expired
4. **Revocation** — Check `revocationEndpoint` if present (fail-open for offline)

```javascript
import { checkRevocation } from "mpcp-service/sdk";

if (policyGrant.revocationEndpoint) {
  const { revoked } = await checkRevocation(
    policyGrant.revocationEndpoint,
    policyGrant.grantId,
  );
  if (revoked) throw new Error("Grant revoked");
}
```

## Trust Bundle for Offline Merchants

Pre-load a Trust Bundle so merchants can verify the wallet's SBA signatures without a network call:

```javascript
import { verifyTrustBundle, resolveFromTrustBundle } from "mpcp-service/sdk";

// Merchant-side: load Trust Bundle at startup
const isValid = verifyTrustBundle(bundle, rootPublicKeyPem);
if (!isValid) throw new Error("Invalid Trust Bundle");

// Resolve SBA issuer key from bundle (no network call)
const jwk = resolveFromTrustBundle(sba.issuer, sba.issuerKeyId, [bundle]);
```

## See Also

- [Reference Flow: Fleet EV](../architecture/fleet-ev-reference-flow.md)
- [Trust Bundles](../protocol/trust-bundles.md) — Key distribution for offline verification
- [Trust Model](../protocol/trust-model.md) — Trust Gateway role and escrow
- [Protocol: Artifacts](../protocol/artifacts.md)
- [Integration Guide](integration-guide.md) — Full actor-by-actor walkthrough
