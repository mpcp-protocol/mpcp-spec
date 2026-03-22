# Human-to-Agent Delegation Profile

Deployment profile for MPCP-controlled AI agent spending under human authorization.

---

## Overview

The Human-to-Agent Delegation Profile maps MPCP's authorization chain onto a human principal
delegating bounded spending authority to an AI agent:

```
Fleet (machine) profile:
  Fleet Operator (DID) → PolicyGrant → Vehicle Wallet → SBA → SPA → Settlement

Human-to-agent profile:
  Human (DID)          → PolicyGrant → AI Agent        → SBA → SPA → Settlement
```

A **human signs a PolicyGrant** with their DID key, delegating a bounded travel or task budget
to an AI agent. The agent acts as both **session authority** (creates and signs SBAs) and
**payment decision service** (signs SPAs). Merchants verify the full chain without calling back
to the human.

---

## When to Use This Profile

This profile is appropriate when:

- A human wants to delegate bounded spending to an AI agent (travel, subscriptions, event budgets)
- Payments span multiple sessions or days (use `budgetScope: "TRIP"`)
- The human may need to cancel mid-delegation (use `revocationEndpoint`)
- Merchant categories should be explicitly constrained (use `allowedPurposes`)
- Offline-capable verification is required at the merchant side

---

## PolicyGrant Structure

The PolicyGrant is signed by the human principal's DID key.

```json
{
  "version": "1.0",
  "grantId": "grant_paris_2026",
  "policyHash": "a1b2c3d4e5f6...",
  "subjectId": "ai-trip-planner-v2",
  "scope": "TRIP",
  "allowedRails": ["xrpl"],
  "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." }],
  "expiresAt": "2026-04-13T23:59:59Z",
  "allowedPurposes": ["travel:hotel", "travel:flight", "travel:transport"],
  "revocationEndpoint": "https://wallet.alice.example.com/revoke",
  "issuer": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
  "issuerKeyId": "alice-did-key-1",
  "signature": "..."
}
```

### Key fields for this profile

| Field | Description |
|-------|-------------|
| `issuer` | Human's DID (did:key, did:web, etc.) — identifies the policy authority |
| `issuerKeyId` | Key ID within the DID document used for signing |
| `allowedPurposes` | Merchant category allowlist — enforced by the AI agent, not the verifier |
| `revocationEndpoint` | URL where the human's wallet accepts cancellation queries |
| `scope` | Use `TRIP` for multi-day or multi-session delegations |

### Policy Authority Server — Common Deployment Pattern

The example above shows Alice signing the PolicyGrant with her DID key directly. In practice, most deployments use a **Policy Authority (PA) server** — a backend service that issues grants on Alice's behalf.

In this model:

- Alice authenticates to her PA server (via session token, API key, or OAuth)
- The PA server issues the PolicyGrant, signing with a domain key
- `issuer` is the PA server's domain (e.g. `wallet.alice.example.com`) rather than Alice's personal DID
- Key resolution uses HTTPS well-known: `https://wallet.alice.example.com/.well-known/mpcp-keys.json`
- The `revocationEndpoint` is also hosted by the PA server, which tracks revocation state

```json
{
  "issuer": "wallet.alice.example.com",
  "issuerKeyId": "pa-grant-key-1",
  "revocationEndpoint": "https://wallet.alice.example.com/revoke"
}
```

The MPCP artifact chain is identical — only the `issuer` value and key resolution method differ. This pattern is operationally simpler than requiring users to manage DID private keys and is the recommended starting point for most production deployments.

---

## TRIP Scope Semantics

`budgetScope: "TRIP"` indicates that the SBA budget applies across multiple sessions for a
single trip or project.

```json
{
  "budgetScope": "TRIP",
  "maxAmountMinor": "80000",
  "sessionId": "paris-trip-2026-alice",
  "actorId": "ai-trip-planner-v2"
}
```

The **agent (session authority)** MUST maintain a cumulative spend counter across all sessions
in the trip. Each SPA reduces the remaining budget. The merchant verifier checks the current
SPA against the SBA's `maxAmountMinor` using the cumulative counter provided in the verification
context.

**Comparison with SESSION scope:**

| | SESSION | TRIP |
|---|---------|------|
| Scope | Single session | Multi-day / multi-session |
| Budget resets | Each session | Never (until expiry or revocation) |
| Designed for | Parking, charging | Travel, subscriptions, project budgets |
| Spend tracking | Session authority | Agent across all sessions |

---

## DID Key Resolution

When `issuer` is a [DID](https://www.w3.org/TR/did-core/):

- `did:key:z6Mk...` — public key is embedded in the DID identifier itself (no network call)
- `did:web:example.com` — resolve via `https://example.com/.well-known/did.json`
- `did:xrpl:mainnet:rAddr...` — resolve via XRPL `account_objects` JSON-RPC
- `did:hedera:mainnet:0.0.xxxxx` — resolve via Hedera Mirror Node

Any W3C-compatible DID method may be used. Verifiers resolve the public key (as JWK) using
`issuer` and `issuerKeyId` before verifying the PolicyGrant signature.
See [Key Resolution](../protocol/key-resolution.md).

---

## `allowedPurposes` — Merchant Category Filter

`allowedPurposes` is an **agent-enforced** constraint, not a cryptographic enforcement by the
MPCP verifier. It documents the human's intent and appears in the audit trail.

**Agent responsibility:** Before signing an SPA, the agent MUST check whether the merchant
category (purpose) is in the `allowedPurposes` list. If not, the agent refuses to sign — no SBA
check, no payment.

**Verifier behavior:** The MPCP verifier does NOT enforce `allowedPurposes`. Merchants relying
on purpose enforcement MUST trust the agent's compliance or implement independent category
verification.

**Example enforcement in agent:**

```javascript
const purposeAllowed = grant.allowedPurposes?.includes(merchantCategory) ?? true;
if (!purposeAllowed) {
  // refuse to sign SPA
}
```

---

## Revocation

### Endpoint contract

```
GET {revocationEndpoint}?grantId={grantId}
Response: { "revoked": boolean, "revokedAt": "ISO8601" }
```

### Merchant responsibility

Merchants and service providers with the `revocationEndpoint` field SHOULD call this endpoint
before accepting a payment. The check is a **separate online step** — the MPCP verifier pipeline
remains stateless and synchronous.

```javascript
import { checkRevocation } from "mpcp-service/sdk";

const { revoked, revokedAt } = await checkRevocation(
  grant.revocationEndpoint,
  grant.grantId,
  { timeoutMs: 3000 }
);
if (revoked) {
  // reject payment
}
```

### Offline exception

If the merchant cannot reach the revocation endpoint (network unavailable, timeout), the
merchant makes a risk-based decision. The MPCP spec recommends:

- **Online merchants** (hotels, airlines): block on revocation endpoint failure
- **Offline merchants** (transit, access control): accept and rely on SBA expiry as upper bound

### Revocation window

Revocation is not instantaneous. Between revocation and the next merchant check, the agent may
complete additional payments. Operators MUST set appropriate SBA expiry times to bound this window.
Short expiry (e.g. 1–4 hours) reduces the revocation window at the cost of requiring more
frequent SBA refresh.

---

## Security Considerations

### Key compromise

If the human's DID key is compromised:
1. Revoke all active PolicyGrants via `revocationEndpoint`
2. Rotate the DID key or create a new DID
3. Reissue PolicyGrants under the new key

### Agent key compromise

If the agent's SBA/SPA signing key is compromised, the attacker is bounded by:
- The `maxAmountMinor` in the SBA
- The `expiresAt` in the SBA
- The `allowedPurposes` and `destinationAllowlist`

Revoke the PolicyGrant immediately to stop new SBAs from being issued.

---

## Comparison with Fleet Profile

| | Fleet Profile | Human-to-Agent Profile |
|---|--------------|----------------------|
| Policy authority | Fleet operator (domain key) | Human (DID key) or PA server (domain key) |
| Subject | Vehicle wallet | AI agent |
| Connectivity | Offline-first (Trust Bundle) | Online by design |
| Revocation | `revocationEndpoint` — fleet disables vehicle mid-shift | `revocationEndpoint` — human cancels delegation |
| Budget scope | SESSION (per-shift, multi-merchant) | TRIP (multi-day, multi-session) |
| Merchant categories | destinationAllowlist (crypto) | allowedPurposes (semantic, agent-enforced) |
| Use case | Tolls, EV charging, parking | Travel, subscriptions, event budgets |

Both profiles use the same MPCP artifact chain and the same verifier. The difference is in
the policy authority, connectivity assumptions, and the new fields for human use cases.

---

## See Also

- [PolicyGrant](../protocol/PolicyGrant.md) — `revocationEndpoint`, `allowedPurposes` fields
- [SignedBudgetAuthorization](../protocol/SignedBudgetAuthorization.md) — TRIP scope
- [Actors](../architecture/actors.md) — AI Agent actor
- [Comparison with Agent Protocols](../overview/comparison-with-agent-protocols.md)
- [Full Profile](full-profile.md) — Fleet / vehicle profile for comparison
