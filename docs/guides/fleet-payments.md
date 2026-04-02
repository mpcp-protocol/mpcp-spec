# Fleet Payments

This guide explains how fleet operators and infrastructure providers integrate MPCP for autonomous vehicle payments.

## Architecture

```
Fleet Operator (PA)               Vehicle                 Trust Gateway        Infrastructure
      │                              │                          │                     │
      │ PolicyGrant (budgetMinor,     │                          │                     │
      │ budgetEscrowRef, gateway)     │                          │                     │
      │ ───────────────────────────► │                          │                     │
      │                              │  Payment request         │                     │
      │                              │ ◄──────────────────────────────────────────── │
      │                              │                          │                     │
      │                              │  SBA (maxAmountMinor,    │                     │
      │                              │  destinationAllowlist)   │                     │
      │                              │ ────────────────────────►│                     │
      │                              │                          │ verify SBA + policy  │
      │                              │                          │ submit XRPL Payment  │
      │                              │                          │ ──────────────────► │
      │                              │                          │              verify locally
      │                              │                          │              gate opens
```

## Fleet Operator: Issue PolicyGrant

The fleet operator's Policy Authority issues a PolicyGrant before the vehicle goes into the field.

```javascript
import { createPolicyGrant } from "mpcp-service/sdk";

const policyGrant = createPolicyGrant({
  policyHash: "fleet-policy-v1",
  allowedRails: ["xrpl"],
  allowedAssets: [{ kind: "IOU", currency: "RLUSD", issuer: "rIssuer" }],
  budgetMinor: 3000,                          // PA-signed ceiling (USD cents = $30.00)
  budgetEscrowRef: "xrpl:escrow:rGateway:12345678",  // on-chain escrow reference
  authorizedGateway: "rGateway...",          // only this gateway may settle
  offlineMaxSinglePayment: 500,              // per-tx cap for offline merchants ($5.00)
  expiresAt: "2026-12-31T23:59:59Z",
});
```

The Trust Gateway creates the XRPL escrow at grant issuance, locking `budgetMinor` XRP as a proof-of-reservation.

## Vehicle: Sign Per-Payment SBA

The vehicle stores the PolicyGrant onboard. When infrastructure requests payment, the vehicle signs a per-payment SBA:

```javascript
import { createSignedSessionBudgetAuthorization } from "mpcp-service/sdk";

const sba = createSignedSessionBudgetAuthorization({
  grantId: policyGrant.grantId,
  sessionId: "sess-vehicle-123",
  actorId: "vehicle-123",
  policyHash: policyGrant.policyHash,
  currency: "USD",
  maxAmountMinor: "780",                     // this payment only (USD cents = $7.80)
  allowedRails: ["xrpl"],
  allowedAssets: [{ kind: "IOU", currency: "RLUSD", issuer: "rIssuer" }],
  destinationAllowlist: ["rChargingStation"],
  budgetScope: "SESSION",
  expiresAt: policyGrant.expiresAt,
});
```

No central backend is contacted at payment time. The SBA + PolicyGrant are sent to the infrastructure and Trust Gateway simultaneously.

## Infrastructure: Verify

The parking meter, charging station, or toll gate verifies the MPCP chain locally:

```javascript
import { verifyMpcp } from "@mpcp/merchant-sdk";

const result = await verifyMpcp(sba, {
  trustBundles: [loadedBundle],   // pre-loaded at startup; no network call needed
});
if (result.valid) {
  // Open gate, start charging, etc.
}
```

The Trust Bundle is pre-loaded at merchant startup and refreshed periodically. No per-payment network call is required for offline verification.

## Trust Gateway: Settle

The Trust Gateway receives the SBA, verifies cumulative spend against `budgetMinor`, and submits the XRPL Payment with an `mpcp/grant-id` memo:

```
XRPL Payment:
  Account:  rGateway...
  Amount:   780000 RLUSD drops
  Destination: rChargingStation
  Memo: MemoType=hex("mpcp/grant-id"), MemoData=hex(grantId)
```

The merchant receives the XRPL transaction hash as the payment receipt.

## Offline Flow

MPCP supports **offline payment** when the vehicle has no network:

1. Vehicle holds PolicyGrant + Trust Bundle onboard before entering garage/tunnel
2. At payment time, vehicle signs SBA locally (no network)
3. Infrastructure verifies PolicyGrant + SBA signatures via Trust Bundle (no network)
4. Infrastructure accepts up to `offlineMaxSinglePayment` per transaction
5. When connectivity returns, the Trust Gateway reconciles and settles on-chain

The offline payment flow is supported natively — grants and Trust Bundles are cached locally; verification requires no network call.

## Reference Profiles

Common deployment patterns:

- **Fleet Online** — Full Trust Gateway enforcement, XRPL escrow, on-chain audit
- **Fleet Offline** — Trust Bundle key resolution, `offlineMaxSinglePayment` cap
- **Parking** — Meter/gate, short sessions, Trust Bundle at kiosk
- **EV Charging** — Variable session length, Trust Bundle + optional online revocation check

## See Also

- [Reference Flow: Fleet EV](../architecture/fleet-ev-reference-flow.md)
- [Trust Bundles](../protocol/trust-bundles.md) — Offline key distribution
- [Trust Model](../protocol/trust-model.md) — Escrow as proof-of-reservation
- [Rails](../protocol/rails.md) — XRPL escrow mechanism
