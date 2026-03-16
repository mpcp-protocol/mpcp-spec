# Why MPCP for AI Agent Spending

When a human delegates spending authority to an AI agent, three things must be true:

1. **The human's intent is cryptographically bound** — the agent can't exceed the budget or
   spend on categories the human didn't approve
2. **Merchants can verify the authorization without calling the human** — offline-capable,
   stateless verification at the point of payment
3. **The human can cancel** — revocation that propagates to merchants

MPCP provides all three. The human signs a PolicyGrant with their [DID](https://www.w3.org/TR/did-core/) key; the agent pre-loads
a signed budget authorization; merchants verify the full chain (PolicyGrant → SBA → SPA →
Settlement) locally, with an optional online revocation check.

---

## The delegation chain

MPCP's authorization chain maps directly onto human-to-agent spending delegation:

```
Fleet (machine) profile:
  Fleet Operator (DID) → PolicyGrant → Vehicle Wallet → SBA → SPA → Settlement

Human-to-agent profile:
  Human (DID)          → PolicyGrant → AI Agent        → SBA → SPA → Settlement
```

Both profiles use the **same MPCP artifacts and the same verifier**. The difference is in who
signs the PolicyGrant (a human with a DID key) and what the agent does with it (books hotels,
not charges EVs).

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

The SBA is a *signed* artifact specifying the exact maximum spend in atomic units. Merchants
verify the signature and the budget math independently. There is no "trust the agent" step.

```
SBA.maxAmountMinor = "80000"   (USD cents → $800.00)
SBA.budgetScope    = "TRIP"    (covers the full Paris trip)
SBA.expiresAt      = "2026-04-13T23:59:59Z"
```

The agent cannot forge a larger SBA — it doesn't hold the SBA signing key (that belongs to
the session authority, which the human or a human-controlled service provisions).

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

The agent enforces this filter — it refuses to sign an SPA for a restaurant booking because
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
MPCP payment:     SPA signed for $250             → bounded by Alice's $800 PolicyGrant
```

The protocols are additive. An agent runtime can use MCP for task execution and MPCP for
payment authorization simultaneously. MPCP does not replace MCP or ACP — it adds the
cryptographic spending layer on top.

---

## When to use MPCP for agent spending

| Situation | MPCP fit |
|-----------|---------|
| Agent books travel across multiple days | TRIP scope SBA covers the whole trip |
| Human needs to cancel mid-delegation | `revocationEndpoint` → `checkRevocation()` |
| Agent should only pay for certain categories | `allowedPurposes` filter |
| Merchant needs offline-capable verification | PolicyGrant + SBA chain verifies locally |
| Agent spending must be auditable | Full artifact bundle per payment, signed chain |
| Human uses a DID key (not a service account) | `issuer` = DID, standard key resolution |

---

## See Also

- [Human-to-Agent Delegation Profile](../profiles/human-agent-profile.md) — full deployment guide
- [Comparison with Agent Protocols](comparison-with-agent-protocols.md) — x402, AP2, ACP, TAPC
- [PolicyGrant](../protocol/PolicyGrant.md) — `revocationEndpoint`, `allowedPurposes` fields
- [SignedBudgetAuthorization](../protocol/SignedBudgetAuthorization.md) — TRIP scope
- [Actors](../architecture/actors.md) — AI Agent actor
