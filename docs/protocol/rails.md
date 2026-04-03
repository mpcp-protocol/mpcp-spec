# Payment Rails

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

---

## Overview

A **payment rail** is the settlement system that executes the actual asset transfer after MPCP
authorization succeeds. MPCP controls *authorization* above settlement rails — it does not replace
them.

**MPCP v1.0** defines **one normative rail: XRPL.** Conforming PolicyGrants MUST use
`allowedRails: ["xrpl"]` only. Additional rail identifiers described in older revisions of this
document are **reserved for future protocol versions** and MUST NOT appear in conforming v1.0
artifacts.

The **XRPL profile** is the reference implementation and uses escrow-based budget enforcement as a
core mechanism.

---

## Rail Identifiers

| Identifier | Status in MPCP v1.0 |
|------------|---------------------|
| `xrpl` | **Normative** — required for conformance |
| `evm`, `stellar`, `stripe`, `hosted`, and others | **Reserved** — MUST NOT appear in conforming PolicyGrants or SBAs |

Custom identifiers for experimental deployments are **non-conforming** until registered in a future
spec revision.

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
preimage may be lost — the escrow is released naturally at `CancelAfter`. **Cumulative spend
enforcement** nevertheless MUST rely on durable gateway state or memo-based reconstruction (see
[Trust Model — Gateway durable spend state](./trust-model.md#gateway-durable-spend-state-must)).

---

## Escrow URI Scheme

The `budgetEscrowRef` field uses a generic URI scheme for documentation extensibility:

```
"{rail}:{mechanism}:{identifier...}"
```

**MPCP v1.0 conforming grants** use XRPL only:

| Rail | budgetEscrowRef | Description |
|------|-----------------|-------------|
| XRPL | `xrpl:escrow:{account}:{sequence}` | EscrowObject identified by owner account and offer sequence |

The URI components after the rail identifier are rail-specific. Verifiers that encounter unknown
rails SHOULD treat `budgetEscrowRef` as opaque metadata.

---

## Future rails

To extend MPCP beyond XRPL in a **future** protocol version, a revision MUST specify:

1. **Budget reservation mechanism** — equivalent to XRPL escrow.
2. **Per-payment memo / tagging** — each settlement transaction MUST carry `grantId` for audit.
3. **Trust Gateway integration** — enforce PA-signed ceilings and identity rules for that rail.
4. **`budgetEscrowRef` format** and **`allowedRails`** identifier registration.

Until such a revision is published, implementations MUST treat XRPL as the sole conforming rail.

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

---

## What MPCP Does Not Control

MPCP does not:

- Choose the settlement rail at runtime outside the PolicyGrant allowlist (v1.0: XRPL only)
- Execute settlement directly (the Trust Gateway submits on-ledger)
- Define the escrow ledger object structure beyond the URI reference

MPCP controls the **authorization chain** that leads to settlement. Settlement itself is
delegated to the rail.

---

## See Also

- [Trust Model](./trust-model.md) — Escrow as proof-of-reservation; gateway durable spend state
- [PolicyGrant](./PolicyGrant.md) — `budgetMinor`, `budgetEscrowRef`, `authorizedGateway`, `velocityLimit`, conformance
- [Trust Bundles](./trust-bundles.md) — Offline key distribution
- [Actors](../architecture/actors.md) — Trust Gateway role
