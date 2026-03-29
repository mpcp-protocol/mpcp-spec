# Intent Anchoring

Optional support for publishing **settlement intent hashes** to a distributed ledger for public
auditability and dispute protection.

!!! note "Scope: Settlement Intent Only"
    This page covers **intent anchoring** — recording the hash of a settlement intent before
    payment. For anchoring the **policy document** itself (on-chain policy audit trails and
    XRPL NFT-backed revocation), see [Policy Anchoring](./policy-anchoring.md).

## Purpose

When an intent hash is anchored:

- **Dispute resolution** — A verifier can fetch the anchor and confirm the intent was published before settlement
- **Auditability** — Third parties can verify intent was committed without seeing payment details
- **Replay protection** — Anchoring timestamps the intent; disputes can establish ordering

## Supported Rails

| Rail | Description |
|------|-------------|
| mock | Stub for development/testing; no real ledger |
| hedera-hcs | Hedera Hashgraph Consensus Service; publishes to a topic |

Additional rails can be supported by implementations (XRPL memos, Ethereum calldata, etc.).

## Flow

1. Compute `intentHash = computeSettlementIntentHash(settlementIntent)`
2. Publish the intentHash to the chosen rail (e.g., Hedera HCS topic)
3. Store the `AnchorResult` (reference, consensusTimestamp, etc.) with the settlement
4. In dispute: verifier fetches anchor, confirms intentHash matches

## Usage

```typescript
import { anchorIntent, computeSettlementIntentHash } from "mpcp-service";

const intentHash = computeSettlementIntentHash(settlementIntent);

// Mock (development)
const anchor = await anchorIntent(intentHash, { rail: "mock" });

// Hedera HCS (requires HEDERA_OPERATOR_ACCOUNT_ID, etc.)
const anchor = await anchorIntent(intentHash, { rail: "hedera-hcs" });
```

## Hedera HCS

Requires environment variables:

- `HEDERA_OPERATOR_ACCOUNT_ID`
- `HEDERA_OPERATOR_PRIVATE_KEY`
- `HEDERA_TOPIC_ID`
- `HEDERA_NETWORK` (optional; default: testnet)

Verification uses the Hedera mirror node to fetch the message and confirm intentHash matches.

## See Also

- [Dispute Resolution](../guides/dispute-resolution.md)
- [Reference: Service API](https://mpcp-protocol.github.io/mpcp-reference/reference/service-api/) — `anchorIntent`
