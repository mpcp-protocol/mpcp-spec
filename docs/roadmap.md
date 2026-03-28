# MPCP Ecosystem Roadmap

MPCP development is tracked per-repository. Each repository has its own `ROADMAP.md` covering its specific implementation phases.

---

## Repositories

| Repository | Role | Roadmap |
|------------|------|---------|
| [mpcp-reference](https://github.com/mpcp-protocol/mpcp-reference) | Protocol core — canonical SDK, verifier, schemas, anchoring adapters, golden vectors | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-reference/blob/main/ROADMAP.md) |
| [mpcp-policy-authority](https://github.com/mpcp-protocol/mpcp-policy-authority) | Deployable policy authority service — grant issuance, revocation, Trust Bundle issuance, on-chain anchoring | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-policy-authority/blob/main/ROADMAP.md) |
| [mpcp-wallet-sdk](https://github.com/mpcp-protocol/mpcp-wallet-sdk) | Wallet SDK — session management, SBA signing, budget enforcement (Node.js + browser) | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-wallet-sdk/blob/main/ROADMAP.md) |
| [mpcp-merchant-sdk](https://github.com/mpcp-protocol/mpcp-merchant-sdk) | Merchant SDK — SBA verification, revocation caching, spend tracking, framework adapters (Express / Fastify / Next.js / Edge) | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-merchant-sdk/blob/main/ROADMAP.md) |
| [mpcp-gateway](https://github.com/mpcp-protocol/mpcp-gateway) | Transparent payment gateway — speaks x402 externally, enforces MPCP internally; bridges non-MPCP agents to MPCP merchants | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-gateway/blob/main/ROADMAP.md) |
| [mpcp-gateway-client](https://github.com/mpcp-protocol/mpcp-gateway-client) | Agent-side fetch wrapper — `GatewayClient` + `session.fetch()`; soft-limit continuation; LangChain / Vercel AI / AutoGen adapters | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-gateway-client/blob/main/ROADMAP.md) |
| [mpcp-spec](https://github.com/mpcp-protocol/mpcp-spec) | Protocol specification, architecture docs, guides | this site |

---

## Implementation status

### mpcp-reference

All core phases complete.

Implemented: canonical serialization · artifact schemas · full verification engine · CLI verifier with explain mode · Hedera HCS and XRPL anchor adapters · `did:xrpl` resolver · XRPL NFT revocation · Trust Bundle signing and verification · `resolveFromTrustBundle` for key lookup · AES-256-GCM encrypted policy anchoring · golden protocol vectors · human-to-agent delegation profile · TRIP budget scope · `checkRevocation` utility.

### mpcp-policy-authority

All phases complete. Grant issuance, policy custody, revocation endpoint, Trust Bundle issuance and signing, XRPL NFT mint/burn, persistent custody with soft-delete, audit log with webhook dispatch, multi-key admin API.

### mpcp-wallet-sdk

All core and ecosystem integration phases complete. Node.js monorepo (`@mpcp/core`, `@mpcp/agent`, `@mpcp/issuer`, `@mpcp/react`).

Implemented: `parseGrant` · `createSession(grant, opts)` → `Session` · `session.createSba({ amount, currency, rail })` · per-session budget ceiling enforcement · live revocation checking with TTL cache · `session.remaining()` · SQLite session persistence via Drizzle · Web Crypto signing path (`CryptoKey` support for browser) · `@mpcp/react` package (`usePolicyGrant`, `useSession` hooks) · `createX402Client` adapter (MPCP budget enforcement wrapping x402-gated APIs) · full integration test suite.

Deferred: React Native bundle + AsyncStorage adapter (PR7).

### mpcp-merchant-sdk

All phases complete. Full Express / Fastify / Next.js / Edge (Web Crypto) adapter suite.

Implemented: `verifyMpcp(sba, opts)` · `mpcp()` Express/Fastify middleware · `withMpcp()` Next.js HOC · `verifyMpcpEdge` (zero Node.js deps) · Trust Bundle key resolution (`trustBundles` option) · revocation checking with TTL cache · spend tracking · `verifyMpcpEdge` Ed25519 + P-256 support.

### mpcp-gateway

All phases (P1–P10) complete. The gateway bridges non-MPCP agents to MPCP merchants: intercepts HTTP 402, executes x402 payments, enforces session budgets/purposes/policies, and optionally attaches a signed SBA (`X-Mpcp-Sba`) so MPCP-aware merchants can verify the authorization chain.

Implemented:

- **P1** — Core proxy + x402 interception
- **P2** — Session CRUD REST API (`POST / GET / DELETE /sessions`)
- **P3** — Ed25519-signed receipts + audit log (`GET /sessions/:id/receipts`)
- **P4** — MPCP passthrough headers (`X-Mpcp-Sba` on 402 retry)
- **P5** — Production hardening: health/ready/metrics endpoints; pluggable `PaymentRail`; `KeyRing` with rotation; Dockerfile; SQLite session persistence (Drizzle + better-sqlite3 WAL)
- **P6** — Trust Bundle auto-distribution (`/.well-known/mpcp-trust-bundle.json`; zero merchant env-var config)
- **P7** — Spend webhooks: HMAC-signed push notifications at configurable thresholds; `payment.denied` events; dispatch log
- **P8** — Session policy controls: merchant allowlist/blocklist (glob); velocity limits (max payments/hour, max amount per merchant/day)
- **P9** — Soft budget ceiling + continuation token: budget exhaustion pauses instead of hard-failing; `PATCH /sessions/:id` raises ceiling via single-use HMAC token
- **P10** — x402 merchant mode: `POST /charge` / `GET /charge/:id/verify`; `/.well-known/x402-payment-info`

Deferred items (each a standalone PR): PostgreSQL adapter, Redis session cache, per-owner rate limiting, OpenTelemetry traces, Prometheus text-format metrics.

### mpcp-gateway-client

P1–P3 complete. P4 (receipts + audit) planned.

Implemented:

- **P1** — Core client: `GatewayClient`, `createSession`, `session.fetch()` wrapper, session CRUD; zero runtime deps; TypeScript + ESM
- **P2** — Soft-limit continuation: `onSoftLimit` callback; `continueSession()`; automatic retry on user approval
- **P3** — Framework adapters: `GatewayFetchTool` (LangChain), `gatewayFetchTool()` (Vercel AI SDK), `gatewayFetchFn()` (generic function-calling / AutoGen)

Planned:

- **P4** — Receipts + audit: `getReceipts()`, `verifyReceipt()` (Ed25519), `fetchGatewayKeys()`

---

## Spec roadmap

Protocol specification work is tracked via GitHub pull requests on [mpcp-spec](https://github.com/mpcp-protocol/mpcp-spec). Spec changes accompany each reference implementation PR that introduces new protocol fields or behaviors.

Upcoming spec work:

- `mpcp-gateway-client` P4 (receipts + audit) — spec alignment when implemented
- `mpcp-wallet-sdk` PR7 (React Native bundle) — spec alignment when implemented
- `mpcp-reference` Phase 6 pending PRs (PR21–PR25) — payment profiles, L1 evaluation, conformance badge
