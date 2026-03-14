# Policy Anchoring

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

---

## Overview

MPCP supports **on-chain policy anchoring** — recording a commitment to a PolicyGrant's source
policy document on a distributed ledger to create a tamper-evident, third-party-auditable trail.

This is distinct from [Intent Anchoring](./anchoring.md), which records settlement intent hashes
for dispute resolution. Policy anchoring records the **policy authorization itself**, enabling
audit of what constraints were in force when a grant was issued.

Two anchoring patterns are defined:

| Pattern | When to use |
|---------|-------------|
| **HCS Policy Anchoring** | Institutional deployments requiring audit trails; any third party can verify the policy hash |
| **XRPL NFT-Backed PolicyGrant** | Consumer deployments without a hosted revocation service; burn the NFT to revoke |

---

## Privacy Model

Policy documents may contain sensitive fields: `subjectId` (identity), `allowedPurposes`
(behavioural/health/travel categories), spending limits, and `revocationEndpoint` (service
provider). Publishing these fields to a public, immutable ledger creates a GDPR right-to-erasure
conflict.

MPCP defines three `submitMode` values:

| `submitMode` | What goes on-chain | Privacy | Rails |
|---|---|---|---|
| `"hash-only"` | `policyHash` only | GDPR-safe; document never on-chain | HCS, XRPL |
| `"full-document"` | Full document in message body | Caller asserts doc is PII-free | HCS only |
| `"encrypted"` | AES-256-GCM ciphertext | Key shared out-of-band with auditors | HCS, XRPL |

**`"hash-only"` is the default.** The on-chain `policyHash` is sufficient for audit — any auditor
who receives the full document from the Service (which acts as custodian) can verify it against
the hash.

### XRPL note on "permissioned topics"

XRPL has no native encrypted storage or message primitive. HCS submit keys control *write*
access to a topic but messages remain publicly readable via any mirror node. True read
confidentiality on both rails requires encryption. `"permissioned HCS topic"` means controlling
who can write, not who can read.

---

## `anchorRef` Field

An optional string on `PolicyGrant` pointing to the on-chain record.

### Formats

| Format | Example |
|--------|---------|
| `hcs:{topicId}:{sequenceNumber}` | `"hcs:0.0.12345:42"` |
| `xrpl:nft:{tokenId}` | `"xrpl:nft:000800006B55D0F1584E4D2CBD04F60B9E61FFDD2A4E3F9F00000001"` |

The verifier passes `anchorRef` through without enforcement. It is informational metadata used
by auditors, merchants, and dispute resolution tooling.

---

## HCS Policy Anchoring

### Flow

1. The policy authority creates a PolicyGrant with a `policyHash`
2. The authority submits a message to a Hedera HCS topic (using `hederaHcsAnchorPolicyDocument`)
3. The returned `sequenceNumber` is encoded as `"hcs:{topicId}:{seq}"` and placed in `anchorRef`
4. Auditors query the HCS mirror node to retrieve the message and verify the `policyHash`

### HCS Message Formats

**Hash-only (default):**
```json
{
  "type": "MPCP:PolicyAnchor:1.0",
  "policyHash": "<sha256>",
  "submitMode": "hash-only",
  "anchoredAt": "2026-03-14T10:00:00.000Z"
}
```

**Encrypted:**
```json
{
  "type": "MPCP:PolicyAnchor:1.0",
  "policyHash": "<sha256>",
  "submitMode": "encrypted",
  "encryptedDocument": {
    "algorithm": "AES-256-GCM",
    "iv": "<base64 12 bytes>",
    "ciphertext": "<base64 — encrypted JSON + 16-byte GCM auth tag>"
  },
  "anchoredAt": "2026-03-14T10:00:00.000Z"
}
```

**Full-document (opt-in; document must be PII-free):**
```json
{
  "type": "MPCP:PolicyAnchor:1.0",
  "policyHash": "<sha256>",
  "submitMode": "full-document",
  "policyDocument": { ... },
  "anchoredAt": "2026-03-14T10:00:00.000Z"
}
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `MPCP_HCS_POLICY_TOPIC_ID` | HCS topic for policy anchoring |
| `MPCP_HCS_OPERATOR_ID` | Hedera operator account ID |
| `MPCP_HCS_OPERATOR_KEY` | Hedera operator private key |
| `HEDERA_NETWORK` | `testnet` or `mainnet` (default: `testnet`) |

### Reference Implementation

```typescript
import { hederaHcsAnchorPolicyDocument } from "mpcp-service/sdk";

// Hash-only (default)
const result = await hederaHcsAnchorPolicyDocument(policyDocument, {
  topicId: "0.0.12345",
  operatorId: "0.0.9876",
  operatorKey: "<key>",
});
// result.reference → "hcs:0.0.12345:42"
// result.submitMode → "hash-only"
// result.policyHash → "<sha256>"

// Encrypted
const aes256Key = globalThis.crypto.getRandomValues(new Uint8Array(32));
const result = await hederaHcsAnchorPolicyDocument(policyDocument, {
  topicId: "0.0.12345",
  operatorId: "0.0.9876",
  operatorKey: "<key>",
  submitMode: "encrypted",
  encryption: { key: aes256Key },
});
// Share aes256Key out-of-band with authorized auditors
```

### Verification via Mirror Node

```
GET https://testnet.mirrornode.hedera.com/api/v1/topics/{topicId}/messages/{sequenceNumber}
```

The response contains a base64-encoded message. Decode and verify:
1. `type === "MPCP:PolicyAnchor:1.0"`
2. `policyHash` matches `PolicyGrant.policyHash`
3. For `"encrypted"`: decrypt with the shared key and verify the decrypted document hashes to `policyHash`

---

## XRPL NFT-Backed PolicyGrant

### How it works

1. The policy authority (or wallet holder) mints a non-transferable XRPL NFToken
2. For `"hash-only"`: the NFT URI encodes the `policyHash` as a hex string
3. For `"encrypted"`: encrypt the policy document → upload to IPFS → NFT URI = `ipfs://{CID}`
4. The token ID is encoded as `"xrpl:nft:{tokenId}"` and placed in `anchorRef`
5. **Revocation** is accomplished by burning the NFToken

### Encrypted XRPL flow (preparation step)

The SDK provides `xrplEncryptAndStorePolicyDocument` to prepare the encrypted blob before minting.
NFT minting (write side) is handled by `mpcp-policy-authority`.

```typescript
import { xrplEncryptAndStorePolicyDocument } from "mpcp-service/sdk";

const aes256Key = globalThis.crypto.getRandomValues(new Uint8Array(32));

const prep = await xrplEncryptAndStorePolicyDocument(policyDocument, {
  encryption: { key: aes256Key },
  ipfsStore: myIpfsClient,  // implements PolicyDocumentIpfsStore
});

// prep.cid        → IPFS CID of the encrypted blob
// prep.policyHash → sha256 of the canonical policy document
// NFT URI = `ipfs://${prep.cid}`
// after minting: anchorRef = `xrpl:nft:${mintedTokenId}`
```

### IPFS store interface

The SDK does not bundle an IPFS client. Callers inject one:

```typescript
interface PolicyDocumentIpfsStore {
  upload(data: Uint8Array, filename?: string): Promise<string>; // returns CID
}
```

Compatible with `web3.storage`, `nft.storage`, a local IPFS node, or any content-addressed store.

### Revocation check

```typescript
import { checkXrplNftRevocation } from "mpcp-service/sdk";

const tokenId = grant.anchorRef?.replace("xrpl:nft:", "");
if (tokenId) {
  const { revoked } = await checkXrplNftRevocation(tokenId);
  if (revoked) { /* grant revoked — NFT burned */ }
}
```

### Comparison to `revocationEndpoint`

| Mechanism | Requires hosted service | Finality | Suitable for |
|-----------|------------------------|----------|--------------|
| `revocationEndpoint` | Yes | Soft | Enterprise, operator-controlled |
| XRPL NFT burn | No | Hard (on-chain) | Consumer, self-sovereign |

Both may be present on the same grant. Merchants SHOULD check both when present.

---

## Off-Chain Document Custody

When using `"hash-only"` mode (the default), the full policy document is never published to
the ledger. The **Service layer** (e.g. `mpcp-policy-authority`) acts as custodian.

Auditors retrieve the full document from the Service and verify it against the on-chain hash:

```typescript
import { InMemoryPolicyCustody } from "mpcp-service/sdk";

// Development / testing
const custody = new InMemoryPolicyCustody();
await custody.store(policyHash, policyDocument);

// Later — auditor retrieval
const doc = await custody.retrieve(policyHash);
// Verify: sha256(canonicalJson(doc)) === policyHash
```

`InMemoryPolicyCustody` is for development. Production implementations back the
`PolicyDocumentCustody` interface with a real database (see `mpcp-policy-authority`).

---

## `did:xrpl` Key Resolution

When a PolicyGrant is issued by an XRPL-native policy authority, the `issuer` field may carry a
`did:xrpl` DID. Verifiers can resolve this DID to retrieve the signing public key.

See [Key Resolution — `did:xrpl`](./key-resolution.md#didxrpl-did-resolution) for the full
resolution algorithm.

---

## Security Considerations

### HCS Topic Visibility

HCS messages are publicly readable via mirror nodes regardless of topic submit keys.
Use `"hash-only"` (default) or `"encrypted"` mode if the policy document contains
sensitive data. Never rely on topic access control for read privacy.

### Encryption Key Management

For `"encrypted"` mode, the AES-256 key must be shared out-of-band with authorized parties
(regulators, auditors). The key must be stored securely — loss of the key means the
on-chain document can never be decrypted. Key rotation requires re-anchoring.

### NFT Burn Finality

XRPL NFT burns are final and irreversible. Once a grant is revoked via NFT burn, it cannot
be un-revoked. Policy authorities MUST ensure the correct token is burned.

### Immutability and GDPR

Public ledger records are immutable. Policy documents (or hashes) published to a public
ledger cannot be deleted. For GDPR compliance:

- Use `"hash-only"` (the default) — the hash alone does not constitute personal data
- For `"encrypted"` mode — the ciphertext is not personal data if the decryption key is
  controlled and can be destroyed (key deletion = effective erasure)
- Never use `"full-document"` mode for documents containing personal data

### Offline Merchants

If `anchorRef` contains an XRPL NFT reference and the XRPL network is temporarily unavailable,
merchants SHOULD apply the same offline exception policy as for `revocationEndpoint` (see
[Human-to-Agent Profile](../profiles/human-agent-profile.md)).

---

## See Also

- [PolicyGrant](./PolicyGrant.md) — `anchorRef` field definition and revocation model
- [Key Resolution](./key-resolution.md) — `did:xrpl` DID resolution
- [Intent Anchoring](./anchoring.md) — settlement intent (not policy) anchoring
- [Human-to-Agent Profile](../profiles/human-agent-profile.md) — revocation and offline guidance
