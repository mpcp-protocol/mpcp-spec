# Policy Anchoring

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

---

## Overview

MPCP supports **on-chain policy anchoring** — recording a commitment to a PolicyGrant's source
policy document on a distributed ledger to create a tamper-evident, third-party-auditable trail.

Policy anchoring records the **policy authorization itself**, enabling
audit of what constraints were in force when a grant was issued.

Anchoring patterns:

| Pattern | When to use |
|---------|-------------|
| **HCS Policy Anchoring** | Institutional deployments requiring audit trails; any third party can verify the policy hash |
| **XRPL (credentials, not NFT)** | **Grant revocation** on XRPL uses XLS-70 Credentials (`PolicyGrant.activeGrantCredentialIssuer`) — see [PolicyGrant — Revocation](./PolicyGrant.md#revocation). Policy hash anchoring on XRPL uses the same HCS-style commitment patterns where applicable, or off-chain custody with `policyHash`. |

**Deprecated:** NFToken-based anchoring (`xrpl:nft:{tokenId}`) and burn-to-revoke are **not**
normative for new deployments. Use Credentials instead.

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
| `xrpl:nft:{tokenId}` | **Deprecated.** Do not issue new grants with this pattern. |

**XRPL revocation** is defined by `activeGrantCredentialIssuer` on the PolicyGrant, not by
`anchorRef`. See [PolicyGrant](./PolicyGrant.md).

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

## XRPL: policy audit and grant revocation (Credentials)

On XRPL, MPCP separates **policy document audit** from **grant liveness**:

1. **Policy hash audit** — Use Hedera HCS (`anchorRef` with `hcs:...`) or off-chain custody with a
   published `policyHash` on the grant. This matches the privacy model in this document
   (`hash-only` default).

2. **Grant revocation** — Use **XLS-70 Credentials**, not NFToken burn. At grant issuance the PA
   issues `CredentialCreate` with `Issuer` = `activeGrantCredentialIssuer`, `Subject` = grant
   subject XRPL account, and `CredentialType` = `hexUTF8("mpcp:active-grant:" + grantId)`. The
   subject accepts the credential on-ledger. **Revocation** is `CredentialDelete` by the issuer.

3. **Verifiers** — The Trust Gateway and online merchants query the ledger for the credential.
   Absence implies revocation. No HTTP `revocationEndpoint` is required for this path.

Historical implementations that minted a non-transferable NFToken and placed `xrpl:nft:{tokenId}`
in `anchorRef` relied on **burn-to-revoke**. That pattern is **deprecated**; new deployments MUST
use Credentials as specified in [PolicyGrant — Revocation](./PolicyGrant.md#revocation).

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

### Credential deletion finality

XRPL `CredentialDelete` is final on-ledger. A new grant requires a new credential issuance. Policy
authorities MUST target the correct (`Subject`, `Issuer`, `CredentialType`) tuple.

### Immutability and GDPR

Public ledger records are immutable. Policy documents (or hashes) published to a public
ledger cannot be deleted. For GDPR compliance:

- Use `"hash-only"` (the default) — the hash alone does not constitute personal data
- For `"encrypted"` mode — the ciphertext is not personal data if the decryption key is
  controlled and can be destroyed (key deletion = effective erasure)
- Never use `"full-document"` mode for documents containing personal data

### Offline Merchants

Offline merchants cannot query XRPL for credential status. They SHOULD apply the same
risk-based policy as for HTTP revocation when connectivity is absent (see
[Human-to-Agent Profile](../profiles/human-agent-profile.md)).

---

## See Also

- [PolicyGrant](./PolicyGrant.md) — `anchorRef` field definition and revocation model
- [Key Resolution](./key-resolution.md) — `did:xrpl` DID resolution
- [Human-to-Agent Profile](../profiles/human-agent-profile.md) — revocation and offline guidance
