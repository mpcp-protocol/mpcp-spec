# Why XRPL as the Settlement Layer

MPCP v1.0 is XRPL-primary. This page explains the design rationale behind that choice.

## The Core Requirement

MPCP's authorization model requires a settlement layer that can do three things:

1. **Pre-reserve a budget** at grant issuance — so the policy ceiling is enforced by the ledger, not by trusting the agent
2. **Settle individual payments** against that reservation — quickly, cheaply, and with deterministic finality
3. **Provide an on-chain audit trail** linking every payment back to its originating grant

These requirements ruled out most settlement options and pointed directly to XRPL.

---

## XRPL Native Escrow

The most important fit is structural. MPCP's budget model works as follows:

```
PolicyGrant issued
      ↓
Trust Gateway pre-reserves budgetMinor via EscrowCreate
      ↓
Each SBA triggers a payment drawn against the escrow
      ↓
EscrowFinish on revocation / EscrowCancel on expiry
```

XRPL has first-class `EscrowCreate`, `EscrowFinish`, and `EscrowCancel` transaction types built into the protocol. No smart contract is required. The ledger itself enforces the ceiling — even if the Trust Gateway were compromised, it cannot spend more than was locked in the escrow.

This isn't replicated cleanly on other rails:

- **EVM** — Requires a custom smart contract to hold funds. Contract bugs become MPCP bugs. Gas costs make micro-payments expensive.
- **Stripe / hosted** — No concept of pre-reservation with cryptographic release conditions. Requires trusting Stripe's API at settlement time.
- **Bitcoin / Lightning** — No escrow with conditional release. Lightning is payment-channel based, not budget-escrow based.

---

## Deterministic Finality

XRPL closes ledgers every 3–5 seconds with deterministic finality. There are no forks, no re-orgs, no gas auctions.

For machine payments this matters:

- A vehicle paying for charging needs confirmation before it drives away
- A parking meter needs settlement assurance before it raises the barrier
- An AI agent booking a hotel needs to know the payment cleared before confirming the reservation

EVM chains have probabilistic finality (waiting for confirmations adds latency) and gas fee variance that makes small, frequent payments unpredictable in cost.

---

## Transaction Memo Field

XRPL payments natively support memo fields. MPCP uses this to attach `mpcp/grant-id` to every payment transaction:

```
MemoType:  hex("mpcp/grant-id")
MemoData:  hex(grantId)
```

This creates a permanent, on-chain audit trail. Auditors can independently query the ledger and sum all payments linked to a grant without trusting any MPCP-specific backend.

This is a first-class ledger feature — no side-channel, no off-chain database required. EVM does have calldata but it is not indexed in the same way and is significantly more expensive per byte.

---

## RLUSD: Fiat-Denominated Settlement

Machine payments are operational expenses denominated in fiat. A fleet operator budgeting $50/day per vehicle needs stable, predictable costs — not exposure to XRP price movements.

RLUSD (Ripple USD) is a regulated USD stablecoin native to XRPL. It enables:

- Fiat-denominated budgets (`budgetMinor` in USD cents)
- No price conversion at payment time
- Institutional-grade compliance (regulated stablecoin)

MPCP policies express budgets in fiat (`currency: "USD"`, `minorUnit: 2`). The Trust Gateway converts to RLUSD at settlement. This separation means policy authors never need to think about on-chain asset mechanics.

---

## did:xrpl for Identity

MPCP uses DID-based key resolution for policy authority identity. XRPL has a native DID method (`did:xrpl`) that ties identity directly to the ledger:

- Policy authority keys are resolved from the XRPL ledger
- No separate identity infrastructure required
- Key rotation is an on-chain transaction, not an off-chain configuration change

This integrates naturally with MPCP's key resolution pipeline and with fleet operators who already hold XRPL accounts.

---

## NFT-Based Policy Anchoring and Revocation

XRPL supports non-transferable NFTokens. MPCP uses these for two purposes:

**Policy anchoring** — The policy document hash can be minted as an NFT at grant issuance, creating a tamper-evident on-chain record that any auditor can verify independently.

**On-chain revocation** — Burning the NFT signals grant revocation. Merchants using Trust Bundles for offline verification can check NFT existence without contacting any hosted revocation service. The ledger is the revocation oracle.

---

## Low Fees

XRPL transaction fees are a fraction of a cent (typically ~0.00001 XRP). This makes MPCP viable for the full range of machine payment scenarios:

| Payment type | Typical amount | XRPL fee | Fee as % |
|-------------|----------------|----------|----------|
| Parking (30 min) | $1.50 | ~$0.0001 | 0.007% |
| EV charging session | $8.00 | ~$0.0001 | 0.001% |
| Toll | $0.75 | ~$0.0001 | 0.013% |
| API inference call | $0.02 | ~$0.0001 | 0.5% |

EVM gas fees at congested periods would make sub-$1 payments economically unviable. Stripe/hosted rails charge 2–3% plus fixed fees, which would consume a meaningful fraction of micro-payments.

---

## What Other Rails Would Need

MPCP's authorization layer is designed to be extensible. Adding a new settlement rail to a future MPCP profile requires:

1. **Budget pre-reservation** — A mechanism to lock `budgetMinor` at grant issuance that the ledger enforces (not just the application)
2. **Per-payment memo** — A way to attach `grantId` to each settlement transaction for on-chain audit
3. **Deterministic finality** — Confirmation within a timeframe compatible with machine payment UX
4. **Low per-transaction cost** — Economically viable for sub-$10 payments

XRPL satisfies all four natively. Future profiles may define how other rails satisfy these requirements — for example, an EVM profile using a smart contract escrow, or a Stripe profile using earmarked funds.

---

## Summary

| Property | XRPL | Why it matters for MPCP |
|----------|------|------------------------|
| Native escrow | Yes | Budget ceiling enforced by ledger, not application |
| Deterministic finality | 3–5s | Machine UX requires fast confirmation |
| Memo field | Yes | On-chain grant-id audit trail |
| RLUSD stablecoin | Yes | Fiat-denominated operational budgets |
| did:xrpl identity | Yes | PA key resolution without external infrastructure |
| NFT policy anchor | Yes | Tamper-evident policy record + burn-to-revoke |
| Sub-cent fees | Yes | Viable for parking, tolls, micro-payments |

XRPL is not the only possible settlement layer for MPCP — it is the one that maps most naturally to the protocol's requirements in v1.0. Other rails may be added as MPCP profiles mature.
