# Artifact Lifecycle

MPCP artifacts flow through a defined lifecycle from policy evaluation to settlement verification.

## Pipeline

```
Fleet Policy
↓
PolicyGrant
↓
SignedBudgetAuthorization
↓
SignedPaymentAuthorization
↓
SettlementIntent
↓
Settlement
```

Each artifact constrains the next. Downstream artifacts must be subsets of upstream constraints.

## Artifact Roles

| Artifact | Issued By | Purpose |
|----------|-----------|---------|
| **PolicyGrant** | Fleet/service policy | Initial permission envelope; rails, assets, caps |
| **SBA** | Vehicle wallet | Session-level spending envelope |
| **SPA** | Vehicle wallet | Binds specific payment to quote and policy |
| **SettlementIntent** | Vehicle wallet | Canonical settlement description (optional hash in SPA) |
| **Settlement Result** | Settlement rail | Confirms execution |

## Typical Lifecycle

1. **Pre-session** — PolicyGrant issued and stored (fleet backend, vehicle wallet)
2. **Session entry** — Vehicle loads PolicyGrant, may issue SBA
3. **Payment request** — Service requests payment; vehicle validates policy and budget
4. **Authorization** — Vehicle creates SettlementIntent, signs SPA
5. **Verification** — Service verifies MPCP chain
6. **Settlement** — Payment executes on rail
7. **Reconciliation** — Settlement verified against authorization

## Storage

Artifacts may be stored in:

- **Fleet backend** — Authoritative PolicyGrant; audit logs
- **Vehicle wallet** — Operational PolicyGrant, SBA, SPA, receipts
- **Service provider** — Received authorizations, verification results, receipts
- **Settlement rail** — Transaction record (authoritative)

## See Also

- [Reference Flow](fleet-ev-reference-flow.md) — End-to-end EV charging scenario with timeline
- [Protocol specs](../protocol/mpcp.md) — Full artifact specifications
