# Machine Payment Control Protocol (MPCP)

**Protocol Version: MPCP 1.0**

**A protocol for verifiable machine-to-service payments.**

Autonomous vehicles, AI agents, and machines increasingly pay for real-world services like parking, charging, and tolls.

## How MPCP works

A machine payment is accepted only if the recipient can verify a chain of signed artifacts:

**[Fleet Policy](protocol/FleetPolicyAuthorization.md) → [PolicyGrant](protocol/PolicyGrant.md) → [SignedBudgetAuthorization](protocol/SignedBudgetAuthorization.md) → [SignedPaymentAuthorization](protocol/SignedPaymentAuthorization.md) → [SettlementIntent](protocol/SettlementIntent.md) → Settlement**

Each step narrows what the machine is allowed to do.

→ [See the full reference flow](architecture/fleet-ev-reference-flow.md)

MPCP is not a settlement rail — it is the authorization layer above settlement.

## Specification Contents

- **Overview** — [What is MPCP](overview/what-is-mpcp.md), [Problem Statement](overview/problem-statement.md), [Design Goals](overview/design-goals.md)
- **Architecture** — [Authorization Chain](architecture/authorization-chain.md), [System Model](architecture/system-model.md), [Actors](architecture/actors.md), [Reference Flow](architecture/fleet-ev-reference-flow.md)
- **Protocol** — [MPCP Spec](protocol/mpcp.md), [Artifacts](protocol/artifacts.md), and artifact definitions (PolicyGrant, SBA, SPA, SettlementIntent, etc.)
- **Guides** — [Integration Guide](guides/integration-guide.md) (start here), [Build a Machine Wallet](guides/build-a-machine-wallet.md), [Fleet Payments](guides/fleet-payments.md), [Dispute Resolution](guides/dispute-resolution.md)
- **Diagrams** — [Visual reference](diagrams/)
- **Roadmap** — [Implementation roadmap](roadmap.md)

## Reference Implementation

The [reference implementation](https://mpcp-protocol.github.io/reference/) and [mpcp-reference repository](https://github.com/mpcp-protocol/mpcp-reference).
