# What is MPCP?

The **Machine Payment Control Protocol (MPCP)** is a cryptographically enforced pipeline that enables machines—autonomous vehicles, robots, IoT devices, and AI agents—to perform financial transactions while remaining tightly constrained by policy.

## Core Idea

Machines need to **spend within bounds**, not ask for approval on every transaction. MPCP provides that control layer:

```
PolicyGrant → SignedBudgetAuthorization (SBA) → Trust Gateway → XRPL Settlement
```

Each step narrows what the machine is allowed to do. The machine signs a per-payment SBA; the Trust Gateway verifies the chain, enforces the PA-signed budget ceiling, and submits the XRPL transaction.

## Key Characteristics

- **Bounded authorization** — Pre-authorized spending envelopes (budgets) instead of per-transaction approval
- **Deterministic verification** — Every settlement can be verified against the authorization chain; on-chain via `mpcp/grant-id` memo
- **XRPL-primary** — v1.0 uses XRPL escrow + RLUSD for settlement; other rails supported via future profiles
- **Offline-capable** — Payments can complete when the network is unavailable (e.g., underground garage)
- **Policy-first** — All spending derives from explicit policy rules (rails, assets, destinations, caps)

## Who Is It For?

- **Fleet operators** — Pre-authorize vehicles for parking, charging, tolls
- **Parking and charging infrastructure** — Verify payments locally without calling a central backend
- **Autonomous system builders** — Give machines spending authority with cryptographic guardrails
- **Backend teams** — Integrate via SDK, service API, or CLI

## What MPCP Is Not

MPCP does **not**:

- Replace the settlement rail — it sits in front of it as the authorization layer
- Define how money moves — it defines how authorization is granted and verified
- Require per-transaction approval — authorization is pre-granted within a policy envelope
- Handle human-present card flows — it is designed for machine-initiated, bounded spending

## Next Steps

- [Problem Statement](problem-statement.md) — Why existing payment systems fail for machines
- [Comparison with Agent Protocols](comparison-with-agent-protocols.md) — How MPCP differs from x402, AP2, and others
- [Protocol: Artifacts](../protocol/artifacts.md) — The authorization chain in detail
