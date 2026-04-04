# MPCP Integration Guide

This guide maps every party in an MPCP deployment to the specific software they run, the SDK they integrate, and the existing infrastructure they connect it to. Start here if you are evaluating adoption.

---

## Quick reference

| You are… | Server software to run | SDK to integrate | Connects to |
|---|---|---|---|
| **Grant issuer** (fleet operator, AI platform, enterprise) | `mpcp-policy-authority` service | — | Your key store, your user/fleet DB, optionally Hedera or XRPL |
| **AI agent or automation** (makes payments within a budget) | Nothing | `mpcp-gateway-client` | Your agent runtime, Trust Gateway |
| **Gateway operator** (runs the Trust Gateway) | `mpcp-gateway` | — | XRPL, session store |
| **Merchant or service provider** (accepts gateway-routed payments) | Nothing | Gateway Trust Bundle (optional `mpcp-service` for SBA verification) | Your existing HTTP backend |
| **Embedded device or offline verifier** (firmware, kiosk, EV charger) | Nothing | `mpcp-reference` (lite) | Your firmware, your settlement rail, periodic connectivity for bundle refresh |

MPCP has **two server components**: the Policy Authority and the Trust Gateway. Agents and merchants integrate libraries.

---

## 1 — Grant issuers (Policy Authority)

**You are a grant issuer if**: you are the party that defines what a machine or agent is allowed to spend, signs the `PolicyGrant` artifact, and needs to be able to revoke it.

Typical roles: fleet operator, enterprise IT/IAM, AI agent platform, crypto wallet provider issuing spend limits to sub-agents.

### What you run

Deploy the `mpcp-policy-authority` service. It is a Node.js/Fastify HTTP service backed by SQLite. A single binary, no external database required.

```bash
npm install && npm run build

MPCP_POLICY_GRANT_SIGNING_PRIVATE_KEY_PEM="$(cat your-key.pem)" \
MPCP_POLICY_GRANT_SIGNING_KEY_ID="pa-key-1" \
MPCP_ISSUER_DOMAIN="pa.your-domain.com" \
MPCP_REVOCATION_BASE_URL="https://pa.your-domain.com" \
npm start
```

The service exposes:

| Endpoint | What it does |
|---|---|
| `POST /policies` | Store a policy document; returns `policyHash` |
| `POST /grants` | Issue a signed `PolicyGrant`; links to a stored policy |
| `GET /revoke?grantId=` | Revocation check endpoint — this URL goes into every issued grant |
| `POST /revoke` | Revoke a grant immediately |
| `GET /.well-known/mpcp-keys.json` | JWKS endpoint — merchants and agents resolve your signing key here |
| `POST /trust-bundles` | Issue signed Trust Bundles for offline verifiers |
| `GET /trust-bundles` | Distribute bundles; supports `?category=`, `?merchant=`, `?region=` |

### Existing infrastructure it connects to

- **Key management**: the signing private key is passed as a PEM environment variable. In production, source it from AWS Secrets Manager, GCP KMS, Vault, or an HSM. New API keys are issued via `POST /admin/keys`; individual keys are revoked via `DELETE /admin/keys/:keyId`.
- **Your user or fleet database**: policy documents reference your own entitlement data. You call `POST /policies` from your existing provisioning flow (when a user sets up a budget, when a fleet vehicle is provisioned, etc.).
- **Revocation trigger**: call `POST /grants/:grantId/revoke` from any existing revocation surface — a user pressing "cancel" in your app, an account suspension flow, a fraud detection system.
- **On-chain anchoring (optional)**: if you need tamper-evident audit trails, configure `MPCP_HCS_*` (Hedera) or `MPCP_XRPL_*` (XRPL). Anchoring is fire-and-forget — it does not affect issuance latency.

### Alternative: embed in an existing backend

If you do not want a separate service, you can call `mpcp-reference` SDK primitives directly from your existing backend:

```typescript
import { createSignedPolicyGrant } from "mpcp-service/sdk";

const grant = createSignedPolicyGrant({
  grantId: crypto.randomUUID(),
  policyHash: yourPolicyHash,
  expiresAt: new Date(Date.now() + 7 * 86_400_000).toISOString(),
  allowedRails: ["xrpl"],
  allowedAssets: [{ kind: "IOU", currency: "RLUSD", issuer: "rIssuer..." }],
  authorizedGateway: "rTrustGateway...",
  velocityLimit: { maxPayments: 500, windowSeconds: 86400 },
  maxAmountMinor: "50000",
  currency: "USD",
}, { issuer: "pa.your-domain.com", keyId: "pa-key-1" });
```

In this case you are responsible for storage, revocation endpoint exposure, and JWKS hosting.

### Delivering grants to agents and wallets

MPCP does not specify a transport for delivering a `PolicyGrant` to the wallet or agent. Common patterns:

- **API**: call your platform API from the agent runtime on session start; grant returned as a signed JSON object
- **QR code / deep link**: encode the signed grant for human-initiated delegation (e.g. Alice scans a QR in her AI assistant app)
- **Push**: embed the grant in a provisioning message (MQTT, push notification, embedded firmware image at manufacture)

---

## 2 — AI agents and automations

**You are an agent if**: you operate an AI agent or automation that needs to make paid requests within a delegated budget — hotel bookings, API calls, fleet operations, or any service with a cost.

Typical roles: AI agent runtime (LangChain, Vercel AI, AutoGen, custom), enterprise automation, fleet vehicle software.

### What you run

Nothing. `mpcp-gateway-client` is a library. No server required — the Trust Gateway handles all MPCP internals.

### SDK API

```bash
npm install mpcp-gateway-client
```

```typescript
import { GatewayClient } from "mpcp-gateway-client";

const gw = new GatewayClient({
  gatewayUrl: "https://gw.example.com",
  apiKey: process.env.GATEWAY_API_KEY,
});

const session = await gw.createSession({
  budget:   { amount: "80000", currency: "USD" },   // $800 ceiling
  purposes: ["travel:hotel", "travel:flight"],
  expiresAt: new Date(Date.now() + 86_400_000).toISOString(),
});

// Agent makes requests — gateway handles SBA issuance, budget, x402 settlement
const res = await session.fetch("https://api.hotel.com/book", {
  method: "POST",
  body: JSON.stringify({ room: "deluxe", nights: 2 }),
});

// Check remaining budget
const { allocatedMinor, budgetMinor } = await session.remaining();
```

#### Framework adapters

For AI agent frameworks, use the built-in tool wrappers:

```typescript
// LangChain
import { GatewayFetchTool } from "mpcp-gateway-client/langchain";
const tools = [new GatewayFetchTool({ session })];

// Vercel AI SDK
import { gatewayFetchTool } from "mpcp-gateway-client/ai-sdk";
const tools = { fetch: gatewayFetchTool(session) };

// Generic function-calling (AutoGen, OpenAI, etc.)
import { gatewayFetchFn } from "mpcp-gateway-client/function-calling";
const { fn, schema } = gatewayFetchFn(session);
```

#### Soft-limit continuation

When a session's budget is exhausted, the gateway can pause instead of failing. Handle this with an `onSoftLimit` callback:

```typescript
const session = await gw.createSession(
  { ..., softLimit: true },
  {
    onSoftLimit: async ({ continueToken, purpose, url }) => {
      const approved = await askUser(`Extend budget for ${purpose}?`);
      if (approved) {
        await gw.continueSession(session.id, continueToken, "10000");
        return true;  // retry automatically
      }
      return false;   // throw GatewaySoftLimitError
    },
  },
);
```

#### Receipts and audit

```typescript
const receipts = await gw.getReceipts(session.id);
const keys     = await gw.fetchGatewayKeys();

for (const r of receipts) {
  const valid = await verifyReceipt(r, keys[0]);
  console.log(`${r.merchant} ${r.amountMinor} ${valid ? "✓" : "INVALID"}`);
}
```

#### Using mpcp-reference primitives directly

For environments that cannot use the gateway (constrained microcontrollers, offline-only firmware), use `mpcp-service` SDK directly. Budget tracking must be implemented by the caller. See section 4 (Embedded devices) below.

### Existing infrastructure it connects to

- **Agent runtime**: replace `fetch(url)` with `session.fetch(url)` wherever a paid request is triggered. No changes to your agent framework are required.
- **Trust Gateway**: the gateway manages session state, SBA issuance, budget enforcement, and XRPL settlement. Your agent only needs the gateway URL and an API key.

### Handling revocation mid-session

If the policy authority revokes the grant while the agent is active, the next `session.fetch()` call throws `GatewayGrantRevokedError`. Your agent should treat this as a terminal signal and halt further payment attempts for this session.

---

## 3 — Merchants and service providers

**You are a merchant if**: you operate a backend that receives payments from agents via the Trust Gateway.

Typical roles: EV charging network backend, parking management platform, hotel PMS, SaaS API with metered billing, fleet servicing portal.

### Gateway-routed payments (recommended)

Most merchants receive payments routed through the Trust Gateway via x402. In this model, **no MPCP SDK is required** — the gateway handles settlement and the merchant receives a standard payment.

For merchants that want to independently verify gateway-issued SBAs (e.g. from the `X-Mpcp-Sba` header), fetch the gateway's Trust Bundle once at startup:

```typescript
const bundle = await fetch(
  "https://gw.example.com/.well-known/mpcp-trust-bundle.json"
).then(r => r.json());
```

Then use `mpcp-service` verifiers:

```typescript
import { verifySignedBudgetAuthorization } from "mpcp-service/sdk";

const result = verifySignedBudgetAuthorization(sba, {
  trustBundles: [bundle],
});
```

### What the gateway enforces

The Trust Gateway performs the full MPCP verification chain on every proxied request:

1. **Session validity** — active, not expired, not revoked
2. **Purpose check** — request purpose is in the session's `purposes` list
3. **Merchant allowlist/blocklist** — target URL matches allowed patterns
4. **Velocity limits** — max payments/hour, max amount per merchant/day
5. **Budget ceiling** — cumulative spend does not exceed session budget
6. **x402 settlement** — if the merchant responds 402, the gateway executes payment and retries

Merchants behind the gateway receive the cleared response. The gateway signs receipts for audit.

### Existing infrastructure it connects to

- **HTTP backend**: no middleware required. Payments arrive as standard HTTP requests (post-x402 settlement).
- **Independent verification (optional)**: fetch the gateway Trust Bundle for offline SBA verification. No env-var key configuration needed.
- **Receipts**: agents can retrieve signed receipts via `gw.getReceipts(sessionId)` for reconciliation.

---

## 4 — Embedded devices and offline verifiers

**You are an embedded verifier if**: you operate hardware that processes MPCP payment authorizations without reliable connectivity — EV charging stations, parking meters, transit gates, kiosks.

### What you run

Nothing beyond your existing firmware. Embed `mpcp-reference` (or the lite subset) into your firmware build.

### Integration approach

The offline verification pattern uses Trust Bundles — signed, pre-distributed key packages that let the device verify MPCP artifact chains without a network call.

```typescript
import {
  verifyTrustBundle,
  verifySignedSessionBudgetAuthorizationForDecision,
  type TrustBundle,
} from "mpcp-service/sdk";

// At startup (or after each bundle refresh) — raw fetch, no SDK helper needed:
const resp = await fetch(
  "https://pa.your-domain.com/trust-bundles" +
  "?category=ev-charging&merchant=did:web:ionity.eu&region=EU"
);
const { bundles } = await resp.json() as { bundles: TrustBundle[] };

// Verify each bundle's signature against the pre-installed root public key
// before storing. Discard any that fail or have expired.
const validBundles = bundles.filter(
  (b) => verifyTrustBundle(b, rootPublicKeyPem).valid
);

// At payment time (fully offline):
// Build a minimal decision from the SBA's own fields to drive verification.
const decision = {
  action:         "ALLOW" as const,
  reasons:        [],
  policyHash:     sba.authorization.policyHash,
  expiresAtISO:   sba.authorization.expiresAt,
  decisionId:     sba.authorization.budgetId,
  sessionGrantId: sba.authorization.grantId,
  priceFiat: {
    amountMinor: requestedAmountMinor,
    currency:    sba.authorization.currency,
  },
};

const result = verifySignedSessionBudgetAuthorizationForDecision(sba, {
  sessionId:            sba.authorization.sessionId,
  decision,
  trustBundles:         validBundles,
  cumulativeSpentMinor: localSpendTracker.get(sba.authorization.grantId) ?? "0",
});

if (result.ok) {
  authorizeCharge();
}
```

### Trust Bundle lifecycle

1. **Provisioning**: during manufacture or initial setup, install an initial set of Trust Bundles. These carry the public keys of all policy authorities the device will accept.
2. **Periodic refresh**: whenever connectivity is available, fetch updated bundles from `GET /trust-bundles?category=ev-charging&merchant=did:web:ionity.eu&region=EU`. Verify the bundle signature before replacing the stored copy.
3. **Expiry**: bundles carry an `expiresAt`. Devices MUST reject expired bundles. Build in a refresh margin — begin fetching before expiry to avoid a verification gap.

### Root key bootstrap

The public key of the bundle signer (the policy authority) cannot itself come from a bundle — this would be circular. Root keys must be installed:

- At manufacture time as a firmware constant
- Fetched once over TLS during initial device setup and then pinned
- Distributed by the fleet operator through a separate secure provisioning channel

### Offline revocation trade-off

Offline verifiers cannot call a revocation endpoint. A grant revoked by the policy authority will remain valid on an offline device until the device reconnects and refreshes its bundles. This is an acceptable risk for most deployments (charging sessions are short, grant `expiresAt` limits exposure). Deployments with stricter revocation requirements must use an online verification path.

---

## 5 — Choosing a deployment profile

Three profiles are defined; pick the one that fits your threat model:

| Profile | Use when | Offline capable |
|---|---|---|
| **Gateway** | Fleet or device payments; Trust Gateway enforces PA-signed budget ceiling + escrow | Yes (signature-only via Trust Bundles + `offlineMaxSinglePayment` cap) |
| **Human-Agent** | A human delegates a spending budget to an AI agent | Partial (agent online; merchant may be offline) |

Both profiles require a Trust Gateway for online payments. Signatures chain:

- **Gateway**: Fleet Operator (PA) → Trust Gateway → XRPL settlement
- **Human-Agent**: Human (DID key) → AI Agent (session key) → Trust Gateway → XRPL settlement

See [Transparent Gateway Profile](../profiles/gateway-profile.md) and [Human-Agent Profile](../profiles/human-agent-profile.md) for normative details.

---

## 6 — End-to-end: how the pieces connect

```
GRANT ISSUER                    AGENT                       GATEWAY                     MERCHANT
─────────────────────────────   ─────────────────────────   ─────────────────────────   ──────────────
mpcp-policy-authority           mpcp-gateway-client         mpcp-gateway
  POST /policies                                              (session + x402 proxy)
  POST /grants ──────────────→  gw.createSession(config)
                PolicyGrant     session.fetch(url) ────────→  budget / purpose check
                                                              x402 interception ───────→  merchant API
                                                              XRPL settlement
                                                              signed receipt
                                ← merchant response ────────  ← merchant response
```

If you are building a new system from scratch, start in this order:

1. Deploy `mpcp-policy-authority` and issue a test grant
2. Deploy `mpcp-gateway` (or use a hosted gateway)
3. Install `mpcp-gateway-client` in your agent and create a session
4. Use `session.fetch()` to make paid requests through the gateway
5. Verify receipts with `gw.getReceipts()` + `verifyReceipt()`
6. (Optional) Enable Trust Bundles for independent merchant-side SBA verification
7. (Optional) Enable on-chain anchoring for audit

---

## See also

- [Ecosystem](../ecosystem.md) — repository map and component roles
- [Actors](../architecture/actors.md) — protocol-level actor definitions
- [Reference Flow (Fleet EV)](../architecture/fleet-ev-reference-flow.md) — full end-to-end walkthrough for fleet charging
- [Reference Flow (Human-Agent)](../architecture/human-agent-reference-flow.md) — full end-to-end walkthrough for AI agent delegation
- [Trust Bundles](../protocol/trust-bundles.md) — offline key distribution
- [Build a Machine Wallet](./build-a-machine-wallet.md) — code quickstart
- [Fleet Payments](./fleet-payments.md) — fleet operator integration detail
