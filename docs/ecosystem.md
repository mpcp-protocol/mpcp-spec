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
  │   mpcp-gateway-client       │  AI Agent / Automation
  │   (session.fetch wrapper)   │  budget-bounded fetch; gateway handles MPCP internals
  └─────────────────────────────┘
        │
        │  POST /proxy (session token)
        ▼
  ┌─────────────────────────────┐
  │   mpcp-gateway              │  Trust Gateway
  │   (session, x402, receipts) │  SBA signing, budget enforcement, x402 settlement
  └─────────────────────────────┘
        │
        │  Payment + mpcp/grant-id memo
        ▼
  XRPL Settlement  (Trust Gateway submits payment)
```

The protocol spec and reference implementation sit underneath all of this — they define the artifact formats, verification rules, and canonical SDK that every layer depends on.

---

## Repository map

| Repository | Role | Audience | Status |
|------------|------|----------|--------|
| mpcp-spec | Protocol specification — artifact formats, verification rules, profiles | Protocol implementers, researchers | Active |
| mpcp-reference | TypeScript reference implementation — canonical SDK, verifier, on-chain adapters, Trust Bundle | All implementers (SDK dependency) | Complete (Phase 1–6) |
| mpcp-policy-authority | Deployable Policy Authority service — grant issuance, revocation, Trust Bundle issuance, on-chain anchoring | Operators, platforms, enterprises | Complete |
| mpcp-gateway | Transparent payment gateway — x402 interception, session budgets, policy controls, signed receipts, soft limits | Gateway operators | Complete (P1–P10) |
| mpcp-gateway-client | Agent-side gateway client — `GatewayClient`, `session.fetch()`, framework adapters, receipts, Trust Bundle | AI agent and automation developers | Complete (P1–P6) |
| mpcp-wallet-sdk | ~~Wallet SDK~~ — archived; superseded by `mpcp-gateway-client` | Legacy | Archived |
| mpcp-merchant-sdk | ~~Merchant SDK~~ — archived; superseded by gateway enforcement + `mpcp-service` | Legacy | Archived |

---

## Actor-to-implementation mapping

Each actor in the MPCP protocol maps to one or more implementation components:

| Actor | Uses | Hosts |
|-------|------|-------|
| **Fleet Operator / Human delegator** | `mpcp-policy-authority` (or custom issuer) | Policy Authority service, revocation endpoint |
| **AI Agent / Automation** | `mpcp-gateway-client` | — (delegates all crypto to the gateway) |
| **Gateway operator** | `mpcp-gateway` | Session store, x402 proxy, payment rail |
| **Merchant / Service Provider** | Gateway enforcement (Trust Bundle + `X-Mpcp-Sba`) | Verification via gateway-signed artifacts |
| **Embedded / Offline verifier** | `mpcp-reference` verifier + Trust Bundles | Local signature verification |
| **Auditor / Verifier** | `mpcp-reference` verifier directly | — |
| **Protocol implementer** | `mpcp-spec` + `mpcp-reference` | — |

---

## Component roles in detail

### mpcp-reference — the protocol core

The canonical SDK. All other components depend on it. It provides:

- Artifact construction: `createPolicyGrant`, `createSignedPolicyGrant`, `createSba`
- Verification: `verifyPolicyGrant`, `verifySignedBudgetAuthorization`, `verifySettlement`
- On-chain adapters: `hederaHcsAnchorPolicyDocument`, active-grant credential verification, `resolveXrplDid`
- Revocation utilities: `checkRevocation`
- Schemas and canonical JSON hashing

`mpcp-reference` is a low-level library — it requires protocol knowledge to use directly. `mpcp-gateway-client` provides a high-level agent-facing API on top of the gateway, which in turn uses `mpcp-reference` server-side.

---

### mpcp-policy-authority — the Policy Authority service

The production Policy Authority is the trust anchor for a deployment. It:

- Stores policy documents and issues `PolicyGrant` artifacts signed with its key
- Exposes `GET /revoke?grantId=` — the revocation endpoint that goes into every grant
- Optionally anchors policy documents on Hedera HCS for tamper-evident audit trails; XRPL grant liveness uses XLS-70 Credentials
- Manages soft-delete retention for policy document custody

For many deployments the policy authority will be embedded directly in an existing platform (an AI agent platform, an enterprise IAM system, a crypto wallet provider) rather than deployed as a standalone service. The `mpcp-policy-authority` repository is a ready-to-deploy reference implementation of this role.

See the [Ecosystem Roadmap](../roadmap/) for the full development plan.

---

### mpcp-gateway-client — the agent / automation SDK

The gateway client is the integration point for **any agent or automation that makes payments through the Trust Gateway**. It provides:

- **Session lifecycle** — `createSession(config)` → `GatewaySession` with budget, purposes, expiry
- **Drop-in fetch** — `session.fetch(url)` proxies requests through the gateway; x402 settlement is automatic
- **Soft-limit continuation** — `onSoftLimit` callback lets the user approve budget increases mid-session
- **Framework adapters** — LangChain `GatewayFetchTool`, Vercel AI SDK `gatewayFetchTool`, generic function-calling `gatewayFetchFn`
- **React hooks** — `usePolicyGrant`, `useGatewaySession` for browser-based agent UIs
- **Receipts + audit** — `getReceipts()`, `verifyReceipt()` (Ed25519), `fetchGatewayKeys()`
- **Trust Bundle** — `fetchGatewayTrustBundle()` for `mpcp-service` verifier integration

**Zero runtime dependencies.** Pure `fetch`; works in Node.js 18+, browsers, and edge runtimes.

---

### Archived: mpcp-wallet-sdk and mpcp-merchant-sdk

These SDKs are **archived** (read-only) as of MPCP v1.0 ecosystem consolidation:

- **`mpcp-wallet-sdk`** — superseded by `mpcp-gateway-client`. New agent code should use `GatewayClient` / `session.fetch()` instead of embedding `@mpcp/agent` signing or duplicate grant logic. The gateway handles SBA issuance, budget enforcement, and revocation server-side.
- **`mpcp-merchant-sdk`** — superseded by gateway enforcement. Production merchants verify gateway-issued authorization (`X-Mpcp-Sba`, receipts, Trust Bundle). For custom standalone verifiers, use `mpcp-service` primitives directly.

Existing published npm versions continue to resolve; no new features will be added.

---

## Integration flow

The end-to-end flow across all components:

```
1. POLICY AUTHORITY
   POST /policies        { policyDocument }   → { policyHash }
   POST /grants          { policyHash, ... }  → SignedPolicyGrant
        (optional: anchor policy hash on Hedera HCS; XRPL grant liveness via XLS-70 Credentials)

2. AGENT  (mpcp-gateway-client)
   gw.createSession({ budget, purposes, expiresAt })  → GatewaySession
   session.fetch(url, { purpose })                     → merchant response
        internally: gateway issues SBA, enforces budget, handles x402

3. TRUST GATEWAY  (mpcp-gateway)
   Session budget/purpose/velocity checks
   x402 interception → XRPL Payment submitted with mpcp/grant-id memo
   Signed receipt returned

4. MERCHANT
   Receives payment via standard x402 or gateway-signed SBA
   Verifies via Trust Bundle (GET /.well-known/mpcp-trust-bundle.json)
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

### For AI agent and automation developers

1. Install `mpcp-gateway-client`
2. Create a `GatewayClient` with your gateway URL and API key
3. Call `gw.createSession({ budget, purposes, expiresAt })` to open a bounded session
4. Use `session.fetch(url)` wherever your agent makes paid requests — payments happen automatically

Estimated integration: minutes. No MPCP protocol knowledge required.

```typescript
import { GatewayClient } from "mpcp-gateway-client";

const gw = new GatewayClient({ gatewayUrl: "https://gw.example.com", apiKey: "..." });
const session = await gw.createSession({
  budget: { amount: "80000", currency: "USD" },
  purposes: ["travel:hotel", "travel:flight"],
  expiresAt: new Date(Date.now() + 86_400_000).toISOString(),
});

const res = await session.fetch("https://api.hotel.com/book", {
  method: "POST",
  body: JSON.stringify({ room: "deluxe", nights: 2 }),
});
```

---

### For merchants accepting gateway-routed payments

Merchants receiving payments via the Trust Gateway need no MPCP SDK. The gateway handles x402 settlement. For independent SBA verification, fetch the gateway's Trust Bundle:

```
GET https://gw.example.com/.well-known/mpcp-trust-bundle.json
```

Pass it to `mpcp-service` verifiers (`verifyMpcp`, `verifyBudgetAuthorization`) as `{ trustBundles: [bundle] }`.

---

### For operators building a Policy Authority

Deploy `mpcp-policy-authority` as a service (Docker Compose, one command) or integrate `mpcp-reference` SDK primitives directly into an existing backend. See the [Integration Guide](../guides/integration-guide/) for setup details.

---

## Current implementation status

| Component | Status | Notes |
|-----------|--------|-------|
| `mpcp-spec` | Complete | Protocol spec, profiles, guides |
| `mpcp-reference` | Complete (Phase 1–6) | Canonical SDK, verifier, Trust Bundle, on-chain adapters, conformance badge |
| `mpcp-policy-authority` | Complete | Grant issuance, revocation, Trust Bundle issuance, audit log |
| `mpcp-gateway` | Complete (P1–P10) | x402 proxy, session API, receipts, policy controls, soft limits, x402 merchant mode, SQLite |
| `mpcp-gateway-client` | Complete (P1–P6) | Core client, soft limits, framework adapters, React hooks, receipts, Trust Bundle |
| `mpcp-wallet-sdk` | Archived | Superseded by `mpcp-gateway-client` |
| `mpcp-merchant-sdk` | Archived | Superseded by gateway enforcement + `mpcp-service` |

For a step-by-step guide to integrating each component see the [Integration Guide](guides/integration-guide.md).
