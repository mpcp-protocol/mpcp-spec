# Fleet Payments

This guide explains how fleet operators and infrastructure providers integrate MPCP for autonomous vehicle payments.

## Architecture

```
Fleet Operator                    Vehicle                    Infrastructure (parking, charging)
      │                              │                                    │
      │ PolicyGrant + SBA             │                                    │
      │ ───────────────────────────► │                                    │
      │                              │                                    │
      │                              │  Payment request                   │
      │                              │ ◄─────────────────────────────────│
      │                              │                                    │
      │                              │  SPA + intent                      │
      │                              │ ─────────────────────────────────►│
      │                              │                                    │
      │                              │              verify locally        │
      │                              │              gate opens            │
```

## Fleet Operator: Issue Budgets

The fleet operator (or policy engine) issues PolicyGrant and SBA before the vehicle goes into the field.

```javascript
import { issueBudget } from "mpcp-service/service";
import { createPolicyGrant } from "mpcp-service/sdk";

const policyGrant = createPolicyGrant({
  policyHash: "fleet-policy-v1",
  allowedRails: ["xrpl", "evm"],
  allowedAssets: [{ kind: "IOU", currency: "RLUSD", issuer: "rIssuer" }],
  expiresAt: "2030-12-31T23:59:59Z",
});

const sba = issueBudget({
  policyGrant,
  sessionId: "sess-vehicle-123",
  vehicleId: "vehicle-123",
  maxAmountMinor: "5000",
  destinationAllowlist: ["rParking", "rCharging", "rToll"],
});
```

Requires `MPCP_SBA_SIGNING_PRIVATE_KEY_PEM` and related env vars.

## Vehicle: Hold and Spend

The vehicle stores PolicyGrant + SBA onboard. When infrastructure requests payment:

1. Check request against budget (amount, destination, rail, asset)
2. Sign SPA locally
3. Return SPA + settlement intent to infrastructure

No central backend is contacted at payment time.

## Infrastructure: Verify

The parking meter, charging station, or toll gate verifies the MPCP chain locally:

```javascript
import { verifySettlementService } from "mpcp-service/service";

const result = verifySettlementService(context);
if (result.valid) {
  // Open gate, start charging, etc.
}
```

Or use the CLI:

```bash
mpcp verify settlement-bundle.json
```

## Offline Flow

MPCP supports **offline payment** when the vehicle has no network:

1. Vehicle loads PolicyGrant + SBA before entering garage/tunnel
2. At payment time, vehicle signs SPA locally (no network)
3. Infrastructure verifies chain locally (no network)
4. When connectivity returns, settlement is reconciled

See [Offline Payments](https://github.com/mpcp-protocol/mpcp-reference/blob/main/doc/architecture/OFFLINE_PAYMENTS.md) in the reference implementation.

## Reference Profiles

Use [reference profiles](https://github.com/mpcp-protocol/mpcp-reference/blob/main/doc/architecture/REFERENCE_PROFILES.md) for common deployment patterns:

- **Fleet Offline** — Pre-auth budgets, offline payment
- **Parking** — Meter/gate, short sessions
- **Charging** — EV charging, variable session length
- **Hosted Rail** — Backend-hosted, online approval

## Run the Example

```bash
npm run build
npm run example:fleet
```

Produces `fleet-demo-bundle.json`. Verify:

```bash
npx mpcp verify examples/fleet-payment/fleet-demo-bundle.json --explain
```

## See Also

- [Examples: Fleet](https://mpcp-protocol.github.io/mpcp-reference/examples/fleet/)
- [Reference Profiles](https://github.com/mpcp-protocol/mpcp-reference/blob/main/doc/architecture/REFERENCE_PROFILES.md)
- [Offline Payments](https://github.com/mpcp-protocol/mpcp-reference/blob/main/doc/architecture/OFFLINE_PAYMENTS.md)
- [Reference: Service API](https://mpcp-protocol.github.io/mpcp-reference/reference/service-api/)
