# MPCP Ecosystem Roadmap

MPCP development is tracked per-repository. Each repository has its own `ROADMAP.md` covering its specific implementation phases.

---

## Repositories

| Repository | Role | Roadmap |
|------------|------|---------|
| [mpcp-reference](https://github.com/mpcp-protocol/mpcp-reference) | Protocol core — canonical SDK, verifier, schemas, anchoring adapters, golden vectors | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-reference/blob/main/ROADMAP.md) |
| [mpcp-policy-authority](https://github.com/mpcp-protocol/mpcp-policy-authority) | Deployable policy authority service — grant issuance, revocation, on-chain anchoring | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-policy-authority/blob/main/ROADMAP.md) |
| [mpcp-wallet-sdk](https://github.com/mpcp-protocol/mpcp-wallet-sdk) | Wallet SDK — session management, SBA signing, budget enforcement (Node.js + browser) | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-wallet-sdk/blob/main/ROADMAP.md) |
| [mpcp-merchant-sdk](https://github.com/mpcp-protocol/mpcp-merchant-sdk) | Merchant SDK — SBA verification, revocation caching, spend tracking, framework adapters | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-merchant-sdk/blob/main/ROADMAP.md) |
| [mpcp-gateway](https://github.com/mpcp-protocol/mpcp-gateway) | Transparent payment gateway — speaks x402 externally, enforces MPCP internally; bridges non-MPCP agents to MPCP merchants | [ROADMAP.md](https://github.com/mpcp-protocol/mpcp-gateway/blob/main/ROADMAP.md) |
| mpcp-gateway-client *(planned)* | Agent-side fetch wrapper — drop-in that routes requests through the gateway and handles 402 interception transparently; LangChain / AutoGen adapters | — |
| [mpcp-spec](https://github.com/mpcp-protocol/mpcp-spec) | Protocol specification, architecture docs, guides | this site |

---

## Implementation status

### mpcp-reference

Phases 1–5 complete. Phase 6 (adoption acceleration) is active.

Implemented highlights: canonical serialization · artifact schemas · full verification engine · CLI verifier with explain mode · Hedera HCS and XRPL anchor adapters · `did:xrpl` resolver · XRPL NFT revocation · AES-256-GCM encrypted policy anchoring · golden protocol vectors · human-to-agent delegation profile.

### mpcp-policy-authority

Phase 1 complete (grant issuance, policy custody, revocation endpoint, XRPL NFT mint/burn, persistent custody with soft-delete).

Phase 2 active: HCS and XRPL on-chain anchoring integration into the service layer.

### mpcp-wallet-sdk

Planned. Phase 1 (Node.js core: `parseGrant`, `Session`, budget tracking) is the starting point.

### mpcp-merchant-sdk

Planned. Phase 1 (core `verifyMpcp`, revocation cache, spend tracking) is the starting point.

### mpcp-gateway

Phases 1–5 complete. The gateway bridges non-MPCP agents to MPCP merchants: it intercepts HTTP 402 responses, executes x402 payments, and optionally attaches a signed SBA (`X-Mpcp-Sba`) so MPCP-aware merchants can verify the authorization chain without any gateway-specific integration.

Phase 5 deferred items (each a standalone PR): SQLite/PostgreSQL session persistence, Redis spend-ceiling cache, per-owner rate limiting, OpenTelemetry traces, Prometheus text-format metrics.

Phases 6–10 planned (adoption acceleration):

- **P6** — Trust Bundle well-known endpoint: merchants fetch `/.well-known/mpcp-trust-bundle.json` at startup and verify gateway SBAs with zero env config
- **P7** — Spend webhooks: budget owners receive signed push notifications at configurable spend thresholds (50%/80%/100%) and on payment denial
- **P8** — Session policy controls: merchant allowlist/blocklist (glob patterns) and velocity limits (max payments per hour, max amount per merchant per day)
- **P9** — Soft budget ceiling + continuation token: budget exhaustion pauses the agent instead of hard-failing; user approves an extension via `PATCH /sessions/{id}` without re-issuing a grant
- **P10** — x402 merchant mode: any backend delegates payment collection to the gateway via `POST /charge`; no x402 implementation required on the merchant side

---

## Spec roadmap

Protocol specification work is tracked via GitHub pull requests on [mpcp-spec](https://github.com/mpcp-protocol/mpcp-spec). Spec changes accompany each reference implementation PR that introduces new protocol fields or behaviors.

Upcoming spec work tracks the active reference implementation PRs:

- Payment profiles expansion (PR21) — XRPL Stablecoin / RLUSD profile doc
- Layer-1 evaluation (PR22) — comparative analysis doc
- Machine wallet guardrails (PR23) — guardrail model guide
- Automated fleet payment demo (PR24) — visual walkthrough doc
- MPCP conformance badge (PR25) — conformance criteria
