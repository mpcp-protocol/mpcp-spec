# Verification

MPCP settlement verification ensures that an executed transaction matches the authorization chain.

## Verification Pipeline

The Trust Gateway verifier runs checks in order:

1. **Schema** — PolicyGrant and SBA parse and validate against expected structure
2. **Signatures** — PolicyGrant and SBA signatures are valid (resolve public keys via `issuer` + `issuerKeyId` using the [Key Resolution](./key-resolution.md) algorithm; in offline deployments, keys are resolved from a pre-loaded [Trust Bundle](./trust-bundles.md))
3. **Linkage** — `SBA.authorization.grantId` references a valid PolicyGrant; constraint subsets are respected
4. **Policy** — Budget limits, rail/asset/destination constraints, expiration

If any check fails, verification fails with a specific reason. On success, the gateway submits the XRPL transaction and returns the `txHash` receipt.

## What Is Verified

| Check | Description |
|-------|-------------|
| PolicyGrant schema | Parses and validates against expected structure |
| PolicyGrant signature | Signature valid; expiresAt not passed; constraints valid |
| SBA schema | Parses and validates against expected structure |
| SBA signature | Signature valid; expiresAt not passed; `authorization.grantId` references a valid PolicyGrant |
| SBA → budget | Current payment amount ≤ `maxAmountMinor`; rail, asset, destination in allowlists. Check is stateless — session authority manages cumulative budget tracking. |

## Usage

```typescript
import { verifySignedBudgetAuthorization } from "mpcp-service/sdk";

const result = await verifySignedBudgetAuthorization(sba, { policyGrant });

if (result.valid) {
  // Chain verified — gateway may submit XRPL transaction
} else {
  // result.reason describes the failure
}
```

## Dispute Verification

When a settlement is disputed, the receipt `txHash` can be looked up directly on the XRPL ledger and reconciled against the SBA fields (rail, asset, amount, destination).

See [Dispute Resolution](../guides/dispute-resolution.md) for the guide.

## See Also

- [Artifacts](artifacts.md)
- [Hashing](hashing.md)
- [Key Resolution](./key-resolution.md)
- [Trust Bundles](./trust-bundles.md) — offline key distribution
- [Reference: CLI](https://mpcp-protocol.github.io/mpcp-reference/reference/cli/) — `mpcp verify` command
