# Artifact Lifecycle

MPCP artifacts flow through a defined lifecycle from policy evaluation to settlement verification.

## Pipeline

```
Fleet Policy
↓
PolicyGrant
↓
SignedBudgetAuthorization (SBA)
↓
Trust Gateway
↓
XRPL Settlement → Receipt (txHash)
```

Each artifact constrains the next. Downstream artifacts must be subsets of upstream constraints.

## Artifact Roles

| Artifact | Issued By | Purpose |
|----------|-----------|---------|
| **PolicyGrant** | Fleet/service policy | Initial permission envelope; rails, assets, caps |
| **SBA** | Vehicle wallet | Session-level spending envelope |
| **Trust Gateway** | Gateway operator | Verifies PolicyGrant + SBA, submits XRPL transaction |
| **Receipt** | XRPL / gateway | `txHash` confirming on-chain settlement |

## Typical Lifecycle

1. **Pre-session** — PolicyGrant issued and stored (fleet backend, vehicle wallet)
2. **Session entry** — Vehicle loads PolicyGrant, issues SBA
3. **Payment request** — Service requests payment; vehicle presents SBA
4. **Verification** — Trust Gateway verifies PolicyGrant and SBA chain
5. **Settlement** — Gateway submits XRPL transaction
6. **Receipt** — Gateway returns `txHash`; operator reconciles against SBA

## Storage

Artifacts may be stored in:

- **Fleet backend** — Authoritative PolicyGrant; audit logs
- **Vehicle wallet** — Operational PolicyGrant, SBA, SPA, receipts
- **Service provider** — Received authorizations, verification results, receipts
- **Settlement rail** — Transaction record (authoritative)

## See Also

- [Reference Flow](fleet-ev-reference-flow.md) — End-to-end EV charging scenario with timeline
- [Protocol specs](../protocol/mpcp.md) — Full artifact specifications
