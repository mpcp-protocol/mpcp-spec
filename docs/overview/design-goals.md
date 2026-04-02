# Design Goals

MPCP is designed around explicit goals that distinguish it from traditional payment systems and other agent payment protocols.

## Core Goals

### 1. Bounded Authorization

Machines must spend **within policy-defined limits**, not per transaction. Approval moves upstream: the human or policy administrator grants a session and budget; the machine spends autonomously within that envelope.

- No per-transaction wallet popups
- No unbounded access
- Cryptographically enforced constraints

### 2. Offline-Capable Payments

Payments must complete when the network is unavailable. Underground parking, tunnels, remote charging facilities—connectivity cannot be assumed.

- Pre-loaded policy chain onboard the machine
- Local verification by the service provider
- No central backend contact at payment time

### 3. Verifiable Chain

Every settlement must be independently verifiable against the authorization chain. PolicyGrant → SBA → Trust Gateway → XRPL Settlement forms a traceable, auditable sequence.

- Each step produces a signed or verifiable artifact
- On-chain `mpcp/grant-id` memo links every XRPL payment back to the originating grant
- Operators and auditors can trace from settlement receipt back to policy
- Deterministic verification rules

### 4. Settlement-Agnostic Policy

Policy and budget are expressed in abstract terms (caps, rails, destinations). Settlement details (tx hash, chain) are handled at execution and verification.

- Works with XRPL, EVM, Stripe, hosted—any rail
- One authorization model, pluggable settlement backends
- Rail-agnostic from the start

### 5. Separation of Concerns

Policy evaluation is distinct from budget authorization, which is distinct from settlement execution. Each layer can be audited, tested, and replaced independently.

- Minimal disclosure: SBA specifies only what is necessary for the current payment
- Trust Gateway enforces the policy ceiling independently of agent behavior

## Architecture Principles

The protocol follows a deliberate pipeline:

```
Policy
   ↓
PolicyGrant (session entry — PA-signed budget ceiling, escrow ref, authorized gateway)
   ↓
SignedBudgetAuthorization (per-payment authorization — amount + destination)
   ↓
Trust Gateway (enforces ceiling, manages escrow, submits XRPL Payment)
   ↓
XRPL Settlement (transaction hash + mpcp/grant-id memo)
```

This sequence ensures:

1. **Separation of concerns** — Each layer has a single responsibility
2. **Minimal disclosure** — No over-sharing of payment details
3. **Verifiable chain** — Signed artifacts at each step; on-chain audit via memo
4. **Settlement-agnostic policy** — Abstract constraints, concrete execution

## Comparison with Alternatives

| | MPCP | x402 | AP2 |
|---|------|------|-----|
| **Primary use case** | Physical machines, fleet payments, variable sessions | API access payments, pay-per-request | Agent commerce |
| **Authorization model** | Pre-authorized budgets | Per-request payment | Verifiable mandates |
| **Offline** | Yes | No | No |
| **Settlement rails** | Any | Stablecoins on supported chains | Cards, x402 |

See [Comparison with Agent Protocols](comparison-with-agent-protocols.md) for a detailed comparison.

## See Also

- [What is MPCP?](what-is-mpcp.md)
- [Problem Statement](problem-statement.md)
- [Reference Flow](../architecture/fleet-ev-reference-flow.md) — Full EV charging reference scenario
