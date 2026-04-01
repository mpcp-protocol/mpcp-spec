# Payment Rails

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

---

## Overview

A **payment rail** is the settlement system that executes the actual XRP/stablecoin transfer
after MPCP authorization succeeds. MPCP controls *authorization* above settlement rails — it
does not replace them.

MPCP is designed to support multiple payment rails under a common authorization model.
The **XRPL profile** is the current reference implementation and uses escrow-based budget
enforcement as a core mechanism.

---

## Rail Identifiers

Rails are identified by short string identifiers in `PolicyGrant.allowedRails`:

| Identifier | Description |
|------------|-------------|
| `xrpl` | XRP Ledger (reference implementation) |
| `evm` | EVM-compatible chains (Ethereum, Polygon, etc.) |
| `stellar` | Stellar network |
| `stripe` | Stripe (card / ACH) |

Custom identifiers SHOULD follow a `{organization}:{rail}` namespace convention to avoid
conflicts (e.g. `"acme:internal"`).

---

## XRPL — Reference Implementation

XRPL is the reference rail for MPCP. It demonstrates the full enforcement model:

### Budget Escrow

At grant issuance, the Trust Gateway calls `EscrowCreate` to lock exactly `budgetMinor` XRP.
This escrow is a **proof-of-reservation** — it guarantees that the funds to cover the entire
grant budget exist on-chain and cannot be spent on anything else during the session.

```
EscrowCreate:
  Account: <gateway address>
  Amount:  budgetMinor (drops)
  Condition: PREIMAGE-SHA-256 crypto-condition (allows early release)
  CancelAfter: grant expiresAt (XRPL ripple epoch seconds)
```

The `budgetEscrowRef` field in the PA-signed PolicyGrant carries a pointer to this escrow:

```
budgetEscrowRef = "xrpl:escrow:{account}:{sequence}"
```

### Per-Payment Settlement

Individual payments are submitted by the gateway using `Payment` transactions. Each payment
carries a `mpcp/grant-id` memo that links it to the grant for on-chain audit:

```
Memo:
  MemoType: hex("mpcp/grant-id")
  MemoData: hex(grantId)
```

### Escrow Release

| Scenario | Mechanism |
|----------|-----------|
| Grant revoked (preimage available) | `EscrowFinish` with PREIMAGE-SHA-256 fulfillment → immediate release |
| Grant expired (preimage unavailable, after CancelAfter) | `EscrowCancel` |
| Session completes normally | Either mechanism after final payment |

The gateway holds the preimage in memory during the session. If the server restarts, the
preimage is lost — the escrow is released naturally at `CancelAfter`.

---

## Escrow URI Scheme

The `budgetEscrowRef` field uses a generic URI scheme that can accommodate any rail:

```
"{rail}:{mechanism}:{identifier...}"
```

Examples:

| Rail | budgetEscrowRef | Description |
|------|-----------------|-------------|
| XRPL | `xrpl:escrow:{account}:{sequence}` | EscrowObject identified by owner account and offer sequence |
| Ethereum | `eth:timelock:{contract}:{lockId}` | ERC-4626 timelock or custom hold contract |
| Stellar | `stellar:clawback:{asset}:{account}` | Clawback-enabled asset hold |

The URI components after the rail identifier are rail-specific. Verifiers that do not recognize
a rail SHOULD treat `budgetEscrowRef` as opaque metadata.

---

## Adding a New Rail

To extend MPCP to a new settlement rail, implementors MUST provide:

1. **Budget reservation mechanism** — equivalent to XRPL escrow. The reserved amount MUST be
   provably locked and released only under the same conditions (grant expiry or revocation).

2. **Per-payment memo / tagging** — each settlement transaction MUST carry the `grantId` in
   an on-chain field to enable audit. The tagging field and encoding are rail-specific.

3. **Trust Gateway integration** — the gateway component for the new rail MUST:
   - Enforce the PA-signed `budgetMinor` as a hard ceiling
   - Verify `authorizedGateway` identity if applicable to the rail
   - Submit settlement transactions (not the agent)

4. **`budgetEscrowRef` format** — define the URI format using the `{rail}:{mechanism}:{id}`
   scheme and document it so verifiers can parse it.

5. **`allowedRails` identifier** — register a short string identifier and document it.

Implementors SHOULD submit a profile document to the MPCP spec repository describing the
rail-specific behavior, escrow mechanism, and audit tagging format.

---

## XRPL Offline Mode (Tiered Trust)

For XRPL, offline mode uses the Trust Bundle + `offlineMaxSinglePayment` cap:

```
Offline merchant verification:
  1. Verify SBA signature via Trust Bundle keys
  2. Verify PolicyGrant signature via Trust Bundle keys
  3. Check SBA.maxAmountMinor ≤ PolicyGrant.offlineMaxSinglePayment
  4. Accept (signature-only guarantee — cumulative budget not enforced)
```

The cumulative budget guarantee is deferred until the merchant comes back online and syncs
with the Trust Gateway.

For other rails, an equivalent offline profile SHOULD be defined. The key requirement is that
the offline-accepted amount per transaction is bounded by a PA-signed cap.

---

## What MPCP Does Not Control

MPCP does not:

- Choose the settlement rail at runtime (the agent or policy selects from `allowedRails`)
- Execute settlement directly (the Trust Gateway or merchant's processor does this)
- Define the escrow smart contract or ledger object structure beyond the URI reference

MPCP controls the **authorization chain** that leads to settlement. Settlement itself is
delegated to the rail.

---

## See Also

- [Trust Model](./trust-model.md) — Escrow as proof-of-reservation
- [PolicyGrant](./PolicyGrant.md) — `budgetMinor`, `budgetEscrowRef`, `authorizedGateway`
- [Trust Bundles](./trust-bundles.md) — Offline key distribution for multi-rail deployments
- [Actors](../architecture/actors.md) — Trust Gateway role
