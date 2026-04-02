# The Problem

Traditional payment systems assume a **human approves every transaction**. A card swipe, a bank transfer, or a wallet signature—each involves an explicit human decision at the moment of payment.

Machine payments break that assumption.

## Why Human-Centric Systems Fail for Machines

### 1. Autonomous Systems Cannot Pause for Approval

An autonomous vehicle cannot stop at a toll gate to open a wallet popup. A delivery robot cannot wait for a human to approve each charging station payment. An AI agent cannot interrupt a workflow every few seconds for manual consent.

**Machines need to spend within bounds, not per transaction.**

### 2. Wallet Popups Don't Scale

In Web3 and wallet-based flows, the dominant pattern is "sign to approve." Each payment triggers a wallet interaction. This works when a human is at the keyboard.

It does **not** work when:

- **Volume is high** — Hundreds of micropayments per vehicle per day (parking, charging, tolls) cannot each require a popup
- **Latency matters** — A gate does not wait 30 seconds for a user to find their phone
- **The user is absent** — A robot, IoT device, or background agent has no human to click "Confirm"
- **UX matters** — Frequent popups destroy usability and adoption

### 3. Connectivity Cannot Be Assumed

Autonomous fleets operate where connectivity may be intermittent:

- Underground parking garages
- Tunnels
- Charging facilities in remote areas
- Dense urban environments with unreliable links

Traditional systems rely on centralized approval APIs. When connectivity is lost, transactions cannot complete. Machines need to **authorize and verify locally** when the network is down.

### 4. Unbounded Access Is Unacceptable

Without constraints, granting a machine the ability to pay is reckless. A single compromised agent could drain an account. A bug could trigger runaway spending.

The alternative—blocking every payment on human approval—doesn't scale and defeats autonomy.

**We need bounded authorization: machines can spend, but only within policy-defined limits.**

## What MPCP Provides

MPCP solves this by shifting approval **upstream**:

1. **Policy** — Defines rules: where, when, how much, and under what conditions spending is allowed
2. **Budget (SBA)** — Authorizes each specific payment (amount + destination), signed by the machine

The human (or policy administrator) approves a **grant** with a budget ceiling. The machine signs per-payment SBAs; the Trust Gateway enforces the ceiling and submits settlement. No per-transaction human approval required.

When the network is unavailable, the machine holds the policy chain onboard and can sign payments locally. The verifier (e.g., parking meter) validates the chain locally. No central backend is contacted at payment time.

## Next Steps

- [Design Goals](design-goals.md) — How MPCP differs from x402, AP2, and others
- [Reference Flow](../architecture/fleet-ev-reference-flow.md) — End-to-end EV charging scenario
- [Protocol: Artifacts](../protocol/artifacts.md) — The authorization chain
- [Offline Payments](../guides/fleet-payments.md#offline-flow) — How pre-authorized budgets enable offline payment
