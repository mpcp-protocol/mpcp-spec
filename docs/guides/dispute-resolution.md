# Dispute Resolution

When a settlement is disputed, MPCP supports verification of the full authorization chain plus optional ledger anchor.

## Verification Flow

1. **MPCP chain** — Verify PolicyGrant → SBA → SPA → SettlementIntent
2. **Ledger anchor** (optional) — If intent was anchored, verify the anchor matches the intent hash

## Usage

### Sync (Mock Anchor or Hedera with intentHash)

```javascript
import { verifyDispute } from "mpcp-service/service";

const result = verifyDispute({
  context: settlementVerificationContext,
  ledgerAnchor: anchorResult,  // optional
});

if (result.verified) {
  // Settlement and anchor (if provided) are valid
} else {
  // result.reason describes the failure
}
```

### Async (Hedera HCS Mirror)

For Hedera HCS anchors, use the async verifier to fetch from the mirror node:

```javascript
import { verifyDisputeAsync } from "mpcp-service/service";

const result = await verifyDisputeAsync({
  context: settlementVerificationContext,
  ledgerAnchor: anchorResult,
});
```

## Anchoring for Disputes

Publishing the intent hash to a ledger (e.g., Hedera HCS) provides:

- **Non-repudiation** — Intent was committed before settlement
- **Ordering** — Consensus timestamp establishes when intent was published
- **Auditability** — Third parties can verify without seeing payment details

```javascript
import { anchorIntent, computeSettlementIntentHash } from "mpcp-service/service";

const intentHash = computeSettlementIntentHash(settlementIntent);
const anchor = await anchorIntent(intentHash, { rail: "hedera-hcs" });

// Store anchor with settlement for dispute resolution
```

## Failure Reasons

| Reason | Meaning |
|--------|---------|
| settlement_verification_failed | MPCP chain verification failed |
| anchor_provided_but_settlement_intent_missing | Anchor given but no settlement intent in context |
| intent_hash_mismatch | Anchor intentHash does not match computed hash |
| anchor_mismatch: ... | Mock anchor txHash does not match |
| hedera_hcs_requires_async_verification | Use verifyDisputeAsync for Hedera |

## See Also

- [Protocol: Anchoring](../protocol/anchoring.md)
- [Intent Anchoring](https://github.com/mpcp-protocol/mpcp-reference/blob/main/doc/architecture/INTENT_ANCHORING.md)
- [Dispute Verification](https://github.com/mpcp-protocol/mpcp-reference/blob/main/doc/architecture/DISPUTE_VERIFICATION.md)
- [Reference: Service API](https://mpcp-protocol.github.io/mpcp-reference/reference/service-api/)
