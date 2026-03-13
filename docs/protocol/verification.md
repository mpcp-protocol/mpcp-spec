# Verification

MPCP settlement verification ensures that an executed transaction matches the authorization chain.

## Verification Pipeline

The verifier runs checks in order:

1. **Schema** — All artifacts parse and validate against expected structure
2. **Signatures** — PolicyGrant, SBA, and SPA signatures are valid (resolve public keys via `issuer` + `issuerKeyId` or deployment config)
3. **Linkage** — `SBA.authorization.grantId` references a valid PolicyGrant; `SPA.authorization.budgetId` references the issuing SBA; constraint subsets are respected
4. **Hash** — If intentHash is present, it matches `computeSettlementIntentHash(settlementIntent)`
5. **Policy** — Budget limits, rail/asset/destination constraints, expiration

If any check fails, verification fails with a specific reason.

## What Is Verified

| Check | Description |
|-------|-------------|
| PolicyGrant | Signature valid; expiresAt not passed; constraints valid |
| SBA | Signature valid; expiresAt not passed; `authorization.grantId` references a valid PolicyGrant |
| SBA → decision | Current payment amount ≤ `maxAmountMinor`; rail, asset, destination in allowlists. Check is stateless — session authority manages cumulative budget tracking. |
| SPA | Signature valid; expiresAt not passed |
| SPA → settlement | rail, amount, destination, asset match executed settlement |
| intentHash | If present, equals hash of settlement intent |

## Usage

```typescript
import { verifySettlement } from "mpcp-service";

const result = verifySettlement(context);

if (result.valid) {
  // Settlement matches authorization chain
} else {
  // result.reason describes the failure
}
```

The `context` includes policyGrant, signedBudgetAuthorization, signedPaymentAuthorization, settlement, paymentPolicyDecision, decisionId, and optional settlementIntent.

## Dispute Verification

When a settlement is disputed, `verifyDisputedSettlement` runs full chain verification plus optional ledger anchor verification. If the intent was anchored (e.g., to Hedera HCS), the anchor can be checked against the expected intentHash.

See [Dispute Resolution](../guides/dispute-resolution.md) for the guide.

## See Also

- [Artifacts](artifacts.md)
- [Hashing](hashing.md)
- [Anchoring](anchoring.md)
- [Reference: CLI](https://mpcp-protocol.github.io/mpcp-reference/reference/cli/) — `mpcp verify` command
