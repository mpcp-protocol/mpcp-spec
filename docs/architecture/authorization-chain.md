# MPCP Authorization Chain

The **authorization chain** is the core visual model for MPCP. Each step produces a verifiable artifact that constrains the next. PolicyGrant, SignedBudgetAuthorization, and SignedPaymentAuthorization are cryptographically signed; verifiers validate all three signatures before accepting settlement. Machines spend within bounds established upstream—no per-transaction approval required.

```
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

In fleet deployments, an optional FleetPolicyAuthorization (FPA) layer may sit above PolicyGrant.

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

## What Each Step Does

| Step | Artifact | Purpose |
|------|-----------|---------|
| **Fleet Policy** | Policy definition | Rules: rails, assets, vendors, caps |
| **PolicyGrant** | Session entry | "This machine may initiate payment under these constraints" |
| **SignedBudgetAuthorization** | Spending envelope | "Up to X, on these rails, to these destinations" |
| **SignedPaymentAuthorization** | Payment binding | "This exact payment was authorized" |
| **SettlementIntent** | Canonical description | Deterministic settlement parameters (optional hash binding) |
| **Settlement** | Executed transaction | Rail executes payment; verifier checks chain |

## Key Idea

Approval moves **upstream**. The human or policy administrator grants a **session** and **budget**. The machine spends within that budget using pre-authorized intents. Settlement becomes a background operation.

## See Also

- [System Model](system-model.md) — How the chain fits in the overall architecture
- [Artifact Lifecycle](artifact-lifecycle.md) — When each artifact is created
- [Reference Flow](reference-flow.md) — Full EV charging walkthrough
- [Protocol: Artifacts](../protocol/artifacts.md) — Detailed artifact specs
