# MPCP Integration Guide

This guide maps every party in an MPCP deployment to the specific software they run, the SDK they integrate, and the existing infrastructure they connect it to. Start here if you are evaluating adoption.

---

## Quick reference

| You are… | Server software to run | SDK to integrate | Connects to |
|---|---|---|---|
| **Grant issuer** (fleet operator, AI platform, enterprise) | `mpcp-policy-authority` service | — | Your key store, your user/fleet DB, optionally Hedera or XRPL |
| **Wallet or AI agent** (issues SBAs, tracks budget) | Nothing | `mpcp-wallet-sdk` | Your agent runtime, your key store, your session state |
| **Merchant or service provider** (accepts MPCP payments) | Nothing | `mpcp-merchant-sdk` | Your existing HTTP backend (Express, Fastify, Next.js, or edge runtime) |
| **Embedded device or offline verifier** (firmware, kiosk, EV charger) | Nothing | `mpcp-reference` (lite) | Your firmware, your settlement rail, periodic connectivity for bundle refresh |

MPCP has exactly **one server component**: the Policy Authority. Every other party integrates a library.

---

## 1 — Grant issuers (Policy Authority)

**You are a grant issuer if**: you are the party that defines what a machine or agent is allowed to spend, signs the `PolicyGrant` artifact, and needs to be able to revoke it.

Typical roles: fleet operator, enterprise IT/IAM, AI agent platform, crypto wallet provider issuing spend limits to sub-agents.

### What you run

Deploy the [`mpcp-policy-authority`](https://github.com/mpcp-protocol/mpcp-policy-authority) service. It is a Node.js/Fastify HTTP service backed by SQLite. A single binary, no external database required.

```bash
git clone https://github.com/mpcp-protocol/mpcp-policy-authority
cd mpcp-policy-authority
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
  allowedRails: ["xrpl", "stripe"],
  allowedAssets: [{ standard: "ISO4217", code: "USD" }],
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

## 2 — Wallets and AI agents

**You are a wallet or agent if**: you receive a `PolicyGrant` on behalf of a machine or AI agent, and need to create `SignedBudgetAuthorizations` (SBAs) to authorise individual payments within the granted bounds.

Typical roles: vehicle OEM wallet, AI agent runtime (LangChain, custom Claude tool, AutoGPT), mobile wallet issuing to a sub-agent, IoT firmware.

### What you run

Nothing. The wallet SDK is a library. No server required.

### SDK API

```bash
npm install @mpcp/wallet-sdk
```

```typescript
import { createSession, MpcpBudgetExceededError, MpcpGrantRevokedError } from "@mpcp/wallet-sdk";

const session = await createSession(signedGrant, {
  actorId:       "agent:my-agent-id",
  signingKey:    process.env.AGENT_SIGNING_PRIVATE_KEY_PEM,
  signingKeyId:  "agent-key-1",
  scope:         "SESSION",
  ceiling:       { amount: "80000", currency: "USD" },  // $800 budget ceiling
  revocationTtl: 60_000,
  // Required when merchants use Trust Bundle key resolution instead of env-var key:
  // issuer: "vehicle:robox-7.fleet.robox.example",
});

// Budget enforcement, revocation checks, and spend tracking handled automatically.
// Throws MpcpBudgetExceededError if amount would exceed ceiling.
// Throws MpcpGrantRevokedError if the grant has been revoked.
let sba;
try {
  sba = await session.createSba({ amount: "2500", currency: "USD", rail: "stripe" });
} catch (err) {
  if (err instanceof MpcpBudgetExceededError) { /* handle */ }
  if (err instanceof MpcpGrantRevokedError)   { /* handle */ }
}

// Show remaining budget
const { remainingMinor } = await session.remaining();
```

#### `issuer` and Trust Bundle key resolution

When the merchant verifies SBAs using a pre-loaded Trust Bundle (rather than a configured env-var public key), the SBA envelope must carry an `issuer` field. The wallet-sdk session sets this automatically when `issuer` is provided in `SessionOptions`:

```typescript
const session = await createSession(signedGrant, {
  actorId:      "vehicle:robox-7",
  issuer:       "vehicle:robox-7.fleet.robox.example",  // must match Trust Bundle entry
  signingKey:   vehiclePrivKeyPem,
  signingKeyId: "vehicle-sba-key-1",
  // ...
});
```

Without `issuer`, the merchant-sdk verifier falls back to `MPCP_SBA_SIGNING_PUBLIC_KEY_PEM` for key lookup. For third-party infrastructure (toll terminals, EV chargers) that cannot be pre-configured with per-vehicle keys, Trust Bundles + `issuer` is the correct pattern.

#### Using mpcp-reference primitives directly

For environments that cannot run `mpcp-wallet-sdk` (e.g. constrained microcontrollers), use the reference SDK directly. Budget tracking must be implemented by the caller.

```typescript
import { createSignedSessionBudgetAuthorization } from "mpcp-service/sdk";

process.env.MPCP_SBA_SIGNING_PRIVATE_KEY_PEM = agentPrivateKeyPem;
process.env.MPCP_SBA_SIGNING_KEY_ID = "agent-key-1";

const sba = createSignedSessionBudgetAuthorization({
  sessionId:            crypto.randomUUID(),
  actorId:              "agent:my-agent-id",
  grantId:              grant.grantId,
  policyHash:           grant.policyHash,
  currency:             "USD",
  maxAmountMinor:       "2500",
  allowedRails:         grant.allowedRails,
  allowedAssets:        grant.allowedAssets,
  destinationAllowlist: grant.destinationAllowlist ?? [],
  expiresAt:            new Date(Date.now() + 3_600_000).toISOString(),
  issuer:               grant.issuer,  // pass through for Trust Bundle resolution
});
```

### Passing the SBA to a merchant

The merchant expects the SBA in the `Authorization` header:

```
Authorization: MPCP <base64(JSON.stringify(sba))>
```

or in the request body as `{ sba: <sba object> }` for non-HTTP protocols.

### Existing infrastructure it connects to

- **Key store**: the agent signing key must be held securely by the host runtime. The SDK accepts a PEM; in production, wrap this with your platform's key management (Secure Enclave, HSM, KMS).
- **Agent runtime**: drop `wallet.createSba(...)` into your tool execution path wherever a payment is triggered. No changes to your agent framework are required.
- **Session state**: by default the SDK tracks spend in memory. Inject a custom `SpendStorage` implementation to persist across restarts.

### Handling revocation mid-session

If the policy authority revokes the grant while the agent is active, the next `createSba` call returns `{ valid: false, error: { code: "grant_revoked" } }`. Your agent should treat this as a terminal signal and halt further payment attempts for this session.

---

## 3 — Merchants and service providers

**You are a merchant if**: you operate a backend that receives MPCP payment authorizations from agents or wallets and needs to verify them before processing a charge.

Typical roles: EV charging network backend, parking management platform, hotel PMS, SaaS API with metered billing, fleet servicing portal.

### What you run

Nothing. The merchant SDK is middleware. No server required.

> **Status**: `mpcp-merchant-sdk` is in active development (Phase 1: core verifier, revocation, spend tracking, Express middleware). The API shown below reflects the current implementation.

```bash
npm install @mpcp/merchant-sdk
```

### Integration: Express / Fastify

```typescript
import { mpcp } from "@mpcp/merchant-sdk/express";

// mpcp() returns an Express middleware; mount it before your route handler.
// It reads the SBA from the Authorization: MPCP <base64> header or req.body.sba,
// verifies the full chain, and attaches req.mpcp on success.
app.post("/charge", mpcp({
  amount:    req.body.amountMinor,         // requested amount in minor units
  currency:  "USD",
  merchantId: "did:web:ionity.eu",         // optional — enforces destinationAllowlist
  revocationTtl: 60_000,                   // cache revocation responses for 60 s
  trackSpend:    true,                     // enforce cumulative grant ceiling
}), (req, res) => {
  const { grant, amount, currency } = req.mpcp;
  // grant is verified; amount is within authorized bounds
  res.json({ status: "authorized", amount });
});
```

On failure the middleware returns `402 Payment Required` with a structured error body — your existing error handling catches it.

### Integration: Next.js edge runtime

```typescript
import { verifyMpcpEdge } from "@mpcp/merchant-sdk/edge";

export async function POST(req: Request) {
  const sba = await req.json();
  const result = await verifyMpcpEdge(sba, {
    amount: sba.authorization.maxAmountMinor,
    currency: "USD",
    trustBundles: await loadBundles(), // pre-fetched Trust Bundles
  });
  if (!result.valid) {
    return Response.json({ error: result.error }, { status: 402 });
  }
  // proceed
}
```

### What the SDK checks

The merchant SDK performs a full MPCP verification chain on every request:

1. **PolicyGrant signature** — verifies the grant was signed by the claimed policy authority (resolves key via `/.well-known/mpcp-keys.json` or Trust Bundle)
2. **SBA signature** — verifies the agent signed the budget authorization with the key recorded in the grant
3. **Revocation** — calls the `revocationEndpoint` from the grant (cached by TTL)
4. **Budget bounds** — confirms the requested amount does not exceed `maxAmountMinor`, accounting for cumulative spend if `trackSpend: true`
5. **Destination allowlist** — if `merchantId` is set, confirms it appears in the grant's `destinationAllowlist`

### Existing infrastructure it connects to

- **HTTP framework**: middleware drops into any existing Express, Fastify, or Next.js route. No changes to your routing or controller logic.
- **Payment processor**: the SDK sits *before* your existing payment code. Once `req.mpcp.valid` is true, pass the verified amount to Stripe, your XRPL submitter, or whatever rail you use.
- **Spend storage**: defaults to in-memory. Inject a database-backed `SpendStorage` implementation for production multi-instance deployments.
- **Key resolution**: the SDK fetches the policy authority's public key from its `/.well-known/mpcp-keys.json` endpoint and caches it. Alternatively pass `signingKeyPem` directly, or supply Trust Bundles for fully offline verification.

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

| Profile | Use when | intentHash required | Offline capable |
|---|---|---|---|
| **Lite** | Single-operator closed-loop (one fleet, one charging network) | No | Yes (via Trust Bundles) |
| **Full** | Multi-party pipelines where memo/metadata substitution matters (e.g. roaming between charging networks) | Yes | Yes (via Trust Bundles) |
| **Human-Agent** | A human delegates a spending budget to an AI agent | Yes | Partial (agent online; merchant may be offline) |

The profiles also determine how signatures chain:

- **Lite / Full**: Fleet Operator → Vehicle Wallet → Merchant (three-party chain)
- **Human-Agent**: Human (DID key) → AI Agent (session key) → Merchant (three-party chain; agent acts as session authority)

See [Lite Profile](../profiles/lite-profile.md), [Full Profile](../profiles/full-profile.md), and [Human-Agent Profile](../profiles/human-agent-profile.md) for normative details.

---

## 6 — End-to-end: how the pieces connect

```
GRANT ISSUER                    WALLET / AGENT              MERCHANT
─────────────────────────────   ─────────────────────────   ─────────────────────────
mpcp-policy-authority           mpcp-wallet-sdk             mpcp-merchant-sdk
  POST /policies                                              (middleware)
  POST /grants ──────────────→  parseGrant()
                PolicyGrant     createSession()
                                createSba()  ────────────→   mpcp()(req, res, next)
                                  SBA                          verifyPolicyGrant ✓
                                                               verifySba ✓
                                                               checkRevocation ✓
                                                               trackSpend ✓
                                                               → req.mpcp.valid = true
                                                             → existing payment logic
                                                             → settlement rail
```

If you are building a new system from scratch, start in this order:

1. Deploy `mpcp-policy-authority` and issue a test grant
2. Integrate `mpcp-wallet-sdk` to create an SBA from that grant
3. Integrate `mpcp-merchant-sdk` to verify the SBA
4. Add `mpcp-merchant-sdk` to your real payment endpoint
5. Add `mpcp-wallet-sdk` to your real agent or wallet runtime
6. Enable revocation and spend tracking
7. (Optional) Enable Trust Bundles for offline verification
8. (Optional) Enable on-chain anchoring for audit

---

## See also

- [Ecosystem](../ecosystem.md) — repository map and component roles
- [Actors](../architecture/actors.md) — protocol-level actor definitions
- [Reference Flow (Fleet EV)](../architecture/fleet-ev-reference-flow.md) — full end-to-end walkthrough for fleet charging
- [Reference Flow (Human-Agent)](../architecture/human-agent-reference-flow.md) — full end-to-end walkthrough for AI agent delegation
- [Trust Bundles](../protocol/trust-bundles.md) — offline key distribution
- [Build a Machine Wallet](./build-a-machine-wallet.md) — code quickstart
- [Fleet Payments](./fleet-payments.md) — fleet operator integration detail
