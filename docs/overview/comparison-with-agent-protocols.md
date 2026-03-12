# Comparison with Agent Protocols

MPCP is one of several protocols emerging for machine and agent payments. This page explains how MPCP differs from **x402**, **AP2**, and related approaches.

## Summary

| | MPCP | x402 | AP2 |
|---|------|------|-----|
| **Primary use case** | Physical machines (vehicles, robots), fleet payments, variable sessions | API access payments, pay-per-request | Agent commerce, human-present and human-not-present |
| **Authorization model** | Pre-authorized budgets; spend within envelope | Per-request payment; pay when you call | Verifiable mandates (Cart, Intent, Payment) |
| **Offline** | Yes — pre-loaded policy chain, local verification | No — HTTP round-trip required | No — online mandate exchange |
| **Settlement rails** | Any (XRPL, EVM, Stripe, hosted) | Stablecoins (USDC, EURC) on supported chains | Cards, x402 |
| **Approval flow** | Session/budget granted upstream; machine spends within bounds | Agent pays per API call | Mandate-based; user signs Cart or Intent |
| **Focus** | Bounded autonomy, verification, auditability | Micropayments, no API keys | Accountability, authenticity, user control |

---

## x402 Protocol

**x402** embeds payment into HTTP using the 402 "Payment Required" status code. An agent sends a request; the server responds with 402 and payment instructions; the agent pays; the server verifies and serves the response.

**How MPCP differs:**

1. **Per-request vs pre-authorized** — x402 is pay-per-call: you pay when you make an API request. MPCP uses pre-authorized budgets: you grant a spending envelope (e.g., $30 for parking) and the machine spends within it. MPCP is designed for **sessions** with variable numbers of transactions, not per-request API access.

2. **Online-only vs offline-capable** — x402 requires an HTTP round-trip at payment time. MPCP allows payments when the network is unavailable. A vehicle in an underground garage can sign a payment locally; the parking meter verifies the MPCP chain locally. No central backend is contacted.

3. **Physical machines vs API consumers** — x402 optimizes for agents paying for API access (micropayments, pay-per-request). MPCP optimizes for **physical machines** (vehicles, robots, IoT) paying for parking, charging, tolls, and infrastructure access—often in environments where connectivity is intermittent.

4. **Stablecoins vs rail-agnostic** — x402 is built around stablecoin payments on specific chains. MPCP is settlement-agnostic: it defines the authorization chain; the settlement rail (XRPL, EVM, Stripe, hosted) is a pluggable backend.

---

## AP2 (Agent Payments Protocol)

**AP2** extends the Agent2Agent (A2A) and Model Context Protocol (MCP) with payment capabilities. It uses Verifiable Digital Credentials (VDCs): Payment Mandate, Cart Mandate, and Intent Mandate.

**How MPCP differs:**

1. **Architecture** — AP2 is mandate-based: the user signs a Cart (human-present) or Intent (human-not-present) mandate, and the agent exchanges these with merchants. MPCP is pipeline-based: Policy → Grant → Budget → Payment → Verification. MPCP focuses on **cryptographically bounded spending envelopes** rather than mandate negotiation.

2. **Offline and physical machines** — AP2 assumes online mandate exchange. MPCP supports offline payment: the machine holds PolicyGrant + SignedBudgetAuthorization onboard and can sign payments when disconnected. This is critical for vehicles in garages, tunnels, or charging facilities.

3. **Cards vs multi-rail** — AP2's initial focus is card payments, with x402 for crypto. MPCP is rail-agnostic from the start: XRPL, EVM, Stripe, hosted—the authorization chain is independent of the settlement rail.

4. **Scope** — AP2 addresses accountability, authenticity, and authorization across agent commerce. MPCP addresses **bounded machine spending** in policy-defined sessions. Different problems, complementary potential.

---

## When to Use MPCP

Use MPCP when:

- Machines (vehicles, robots, IoT) need to spend autonomously within policy limits
- Payments must work **offline** (underground, tunnels, intermittent connectivity)
- You need **pre-authorized budgets** (session-based spending envelopes) rather than per-request payment
- You want **any settlement rail** (XRPL, EVM, Stripe, hosted) with a single authorization model
- Verification and auditability of the authorization chain matter

Consider x402 when:

- You need pay-per-request API access payments
- Stablecoin micropayments fit your use case
- Online HTTP flow is acceptable

Consider AP2 when:

- You are building agent commerce on A2A/MCP
- Card payments and mandate-based flows are primary
- Human-present vs human-not-present transaction types are central

---

## See Also

- [What is MPCP?](what-is-mpcp.md)
- [The Problem](problem.md)
- [Protocol: Artifacts](../protocol/artifacts.md)
