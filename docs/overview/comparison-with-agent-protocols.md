# Comparison with Agent Protocols

MPCP is one of several protocols emerging for machine and agent payments. This page explains how
MPCP differs from **x402**, **AP2**, **ACP**, **TAPC**, and related approaches — and covers why
MPCP is the right authorization layer for human-to-agent spending delegation.

## Summary

| | MPCP | x402 | AP2 | ACP | TAPC |
|---|------|------|-----|-----|------|
| **Primary use case** | Physical machines + AI agents; bounded budget delegation | API access, pay-per-request | Agent commerce; mandate-based | Agent-to-agent communication | Agent payment negotiation |
| **Authorization model** | Pre-authorized budgets; spend within envelope | Per-request payment | Verifiable mandates (Cart, Intent) | Task/capability negotiation | Payment protocol inside agent tasks |
| **Offline** | Yes — pre-loaded chain, local verification | No — HTTP round-trip | No — online mandate exchange | No | No |
| **Settlement rails** | Any (XRPL, EVM, Stripe, hosted) | Stablecoins (USDC, EURC) | Cards, x402 | Rail-agnostic (unspecified) | Unspecified |
| **Approval flow** | Budget granted upstream; agent spends within bounds | Pay per API call | User signs Cart or Intent mandate | Capability exchange | Payment negotiation |
| **Human revocation** | Yes — `revocationEndpoint` | No | Yes (mandate expiry) | N/A | N/A |
| **Focus** | Bounded autonomy, verification, auditability | Micropayments, no API keys | Accountability, authenticity, user control | Agent interoperability | Agent payment flows |

---

## x402 Protocol

**x402** embeds payment into HTTP using the 402 "Payment Required" status code. An agent sends a
request; the server responds with 402 and payment instructions; the agent pays; the server verifies
and serves the response.

**How MPCP differs:**

1. **Per-request vs pre-authorized** — x402 is pay-per-call. MPCP uses pre-authorized budgets: you
   grant a spending envelope (e.g., $800 for a Paris trip) and the agent spends within it across
   multiple sessions. MPCP is designed for **multi-payment sessions**, not per-request API access.

2. **Online-only vs offline-capable** — x402 requires an HTTP round-trip at payment time. MPCP
   allows payments when the network is unavailable. A vehicle in an underground garage, or an agent
   operating in a low-connectivity environment, can sign payments locally.

3. **Physical machines vs API consumers** — x402 optimizes for agents paying for API access.
   MPCP optimizes for **machines and agents** paying for bounded real-world services — parking,
   charging, hotel bookings, transport — often in environments where connectivity is intermittent.

4. **Stablecoins vs rail-agnostic** — x402 is built around stablecoins on specific chains. MPCP
   defines the authorization chain; the settlement rail is a pluggable backend.

---

## AP2 (Agent Payments Protocol)

**AP2** extends Agent2Agent (A2A) and Model Context Protocol (MCP) with payment capabilities. It
uses Verifiable Digital Credentials (VDCs): Payment Mandate, Cart Mandate, and Intent Mandate.

**How MPCP differs:**

1. **Architecture** — AP2 is mandate-based: the user signs a Cart (human-present) or Intent
   (human-not-present) mandate, exchanged with merchants at payment time. MPCP is pipeline-based:
   Policy → Grant → Budget → Payment → Verification. MPCP focuses on **cryptographically bounded
   spending envelopes** that the agent can use without further online mandate exchange.

2. **Offline and physical machines** — AP2 assumes online mandate exchange. MPCP supports offline
   payment: the machine holds PolicyGrant + SBA onboard and signs payments when disconnected.

3. **Cards vs multi-rail** — AP2's initial focus is card payments, with x402 for crypto. MPCP is
   rail-agnostic from the start: XRPL, EVM, Stripe, hosted.

4. **Scope** — AP2 addresses accountability, authenticity, and authorization across agent commerce.
   MPCP addresses **bounded spending** in policy-defined sessions. Different problems, complementary
   potential.

---

## ACP (Agent Communication Protocol)

**ACP** (from BeeAI/IBM) is a REST-based protocol for agent-to-agent communication. It defines
how agents discover each other, exchange tasks, stream results, and coordinate work.

**Relationship to MPCP:**

ACP defines *what* the agent does (task exchange, capability discovery). MPCP bounds *how much*
the agent can spend while doing it. They operate at different layers and are complementary:

```
ACP:  Agent A → sends task → Agent B
MPCP: Agent B → spends $X  → within human-granted budget
```

MPCP sits **above** ACP as the spending authorization layer. An ACP agent executing a paid task
can carry an MPCP PolicyGrant to prove its spending authority to the service provider.

---

## TAPC (Task and Payment Coordination)

**TAPC** (emerging) defines how payment negotiation is embedded inside agent task flows. It
addresses payment initiation, confirmation, and receipt within agent-to-agent or agent-to-service
interactions.

**Relationship to MPCP:**

TAPC handles payment *negotiation and initiation*. MPCP handles *authorization and verification*
of the spending that results. They are complementary layers:

```
TAPC: Agent negotiates price with service → initiates payment
MPCP: PolicyGrant → SBA → SPA bounds what that payment can be
```

MPCP provides the cryptographic guarantees (bounded budget, signed chain, offline verification)
that a TAPC payment flow can leverage. The merchant verifies the MPCP chain independently of the
TAPC negotiation.

---

## Human-to-Agent Delegation with MPCP

See **[Why MPCP for AI Agent Spending](why-mpcp-for-agents.md)** for a dedicated explanation of:

- Why pre-authorized budgets fit human-to-agent delegation better than per-transaction mandates
- How MPCP complements MCP and ACP (task protocols + spending bounds)
- Key differentiators vs AP2 for multi-day trips
- When to use MPCP for agent spending

---

## When to Use MPCP

Use MPCP when:

- Machines or AI agents need to spend autonomously within policy limits
- Payments may work **offline** (vehicles in garages, agents in low-connectivity environments)
- You need **pre-authorized budgets** (session/trip spending envelopes) rather than per-request payment
- You want **any settlement rail** (XRPL, EVM, Stripe, hosted) with a single authorization model
- The human needs to **revoke** the agent's spending authority mid-delegation
- Verification and auditability of the authorization chain matter

Consider x402 when:

- You need pay-per-request API access payments
- Stablecoin micropayments fit your use case
- Online HTTP flow is acceptable

Consider AP2 when:

- You are building agent commerce on A2A/MCP
- Card payments and mandate-based flows are primary
- Human-present vs human-not-present transaction types are central

Use MPCP + ACP/MCP together when:

- You want task execution (ACP/MCP) with cryptographically bounded spending (MPCP)
- Your agent runtime needs to prove spending authority to service providers

---

## See Also

- [Human-to-Agent Delegation Profile](../profiles/human-agent-profile.md)
- [What is MPCP?](what-is-mpcp.md)
- [The Problem](problem.md)
- [Protocol: Artifacts](../protocol/artifacts.md)
