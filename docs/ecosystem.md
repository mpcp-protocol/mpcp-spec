# MPCP Ecosystem

MPCP is a protocol, not a product. Adoption requires implementations at every layer of the stack — from the signing key in a wallet to the verification logic in a merchant backend. This document describes the full ecosystem: the repositories, the role of each, how they connect, and the status of each component.

---

## End-goal architecture

```
  Human / Fleet Operator
        │
        │  issues PolicyGrant (signs with DID key)
        ▼
  ┌─────────────────────────────┐
  │   mpcp-policy-authority     │  Policy Authority service
  │   (or embedded in platform) │  stores + revokes grants, optional on-chain anchor
  └─────────────────────────────┘
        │
        │  PolicyGrant (signed artifact)
        ▼
  ┌─────────────────────────────┐
  │   mpcp-wallet-sdk           │  Wallet / AI Agent
  │   (machine wallet or agent) │  creates SBAs within grant bounds, tracks budget
  └─────────────────────────────┘
        │
        │  SignedBudgetAuthorization
        ▼
  ┌─────────────────────────────┐
  │   mpcp-merchant-sdk         │  Merchant / Service Provider
  │   (Express/Fastify/Next.js) │  verifies full chain, checks revocation, records spend
  └─────────────────────────────┘
        │
        │  SBA → Trust Gateway
        ▼
  XRPL Settlement  (Trust Gateway submits payment + mpcp/grant-id memo)
```

The protocol spec and reference implementation sit underneath all of this — they define the artifact formats, verification rules, and canonical SDK that every layer depends on.

---

## Repository map

| Repository | Role | Audience | Status |
|------------|------|----------|--------|
| mpcp-spec | Protocol specification — artifact formats, verification rules, profiles | Protocol implementers, researchers | Active |
| mpcp-reference | TypeScript reference implementation — canonical SDK, verifier, on-chain adapters, Trust Bundle | All implementers (SDK dependency) | Complete |
| mpcp-policy-authority | Deployable Policy Authority service — grant issuance, revocation, Trust Bundle issuance, on-chain anchoring | Operators, platforms, enterprises | Complete |
| mpcp-wallet-sdk | Wallet SDK — `createSession`, SBA signing, budget tracking, revocation; Node.js | Wallet developers, AI agent builders | Complete (Node.js) |
| mpcp-merchant-sdk | Merchant SDK — SBA verification middleware for Express, Fastify, Next.js, Edge; Trust Bundle key resolution | Merchant and service provider backends | Complete |
| mpcp-gateway | Transparent payment gateway — x402 interception, session budgets, policy controls, signed receipts, soft limits | Operators bridging non-MPCP agents | Complete (P1–P10) |
| mpcp-gateway-client | Agent-side gateway client — `GatewayClient`, `session.fetch()`, framework adapters | AI agent and automation developers | Active (P1–P3) |

---

## Actor-to-implementation mapping

Each actor in the MPCP protocol maps to one or more implementation components:

| Actor | Uses | Hosts |
|-------|------|-------|
| **Fleet Operator / Human delegator** | `mpcp-policy-authority` (or custom issuer) | Policy Authority service, revocation endpoint |
| **Vehicle Wallet / AI Agent (native MPCP)** | `mpcp-wallet-sdk` | SBA signing keys, session state |
| **AI Agent (gateway path)** | `mpcp-gateway-client` | — (delegates all crypto to the gateway) |
| **Merchant / Service Provider** | `mpcp-merchant-sdk` | Verification middleware |
| **Gateway operator** | `mpcp-gateway` | Session store, x402 proxy, payment rail |
| **Auditor / Verifier** | `mpcp-reference` verifier directly | — |
| **Protocol implementer** | `mpcp-spec` + `mpcp-reference` | — |

---

## Component roles in detail

### mpcp-reference — the protocol core

The canonical SDK. All other components depend on it. It provides:

- Artifact construction: `createPolicyGrant`, `createSignedPolicyGrant`, `createSba`
- Verification: `verifyPolicyGrant`, `verifySignedBudgetAuthorization`, `verifySettlement`
- On-chain adapters: `hederaHcsAnchorPolicyDocument`, `checkXrplNftRevocation`, `resolveXrplDid`
- Revocation utilities: `checkRevocation`
- Schemas and canonical JSON hashing

`mpcp-reference` is a low-level library — it requires protocol knowledge to use directly. The wallet and merchant SDKs are opinionated layers on top of it for specific deployment contexts.

---

### mpcp-policy-authority — the Policy Authority service

The production Policy Authority is the trust anchor for a deployment. It:

- Stores policy documents and issues `PolicyGrant` artifacts signed with its key
- Exposes `GET /revoke?grantId=` — the revocation endpoint that goes into every grant
- Optionally anchors policy documents on Hedera HCS or XRPL NFT for tamper-evident audit trails
- Manages soft-delete retention for policy document custody

For many deployments the policy authority will be embedded directly in an existing platform (an AI agent platform, an enterprise IAM system, a crypto wallet provider) rather than deployed as a standalone service. The `mpcp-policy-authority` repository is a ready-to-deploy reference implementation of this role.

See the [Ecosystem Roadmap](../roadmap/) for the full development plan.

---

### mpcp-wallet-sdk — the wallet / agent SDK

The wallet SDK is the integration point for **any actor that creates SBAs** — machine wallets in vehicles, AI agents operating on behalf of humans, or enterprise automation systems. It provides:

- **PolicyGrant display** — parse a received grant into human- or agent-readable form
- **SBA creation and signing** — `createSession(grant, signingKey)` → signs SBAs within authorized scope
- **Budget enforcement** — tracks cumulative spend, rejects requests that would exceed the grant ceiling
- **Revocation** — checks `revocationEndpoint` (and optionally XRPL NFT status) before each transaction
- **Persistence** — pluggable storage adapters (in-memory, localStorage, React Native AsyncStorage)
- **Platform support** — browser bundle (Web Crypto API), React Native, Node.js

**Not in scope**: UI components, key generation and custody (both are platform-specific concerns). The SDK operates on keys provided by the host application.

---

### mpcp-merchant-sdk — the merchant / service provider SDK

The merchant SDK is the integration point for **any actor that accepts MPCP-authorized payments**. It provides:

- **Verification middleware** for Express, Fastify, and Next.js (Edge compatible) — attaches a verified `mpcp` object to the request; returns structured 402 on failure
- **Revocation checking with caching** — automatic HTTP + optional on-chain check; configurable TTL to avoid per-transaction latency
- **Spend tracking** — enforces cumulative grant ceiling; idempotency key support for payment deduplication
- **Event hooks** — `payment.authorized`, `payment.rejected`, `grant.revoked` events for webhook dispatch and audit systems

The merchant SDK wraps `mpcp-reference` verification — it does not reimplement protocol logic.

---

## Integration flow

The end-to-end flow across all components:

```
1. POLICY AUTHORITY
   POST /policies        { policyDocument }   → { policyHash }
   POST /grants          { policyHash, ... }  → SignedPolicyGrant
        (optional: anchor on Hedera HCS or XRPL NFT)

2. WALLET / AGENT  (mpcp-wallet-sdk)
   parseGrant(signedGrant)                    → display / consent prompt
   createSession(grant, actorId, signingKey)  → Session
   session.createSba(amount, currency)        → SignedBudgetAuthorization

3. MERCHANT  (mpcp-merchant-sdk)
   mpcp()(req, res, next)                     → req.mpcp = { valid, grant, amount }
        internally: verifyPolicyGrant
                  + verifySba
                  + checkRevocation (cached)
                  + trackSpend

4. TRUST GATEWAY  (mpcp-gateway)
   SBA verified → XRPL Payment submitted with mpcp/grant-id memo
   txHash returned as settlement receipt
```

---

## What "protocol neutral" means in practice

MPCP deliberately does not dictate:

- **Identity system** — the policy authority can be a `did:web` domain, a `did:key`, an XRPL account, or any verifiable key. Enterprises use their IAM system; crypto wallets use their existing keys.
- **Settlement rail** — v1.0 uses XRPL + RLUSD via the Trust Gateway. The authorization model is designed to be extensible to other rails in future profiles.
- **Deployment topology** — the policy authority can be a standalone service, embedded in an agent platform, or part of a wallet provider backend.

This means each SDK has an adapters layer for the platform-specific concerns, while the protocol core remains stable.

---

## Adoption paths

### For merchant and service provider teams

1. Install `mpcp-merchant-sdk`
2. Add the middleware: `app.use(mpcp({ revocationTtl: 60 }))`
3. Read `req.mpcp.grant` to get the authorized scope; `req.mpcp.amount` to confirm payment bounds
4. Existing revocation, spend tracking, and settlement recording are handled by the SDK

Estimated integration: a few hours for a standard Express or Fastify backend.

---

### For wallet developers and AI agent platforms

1. Install `mpcp-wallet-sdk`
2. Receive a `PolicyGrant` from the policy authority (delivered out-of-band — via API, QR, deep link)
3. Call `parseGrant(grant)` to display scope and bounds to the user or agent
4. Call `createSession(grant, actorId, signingKey)` to open a payment session
5. Call `session.createSba(amount, currency)` for each transaction — SDK enforces budget and revocation automatically

Estimated integration: a few hours for a standard agent that already holds signing keys.

---

### For operators building a Policy Authority

Deploy `mpcp-policy-authority` as a service (Docker Compose, one command) or integrate `mpcp-reference` SDK primitives directly into an existing backend. See the [Integration Guide](../guides/integration-guide/) for setup details.

---

## Current implementation status

| Component | Status | Notes |
|-----------|--------|-------|
| `mpcp-spec` | Complete | Protocol spec, profiles, guides |
| `mpcp-reference` | Complete | Canonical SDK, verifier, Trust Bundle, on-chain adapters |
| `mpcp-policy-authority` | Complete | Grant issuance, revocation, Trust Bundle issuance, audit log |
| `mpcp-wallet-sdk` | Complete (Node.js) | `createSession`, SBA signing, budget enforcement, SQLite persistence |
| `mpcp-merchant-sdk` | Complete | Express / Fastify / Next.js / Edge adapters; Trust Bundle key resolution |
| `mpcp-gateway` | Complete (P1–P10) | x402 proxy, session API, receipts, policy controls, soft limits, x402 merchant mode, SQLite |
| `mpcp-gateway-client` | Active — P1 | Core client in progress; P2–P4 planned |

For a step-by-step guide to integrating each component see the [Integration Guide](guides/integration-guide.md).
