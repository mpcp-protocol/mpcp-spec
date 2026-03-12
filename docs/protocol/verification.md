# Verification

MPCP settlement verification ensures that an executed transaction matches the authorization chain.

## Verification Pipeline

The verifier runs checks in order:

1. **Schema** — All artifacts parse and validate against expected structure
2. **Linkage** — PolicyGrant → SBA → SPA chain is consistent (sessionId, policyHash, constraints)
3. **Hash** — If intentHash is present, it matches `computeSettlementIntentHash(settlementIntent)`
4. **Policy** — Budget limits, rail/asset/destination constraints, expiration

If any check fails, verification fails with a specific reason.

## What Is Verified

| Check | Description |
|-------|-------------|
| PolicyGrant | ExpiresAt not passed; constraints valid |
| SBA | Signature valid; expiresAt not passed; sessionId, policyHash match |
| SBA → decision | Budget not exceeded; rail, asset, destination in allowlists |
| SPA | Signature valid; expiresAt not passed |
| SPA → settlement | decisionId, rail, amount, destination, asset match executed settlement |
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
