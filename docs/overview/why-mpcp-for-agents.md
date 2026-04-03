# Why MPCP for AI Agent Spending

When a human delegates spending authority to an AI agent, three things must be true:

1. **The human's intent is cryptographically bound** — the agent can't exceed the budget or
   spend on categories the human didn't approve
2. **Merchants can verify the authorization without calling the human** — offline-capable,
   stateless verification at the point of payment
3. **The human can cancel** — revocation that propagates to merchants

MPCP provides all three. The human signs a PolicyGrant with their [DID](https://www.w3.org/TR/did-core/) key; the agent signs per-payment SBAs; merchants verify the chain (PolicyGrant + SBA) locally; and the Trust Gateway enforces the budget ceiling and submits XRPL settlement — with an optional online revocation check.

---

## The delegation chain

MPCP's authorization chain maps directly onto human-to-agent spending delegation:

```
Fleet (machine) profile:
  Fleet Operator → PolicyGrant → Trust Gateway → Vehicle Wallet → SBA → XRPL Settlement

Human-to-agent profile:
  Human (DID)    → PolicyGrant → Trust Gateway → AI Agent        → SBA → XRPL Settlement
```

Both profiles use the **same MPCP artifacts and the same verifier**. The difference is in who
signs the PolicyGrant (a human with a DID key or PA server) and what the agent does with it
(books hotels, not charges EVs).

---

## What MPCP adds that agent protocols don't

### Pre-authorized spending envelopes

Most agent protocols (AP2, TAPC) require online mandate exchange at payment time: the user signs
a cart or intent, the agent presents it to the merchant, the merchant verifies it live.

MPCP works differently: the human signs *once* (the PolicyGrant), and the agent pre-loads a
signed budget (SBA). The merchant verifies the chain locally, with no round-trip to the human.

**Result:** the agent can complete payments even when the human is unavailable or offline. The
spending is still bounded — the agent cannot exceed `maxAmountMinor` or pay outside
`allowedPurposes`.

### Cryptographic spending bounds, not just policy text

The SBA is a *signed* artifact specifying the exact maximum spend for this payment. Merchants verify the signature independently. There is no "trust the agent" step. And the Trust Gateway enforces the cumulative budget ceiling on top — a compromised or prompt-injected agent cannot cause overspending.

```
SBA.maxAmountMinor = "25000"   (USD cents → $250.00 — this booking)
SBA.budgetScope    = "TRIP"    (delegation spans the full Paris trip)
SBA.expiresAt      = "2026-04-13T23:59:59Z"

PolicyGrant.budgetMinor = 80000  (PA-signed ceiling → $800.00 total, enforced by Trust Gateway)
```

The agent cannot forge a larger SBA — it doesn't hold the SBA signing key. And even if it
did, the Trust Gateway rejects any SBA that would push cumulative spend past `budgetMinor`.

### Human revocation mid-delegation

```
GET {revocationEndpoint}?grantId={grantId}
Response: { "revoked": boolean, "revokedAt": "ISO8601" }
```

Alice can cancel her AI trip planner's budget at any time. Merchants who check the
revocation endpoint before processing payment will refuse. The MPCP verifier stays stateless —
revocation is a separate online check the merchant makes using `checkRevocation()`.

### Merchant category filter with auditability

`allowedPurposes` documents the human's intent in the signed PolicyGrant:

```json
"allowedPurposes": ["travel:hotel", "travel:flight", "travel:transport"]
```

The agent enforces this filter — it refuses to sign an SBA for a restaurant booking because
`travel:dining` is not in the list. The merchant sees the `allowedPurposes` field in the
PolicyGrant during verification and can confirm the payment category was permitted.

---

## How MPCP complements MCP and ACP

MCP and ACP define **what the agent does** (tool calls, task exchange). MPCP bounds **how
much the agent can spend** while doing it.

A travel agent powered by MCP tools might:

```
MCP tool call:    search_hotels("Paris", dates)   → returns options
MCP tool call:    book_hotel("Mercure Paris")      → initiates booking
MPCP payment:     SBA signed for $250             → Trust Gateway enforces Alice's $800 ceiling
```

The protocols are additive. An agent runtime can use MCP for task execution and MPCP for
payment authorization simultaneously. MPCP does not replace MCP or ACP — it adds the
cryptographic spending layer on top.

---

## When to use MPCP for agent spending

| Situation | MPCP fit |
|-----------|---------|
| Agent books travel across multiple days | TRIP scope SBA covers the whole trip |
| Human needs to cancel mid-delegation | XRPL: `CredentialDelete` on active-grant credential; non-XRPL: `revocationEndpoint` → `checkRevocation()` |
| Agent should only pay for certain categories | `allowedPurposes` filter |
| Merchant needs offline-capable verification | PolicyGrant + SBA chain verifies locally via Trust Bundle |
| Agent spending must be auditable | On-chain `mpcp/grant-id` memo + PolicyGrant + SBA bundle |
| Human uses a DID key (not a service account) | `issuer` = DID, standard key resolution |

---

## See Also

- [Human-to-Agent Delegation Profile](../profiles/human-agent-profile.md) — full deployment guide
- [Comparison with Agent Protocols](comparison-with-agent-protocols.md) — x402, AP2, ACP, TAPC
- [PolicyGrant](../protocol/PolicyGrant.md) — `activeGrantCredentialIssuer`, `revocationEndpoint`, `allowedPurposes`
- [SignedBudgetAuthorization](../protocol/SignedBudgetAuthorization.md) — TRIP scope
- [Actors](../architecture/actors.md) — AI Agent actor
