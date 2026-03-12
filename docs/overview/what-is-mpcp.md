# What is MPCP?

The **Machine Payment Control Protocol (MPCP)** is a cryptographically enforced pipeline that enables machines—autonomous vehicles, robots, IoT devices, and AI agents—to perform financial transactions while remaining tightly constrained by policy.

## Core Idea

Machines need to **spend within bounds**, not ask for approval on every transaction. MPCP provides that control layer:

```
Policy → PolicyGrant → Budget (SBA) → Payment (SPA) → Settlement → Verification
```

Each step produces signed artifacts that constrain the next. The machine can execute payments autonomously—as long as it stays within the bounds established when the session and budget were granted.

## Key Characteristics

- **Bounded authorization** — Pre-authorized spending envelopes (budgets) instead of per-transaction approval
- **Deterministic verification** — Every settlement can be verified against the authorization chain
- **Settlement-agnostic** — Works with XRPL, EVM chains, Stripe, hosted providers, and other rails
- **Offline-capable** — Payments can complete when the network is unavailable (e.g., underground garage)
- **Policy-first** — All spending derives from explicit policy rules (rails, assets, destinations, caps)

## Who Is It For?

- **Fleet operators** — Pre-authorize vehicles for parking, charging, tolls
- **Parking and charging infrastructure** — Verify payments locally without calling a central backend
- **Autonomous system builders** — Give machines spending authority with cryptographic guardrails
- **Backend teams** — Integrate via SDK, service API, or CLI

## What MPCP Is Not

MPCP does **not**:

- Replace the settlement rail (XRPL, EVM, etc.) — it sits in front of it
- Define how money moves — it defines how authorization is granted and verified
- Require a specific blockchain — it is rail-agnostic
- Handle human-present card flows — it is designed for machine-initiated, bounded spending

## Next Steps

- [Problem Statement](problem-statement.md) — Why existing payment systems fail for machines
- [Comparison with Agent Protocols](comparison-with-agent-protocols.md) — How MPCP differs from x402, AP2, and others
- [Protocol: Artifacts](../protocol/artifacts.md) — The authorization chain in detail
