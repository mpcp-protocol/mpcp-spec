# Trust Model

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

---

## Overview

MPCP defines a layered trust model in which each actor operates within cryptographically enforced
constraints established by a higher-trust actor. No actor can exceed the authority granted by
its superior in the chain.

```
Policy Authority (PA)
       │  signs PolicyGrant
       ▼
   Trust Gateway
       │  enforces PA-signed budget ceiling, manages escrow
       ▼
     Agent / Vehicle Wallet
       │  signs SBAs within gateway-enforced ceiling
       ▼
    Merchant (Service Provider)
       │  verifies SBA + PolicyGrant
       ▼
    XRPL Settlement
```

---

## Actor Trust Hierarchy

### Policy Authority (highest trust)

The PA is the **root of trust** for all payment authorization. It signs PolicyGrant artifacts
that encode:

- `budgetMinor` — maximum XRP (in drops) the session may spend
- `expiresAt` — hard grant expiry
- `allowedRails` — permitted payment rails
- `allowedPurposes` — merchant category allowlist
- `authorizedGateway` — the single XRPL address permitted to submit payments
- `offlineMaxSinglePayment` — per-transaction cap for offline merchant acceptance
- `budgetEscrowRef` — reference to the on-chain XRPL escrow that pre-reserves the budget

The PA private key is the only thing that can produce a valid PolicyGrant. A compromised agent or
gateway cannot forge a PolicyGrant with a higher budget or looser constraints.

**What the PA cannot do:** The PA does not execute transactions. It has no visibility into
individual payments after grant issuance.

---

### Trust Gateway (second-highest trust)

The Trust Gateway is a mandatory **online enforcement actor** in MPCP's XRPL profile. It:

1. Creates the XRPL budget escrow at grant issuance (pre-reserving `budgetMinor` XRP)
2. Receives the PA-signed `budgetMinor` and enforces it as a hard ceiling for all payments
3. Holds the XRPL gateway seed — no other actor can submit payments on this gateway's behalf
4. Verifies the SBA signature before signing each XRPL Payment transaction
5. Enforces `allowedPurposes` from the PA-signed grant — rejects payments whose declared purpose is not in the allowlist (see [Purpose Enforcement](./PolicyGrant.md#purpose-enforcement))
6. Enforces `destinationAllowlist` and/or `merchantCredentialIssuer` from the PA-signed grant — rejects payments to unapproved destinations (see [Destination Enforcement](./PolicyGrant.md#destination-enforcement))
7. Attaches `mpcp/grant-id` memo to every on-chain payment for audit traceability
8. Releases the escrow on grant revocation (EscrowFinish with preimage) or expiry (EscrowCancel)

**What the Gateway cannot do:**

- Exceed the PA-signed `budgetMinor` (it enforces this ceiling on itself)
- Spend against a grant whose `authorizedGateway` does not match its own XRPL address
- Forge a PolicyGrant or SBA signature

**Why it is mandatory:** Without the Trust Gateway, an agent could self-report any budget ceiling.
The gateway enforces the PA-signed limit independently of agent behavior — a compromised or
prompt-injected agent cannot cause overspending.

---

### Agent / Vehicle Wallet (third-highest trust)

The agent creates per-payment **SignedBudgetAuthorizations** within the limits established by
the PolicyGrant and enforced by the gateway:

- SBA `maxAmountMinor` ≤ remaining gateway budget
- SBA `allowedPurposes` ⊆ PolicyGrant `allowedPurposes`
- SBA `destinationAllowlist` ⊆ PolicyGrant `destinationAllowlist` (when PA field is present)
- SBA signed with agent's own key (not the gateway key)

**What the agent cannot do:**

- Submit XRPL payments directly (no access to gateway seed)
- Exceed the PA-signed ceiling (gateway rejects overspends)
- Pay for a purpose not in the PolicyGrant `allowedPurposes` list (gateway enforces)

**Agent trust level:** The gateway does not trust the agent's self-reported budget state — it
maintains its own independent spend counter. The gateway also independently enforces the
PA-signed `allowedPurposes` against the declared purpose in the settlement request, and
enforces the PA-signed `destinationAllowlist` (or on-chain merchant credentials) against the
payment destination, so a compromised agent that skips its own purpose or destination check
is still blocked at the gateway.

---

### Merchant / Service Provider (lowest trust)

Merchants verify the SBA signature and PolicyGrant signature before accepting payment. They
receive a payment receipt (XRPL transaction hash) after the gateway submits the transaction.

In online mode, the merchant relies on the full chain:
`SBA signature → PolicyGrant signature → gateway spend counter → XRPL settlement`.

In offline mode, the merchant relies only on:
`SBA signature → PolicyGrant signature → offlineMaxSinglePayment cap`.

**What the merchant cannot do:**

- Create or modify a PolicyGrant
- Force a payment above the SBA `maxAmountMinor`
- Access the gateway seed

---

## What Each Actor Can and Cannot Forge

| Actor | Can forge | Cannot forge |
|-------|-----------|--------------|
| Policy Authority | Anything it signs | (root — external governance) |
| Trust Gateway | Payment sequence, timing | PolicyGrant, SBA signature |
| Agent / Wallet | SBA (within grant limits) | PolicyGrant, gateway key |
| Merchant | Verification result (local) | Any artifact, gateway key |

The critical attack surface is **agent compromise** (prompt injection, model manipulation,
software vulnerability). MPCP's gateway model ensures that a compromised agent cannot cause
overspending because:

1. The gateway enforces the PA-signed `budgetMinor` independently of the agent
2. The escrow pre-reserves the maximum budget on-chain, preventing the gateway from overspending
   even if the gateway itself is compromised (the XRPL ledger enforces the escrow amount)

---

## Online vs Offline Guarantee Table

| Guarantee | Online (gateway present) | Offline (signature-only) |
|-----------|--------------------------|--------------------------|
| SBA signature valid | ✅ | ✅ |
| PolicyGrant signature valid | ✅ | ✅ |
| Per-transaction cap enforced | ✅ `budgetMinor` / remaining | ✅ `offlineMaxSinglePayment` |
| Cumulative budget enforced | ✅ gateway counter + escrow | ❌ not enforced |
| Purpose enforced | ✅ gateway checks `allowedPurposes` | ❌ not enforced (agent-only) |
| Destination enforced | ✅ gateway checks `destinationAllowlist` / credentials | ❌ not enforced (agent-only) |
| On-chain confirmation | ✅ XRPL receipt | ❌ no settlement yet |
| Budget escrow verified | ✅ | ❌ |
| Revocation checked | ✅ gateway checks on each payment | ⚠️ best-effort (TTL cache) |

**Offline mode (Option A — Tiered Trust):** Merchants accept reduced guarantees in exchange for
the ability to operate without a network connection. The `offlineMaxSinglePayment` cap (PA-signed)
limits exposure: a compromised agent cannot present an SBA above this cap and get it accepted
offline. Cumulative overspend across many offline transactions remains a theoretical risk; it
is bounded by the escrow amount once the gateway comes back online.

---

## Escrow as Proof of Reservation

The XRPL escrow is not a payment — it is a **credit pre-authorization hold**.

```
Grant issuance:
  Gateway calls EscrowCreate(amount=budgetMinor, CancelAfter=expiresAt, Condition=crypto-condition)
  Escrow locks exactly budgetMinor XRP in the gateway's account
  budgetEscrowRef = "xrpl:escrow:{account}:{sequence}" (PA-signed into grant)

During session:
  Individual payments come from the gateway's unlocked balance (not from the escrow)
  Gateway tracks cumulative spend via its own counter

Grant revocation:
  Gateway calls EscrowFinish(Fulfillment=preimage) → immediate release of locked funds
  If preimage unavailable (server restart): EscrowCancel after CancelAfter passes

On-chain audit:
  Total spent = sum(Amount of XRPL Payments with MemoType="mpcp/grant-id", MemoData=hex(grantId))
  This is always ≤ escrow amount (enforced by gateway counter)
```

The escrow provides a public, tamper-proof **upper bound** on what the session can spend. Even
if the gateway's internal counter is wrong, it cannot have spent more than the escrow amount
(because the XRP was pre-reserved).

---

## Trust Gateway as Mandatory Actor

For MPCP's XRPL profile, the Trust Gateway is **not optional** for online payments.

Deployments that skip the gateway (having the agent submit payments directly) lose:

- PA-signed budget ceiling enforcement (agent self-reports remaining budget)
- Escrow-based budget reservation (no on-chain upper bound)
- `authorizedGateway` binding (any node could submit payments)
- On-chain audit trail (memo tagging not guaranteed)

In a planned future extension, the Trust Gateway's XRPL address will be included in the Trust
Bundle so offline merchants can verify that an SBA was produced by an entity operating under a
registered gateway. (See roadmap: Gateway key in Trust Bundle.)

---

## See Also

- [Actors](../architecture/actors.md) — Actor definitions including Trust Gateway
- [PolicyGrant](./PolicyGrant.md) — PA-signed grant fields
- [Trust Bundles](./trust-bundles.md) — Offline key distribution
- [Rails](./rails.md) — Rail extensibility and escrow URI scheme
