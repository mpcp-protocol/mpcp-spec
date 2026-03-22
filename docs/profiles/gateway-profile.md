# Transparent Gateway Profile

A deployment pattern for adopting MPCP without requiring SDK integration on either side of a payment.

---

## Motivation

Integrating MPCP natively requires effort on both sides of every payment:

- **Budget owner side**: run a Policy Authority server, publish policies, issue PolicyGrants, and integrate the wallet-sdk into the spending agent
- **Merchant side**: integrate the merchant-sdk, accept SBA artifacts, and verify the authorization chain

This friction is the right design for deployments that need **end-to-end cryptographic verification** — fleet vehicles, embedded devices, or AI agents operating across many independent merchants with no pre-existing trust relationship.

But many deployments don't need this from day one. A startup processing AI agent payments, a travel platform delegating spend to an LLM, or an enterprise deploying autonomous purchasing agents may want to:

- Enforce budget limits and purpose constraints on an AI agent
- Let humans cancel a delegation mid-flight
- Get an audit trail of what was spent and why

…without asking every merchant to adopt a new SDK, and without requiring the budget owner to run server infrastructure.

The **Transparent Gateway** pattern solves this. It sits between the budget owner and the merchant, implementing MPCP internally while exposing simple, familiar interfaces on both sides.

---

## Overview

```
Budget Owner
  │  authorizes gateway with spending constraints
  │  (no SDK, no PA server — just a configuration call)
  ▼
┌──────────────────────────────────────────────────┐
│             MPCP Transparent Gateway              │
│                                                   │
│   PA server (internal)  →  Wallet Session         │
│   PolicyGrant issuance      per-payment SBAs      │
│   revocation tracking       budget enforcement    │
│   audit log                 purpose filtering     │
└──────────────────────────┬───────────────────────┘
                           │  x402 / standard payment protocol
                           ▼
                        Merchant
                   (no MPCP knowledge required)
```

The gateway runs the full MPCP stack internally. Externally it presents:

- **Inward** (budget owner → gateway): a lightweight session configuration API
- **Outward** (gateway → merchant): a standard payment protocol such as [x402](https://x402.org)

---

## When to Use This Profile

Use the Transparent Gateway profile when:

- You want MPCP budget enforcement and audit without requiring merchant SDK integration
- You are in an early adoption phase and cannot mandate MPCP on both sides simultaneously
- The budget owner is a human or service that cannot run a PA server (consumer apps, SaaS products)
- You need a migration path toward native MPCP as merchant adoption grows
- Merchants already accept a standard payment protocol (x402, Stripe, etc.) and must not be disrupted

Do **not** use this profile when:

- Merchants must independently verify the full authorization chain without trusting an intermediary
- The deployment is adversarial (the gateway itself is untrusted by one or both parties)
- Cryptographic proof of policy compliance must flow unbroken from budget owner to merchant

For those requirements, use native MPCP with the [Full Profile](full-profile.md) or [Human-Agent Profile](human-agent-profile.md).

---

## Trust Model

The gateway shifts trust compared to native MPCP:

| Property | Native MPCP | Transparent Gateway |
|----------|-------------|---------------------|
| Budget ceiling enforced | ✓ cryptographic | ✓ inside gateway |
| Purpose filtering | ✓ cryptographic | ✓ inside gateway |
| Revocation by budget owner | ✓ | ✓ gateway checks endpoint |
| Cumulative spend tracking | ✓ | ✓ inside gateway |
| Merchant verifies chain independently | ✓ | ✗ merchant trusts gateway |
| Merchant needs MPCP SDK | required | not required |
| Budget owner needs PA server | required | not required |
| End-to-end cryptographic audit | ✓ | gateway receipt only |

The key trade-off: merchants trust the gateway for payment validity rather than the cryptographic artifact chain. This is the same trust model as traditional payment processors (Visa, Stripe) and is commercially accepted in nearly all existing commerce.

The budget owner retains meaningful control:

- Spending ceiling is enforced by the gateway before any payment is executed
- Purposes are filtered by the gateway before any x402 request is sent
- The budget owner can revoke at any time via the gateway's session API
- The gateway produces per-payment receipts the budget owner can audit

---

## Interfaces

### Budget Owner → Gateway (Session Configuration)

The budget owner creates a **gateway session** specifying the spending constraints. No PolicyGrant signing, no private key management.

```
POST /sessions
{
  "budget":    { "amount": "80000", "currency": "USD" },
  "purposes":  ["travel:hotel", "travel:flight", "travel:transport"],
  "expiresAt": "2026-04-13T00:00:00Z",
  "label":     "Alice Paris trip"
}

→ { "sessionToken": "gw_sess_abc123...", "sessionId": "...", "revocationUrl": "..." }
```

The `sessionToken` is passed to the AI agent or autonomous process. The gateway revokes the session on `DELETE /sessions/{id}` or when `expiresAt` is reached.

### Gateway → Merchant (x402)

The gateway speaks [x402](https://x402.org) on the outbound side. When the agent (via the gateway) makes an HTTP request to a merchant endpoint:

```
1. Agent makes request
2. Merchant returns:
      HTTP 402 Payment Required
      X-Payment: { "amount": "18000", "currency": "USD", "address": "..." }

3. Gateway checks internal MPCP session:
   - purpose allowed? ✓
   - $180 fits within remaining budget? ✓
   - grant not revoked? ✓

4. Gateway executes payment, retries with receipt:
      X-Payment-Receipt: "txid:..."

5. Merchant serves the resource. No MPCP artifact seen.
```

The gateway may also speak other outbound protocols (Stripe, direct bank transfer, stablecoin rails) depending on what the merchant accepts. x402 is preferred for machine-to-machine flows because its 402 response carries machine-readable payment terms that map directly onto MPCP's authorization model.

---

## Internal Architecture

The gateway implements these MPCP components internally, invisible to both sides:

### Policy Authority (internal)

When a budget owner creates a session, the gateway mints a PolicyGrant from the session parameters and stores it internally. No external PA server is required.

```
Session config  →  internal PolicyGrant
{                    {
  budget: $800         grantId: ...,
  purposes: [...]  →   policyHash: ...,
  expiresAt: ...       allowedPurposes: [...],
}                      expiresAt: ...,
                       revocationEndpoint: internal
                    }
```

### Wallet Session

For each active gateway session, the gateway runs a wallet Session that:

- Issues a per-payment SBA (`budgetScope: "SESSION"`, `maxAmountMinor` = this payment amount)
- Tracks cumulative spend against the session ceiling
- Checks the internal revocation state before signing each SBA
- Throws `MpcpBudgetExceededError` or `MpcpGrantRevokedError` when appropriate — refusing to proceed with the outbound payment

### Revocation

Budget owners revoke via the gateway's REST API. The gateway immediately marks the internal grant as revoked. The wallet Session checks this state before signing the next SBA. The next outbound payment attempt is refused before any x402 request is sent.

---

## Audit and Receipts

The gateway produces a signed per-payment receipt for every completed payment:

```json
{
  "receiptId": "rcpt_...",
  "sessionId": "...",
  "purpose":   "travel:hotel",
  "amount":    { "amountMinor": "18000", "currency": "USD" },
  "merchant":  "...",
  "paidAt":    "2026-04-10T15:00:00Z",
  "txRef":     "txid:...",
  "signature": "..."
}
```

The budget owner can retrieve the full receipt log at any time via `GET /sessions/{id}/receipts`. This provides after-the-fact accountability even without a full MPCP artifact chain.

For deployments requiring stronger guarantees, the gateway can optionally include the internal SBA in an `X-Mpcp-Sba` response header, allowing the budget owner to independently verify the artifact chain at audit time.

---

## Progressive Trust Path

The gateway profile is designed as a migration path toward native MPCP, not a permanent ceiling:

### Level 0 — Gateway trust only

Merchant sees x402 payment confirmation. No MPCP knowledge. Budget owner audits via gateway receipts.

### Level 1 — MPCP passthrough headers

The gateway includes the internal SBA in a custom HTTP header alongside the x402 payment:

```
X-Mpcp-Sba: base64encodedSBA...
```

MPCP-aware merchants can independently verify the authorization chain if they choose. Non-MPCP merchants ignore the header. No merchant-side changes required to proceed.

### Level 2 — Native MPCP

Merchant integrates the merchant-sdk. Full end-to-end verification. The gateway is removed from the trust chain. Budget owner runs their own PA server or continues to delegate to the gateway for grant issuance only.

This path lets deployments adopt MPCP gradually, proving value at each level before requiring integration from counterparties.

---

## Comparison with Other Profiles

| | Lite Profile | Full Profile | Human-Agent Profile | Gateway Profile |
|---|--------------|--------------|---------------------|-----------------|
| Merchant SDK required | ✓ | ✓ | ✓ | ✗ |
| PA server required | ✗ | ✓ | ✓ (or gateway) | ✗ (hosted by gateway) |
| Merchant verifies chain | ✓ | ✓ | ✓ | ✗ (trusts gateway) |
| Budget owner controls spend | ✓ | ✓ | ✓ | ✓ |
| Revocation | ✓ | ✓ | ✓ | ✓ (gateway-mediated) |
| Adoption friction | medium | high | medium | low |
| Cryptographic audit | ✓ | ✓ | ✓ | gateway receipts |
| Migration to native MPCP | — | — | — | ✓ progressive |

---

## Security Considerations

### Gateway as single point of trust

Because merchants trust the gateway for payment validity, a compromised or dishonest gateway could approve payments outside the budget owner's constraints. Mitigations:

- Budget owners should use short-lived sessions with explicit expiry
- The gateway should publish its enforcement logic and be independently auditable
- Signed receipts allow budget owners to detect gateway misbehavior after the fact
- Level 1 passthrough headers allow budget owners to cryptographically verify what the gateway signed

### Budget owner session token security

The `sessionToken` granted to an agent controls spending up to the session ceiling. It should be treated with the same care as a payment credential:

- Transmit over TLS only
- Scope to a single agent process; do not share across agents
- Revoke immediately if the token may be compromised

### Revocation latency

Revocation takes effect before the next payment attempt (the wallet Session checks before signing each SBA). There is no window where a previously-authorized in-flight payment is retroactively cancelled. Payments already completed before revocation are unaffected.

---

## See Also

- [Human-Agent Profile](human-agent-profile.md) — native MPCP for AI agent delegation
- [Lite Profile](lite-profile.md) — lightweight SBA-only native integration
- [Integration Guide](../guides/integration-guide.md) — implementation paths for all profiles
- [Trust Bundles](../protocol/trust-bundles.md) — offline key resolution for embedded device deployments
- [x402](https://x402.org) — HTTP-native machine payment protocol used on the outbound side
