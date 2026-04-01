# MPCP Authorization Chain

The **authorization chain** is the core visual model for MPCP. Each step produces a verifiable artifact that constrains the next. PolicyGrant and SignedBudgetAuthorization are cryptographically signed; the Trust Gateway verifies both signatures before submitting settlement. Machines spend within bounds established upstream—no per-transaction approval required.

```
PolicyGrant → SBA → Trust Gateway → XRPL Settlement → Receipt
```

In fleet deployments, an optional FleetPolicyAuthorization (FPA) layer may sit above PolicyGrant.

```
Fleet Policy
↓
PolicyGrant
↓
SignedBudgetAuthorization (SBA)
↓
Trust Gateway
↓
XRPL Settlement → Receipt
```

## What Each Step Does

| Step | Artifact | Purpose |
|------|-----------|---------|
| **Fleet Policy** | Policy definition | Rules: rails, assets, vendors, caps |
| **PolicyGrant** | Session entry | "This machine may initiate payment under these constraints" |
| **SignedBudgetAuthorization** | Spending envelope | "Up to X, on these rails, to these destinations" |
| **Trust Gateway** | Settlement executor | Verifies the authorization chain and submits the XRPL transaction |
| **Receipt** | txHash | Confirmed on-chain settlement result |

## Key Idea

Approval moves **upstream**. The human or policy administrator grants a **session** and **budget**. The machine spends within that budget. The Trust Gateway verifies the chain and executes settlement — no separate per-payment authorization artifact is required.

## See Also

- [System Model](system-model.md) — How the chain fits in the overall architecture
- [Artifact Lifecycle](artifact-lifecycle.md) — When each artifact is created
- [Reference Flow](fleet-ev-reference-flow.md) — Full EV charging walkthrough
- [Protocol: Artifacts](../protocol/artifacts.md) — Detailed artifact specs
