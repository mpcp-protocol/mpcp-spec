# System Model

MPCP models machine payments as a **cryptographic authorization chain** that sits above settlement rails.

## Overview

The system model has three layers:

| Layer | Role | Examples |
|-------|------|----------|
| **Policy** | Defines spending rules | Fleet operator policy, vendor allowlists, caps |
| **Authorization** | Bounds runtime spending | PolicyGrant, SBA, SPA |
| **Settlement** | Executes payment | XRPL, EVM, Stripe, hosted |

MPCP operates in the **authorization** layer. It does not replace or implement the settlement layer—it constrains what may be settled.

The canonical flow is: **Fleet Policy → PolicyGrant → SBA → SPA → SettlementIntent → Settlement**.

→ [Authorization Chain (visual diagram)](authorization-chain.md)

## Trust Model

- **Policy issuer** — Authority that defines rules (fleet operator, service operator)
- **Machine wallet** — Signs budgets and payment authorizations within policy
- **Verifier** — Validates the chain before allowing service or settlement
- **Settlement rail** — Executes the actual payment

Each step produces verifiable artifacts. The verifier can independently validate the full chain without trusting any single party.

## Key Properties

1. **Decoupled** — Policy, budget, and payment binding are separate concerns
2. **Verifiable** — Settlement can be checked against authorization chain
3. **Offline-capable** — Machine holds chain onboard; verifier validates locally
4. **Rail-agnostic** — Same authorization model for any settlement backend

## See Also

- [Authorization Chain](authorization-chain.md) — The canonical visual diagram
- [Actors](actors.md)
- [Artifact Lifecycle](artifact-lifecycle.md)
- [Reference Flow](reference-flow.md)
