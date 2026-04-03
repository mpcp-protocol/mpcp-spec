# Machine Payment Control Protocol (MPCP)

## Overview

The **Machine Payment Control Protocol (MPCP)** defines a cryptographically enforced pipeline for autonomous or software-controlled payments.

The protocol enables machines (vehicles, robots, services, AI agents, or IoT devices) to perform financial transactions while remaining constrained by deterministic policies.

Unlike traditional payment systems that rely on trusted intermediaries, MPCP enforces spending constraints through a sequence of signed authorization artifacts that are verified before settlement.

The protocol introduces a structured authorization flow:

Policy → Grant → Budget Authorization → Trust Gateway (Settlement) → Receipt

This architecture ensures that machine-initiated payments remain bounded, auditable, and verifiable.

---

# Motivation

Autonomous systems increasingly participate in economic activity.

Examples include:

- autonomous vehicles paying for parking, tolls, or charging
- delivery robots purchasing access to infrastructure
- IoT devices paying for services or resources
- AI agents executing automated purchases
- fleet-operated vehicles performing operational payments

Traditional payment systems are not designed for these environments because they assume a human actor approving each transaction.

Machine payments require a different model where:

- policies are defined ahead of time
- spending is constrained cryptographically
- authorization artifacts can be verified independently
- settlement can be audited after execution

MPCP provides this control layer.

---

# Core Design Principles

The protocol is built around the following principles:

### Policy First

All payments must derive from explicit policy rules.

Policies may define:

- allowed operators
- allowed payment rails
- allowed assets
- geographic restrictions
- spending limits
- approval requirements

### Bounded Autonomy

Machines may execute payments autonomously but only within policy-defined limits.

### Cryptographic Authorization

Each stage of the pipeline produces a signed artifact that constrains the next stage.

### Deterministic Verification

Settlement transactions must be verifiable against the authorization artifacts.

### Optional Public Attestation

Intent commitments can optionally be anchored to a public ledger for additional audit guarantees.

---

## Identity and Credentials

MPCP verification is identity-agnostic.

The protocol verifies authorization through cryptographic signatures on MPCP artifacts
(PolicyGrant → SignedBudgetAuthorization).

Public keys are distributed via **HTTPS well-known endpoints** — the baseline mechanism all conforming implementations MUST support. Keys are expressed as **JWK** (JSON Web Key, RFC 7517).

Deployments MAY additionally associate MPCP keys with decentralized identifiers (DIDs) or Verifiable Credentials (VCs), but this is never required for MPCP compliance.

See [Key Resolution](./key-resolution.md) for the full specification.

---

## Artifact Issuance and Signature Verification

Each MPCP artifact is created and signed by a specific authority responsible for that stage of the authorization pipeline.

The protocol requires that every artifact signature be independently verifiable using the public key of the issuing authority.

This ensures that authorization can be validated without contacting the original issuer.

### Artifact Authority Model

The MPCP artifact pipeline assigns responsibility for creation and signing as follows:

| Artifact | Created By | Signed By | Verified By |
|--------|-------------|-----------|-------------|
| PolicyGrant | Policy engine / operator system | Policy authority key | Trust Gateway |
| SignedBudgetAuthorization (SBA) | Session authority (fleet or operator backend) | Budget authorization key | Trust Gateway |

Each artifact constrains the parameters of the next stage in the protocol.

### Authority Domains

MPCP separates authority across multiple domains to reduce risk and improve auditability.

Typical deployments may use the following signing authorities:

| Authority | Example Owner |
|-----------|---------------|
| Policy authority | fleet operator or infrastructure provider |
| Budget authority | fleet backend or session controller |
| Wallet key | machine wallet or embedded secure element |

No single key is required to control the entire payment pipeline.

### Signature Verification Requirements

Implementations MUST verify signatures for the following artifacts:

- PolicyGrant
- SignedBudgetAuthorization

Signature verification MUST confirm:

- payload integrity
- signature validity
- that the signer is an authorized issuer for the artifact

Public keys MUST be retrievable as JWK objects via the issuer's HTTPS well-known endpoint:

```
GET https://{issuer-domain}/.well-known/mpcp-keys.json
```

The verifier looks up the entry where `kid` equals `issuerKeyId`. Implementations MAY also use pre-configured (pinned) keys in JWK format, which is the recommended approach for offline and air-gapped deployments.

DID resolution and Verifiable Credentials are optional and outside the core verification requirement.

See [Key Resolution](./key-resolution.md) for the full resolution algorithm, key set document format, and error codes.

### Verification Chain

The authorization chain verified by the Trust Gateway before settlement is:

```text
PolicyGrant.signature
↓
SignedBudgetAuthorization.signature
↓
Trust Gateway → XRPL Settlement → Receipt (txHash)
```

Each stage constrains the next stage and ensures that settlement parameters cannot be modified without invalidating the authorization chain.

---

# Protocol Versioning & Compatibility

## Version Field

All MPCP artifacts SHOULD include a semantic version string in the `version` field.

Example:

```json
{
  "version": "1.0",
  "decisionId": "dec_123",
  ...
}
```

The version identifies the protocol semantics used when producing the artifact.

---

## Versioning Model

MPCP uses semantic versioning: **MAJOR.MINOR**

Example: `1.0`, `1.1`, `2.0`

### Minor Versions

Minor versions may:

- add optional fields
- extend artifact structures
- introduce new rails or assets

Minor upgrades MUST remain backward compatible.

Verifiers MUST ignore unknown optional fields.

### Major Versions

Major versions may:

- change artifact semantics
- modify verification rules
- alter canonicalization requirements

Verifiers MUST reject artifacts whose major version they do not support.

---

## Forward Compatibility

Implementations MUST:

- ignore unknown optional fields
- preserve unknown fields when forwarding artifacts

This ensures MPCP artifacts remain interoperable between different implementations.

---

## Artifact Version Propagation

Artifacts SHOULD propagate the version they were produced under.

Example chain:

```text
PolicyGrant.version
    ↓
SBA.version
```

A verifier MAY reject chains containing mixed incompatible versions.

---

## Reference Version

The MPCP specification in this repository defines:

**Protocol Version: 1.0**

---

# Protocol Pipeline

The protocol operates as a multi-stage authorization pipeline.

```text
Policy Engine
      ↓
PolicyGrant
      ↓
SignedBudgetAuthorization (SBA)
      ↓
Trust Gateway (verifies + submits settlement)
      ↓
XRPL Receipt (txHash)
```

Each stage cryptographically binds the parameters for the following stage.
In MPCP, every settlement must be authorized by a deterministic chain of artifacts that progressively constrain the transaction parameters.

---

## Implementer Checklist

An implementation claiming MPCP compatibility MUST support the following capabilities.

### Artifact Handling

Implementations MUST be able to parse and validate the following artifacts:

- PolicyGrant
- SignedBudgetAuthorization (SBA)

### Canonical JSON

Implementations MUST produce identical hashes for the same artifact data.

Requirements:

- lexicographically sorted keys
- no insignificant whitespace
- UTF-8 encoding
- omit `null` / `undefined` fields
- monetary values encoded as strings

### Hash Domain Separation

Hashes MUST include the MPCP domain prefix.

Example:

```text
SHA256("MPCP:SBA:1.0:" || canonical_json(sba.authorization))
```

---

## Protocol Artifacts

The MPCP pipeline produces a series of structured artifacts. Each artifact constrains the next stage of the protocol and can be independently verified.

### PolicyGrant (signed by policy authority)

The **PolicyGrant** represents the admission of a machine into a controlled payment context. It is signed by the policy authority; verifiers use `issuer` and `issuerKeyId` to resolve the policy authority public key.

Example structure:

```json
{
  "version": "1.0",
  "grantId": "grant_abc123",
  "subjectId": "veh_001",
  "operatorId": "operator_42",
  "scope": "SESSION",
  "allowedRails": ["xrpl"],
  "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." }],
  "policyHash": "sha256(...)",
  "expiresAt": "2026-03-08T14:00:00Z",
  "issuer": "did:web:operator.example.com",
  "issuerKeyId": "policy-auth-key-1",
  "signature": "..."
}
```

The PolicyGrant defines the operational scope in which further authorizations may be issued. **Who signed:** policy authority (identified by `issuer`). **Which key:** `issuerKeyId` selects the signing key. **Verification:** resolve `policyAuthorityPublicKey` from `issuer` + `issuerKeyId` (config, DID, or registry), then verify `signature` over the canonical payload (all fields except `signature`).

---

### SignedBudgetAuthorization (SBA) (signed by budget authority)

The **SignedBudgetAuthorization (SBA)** establishes the maximum spending envelope available to the machine. It is signed by the budget (session) authority; verifiers use SBA issuer fields or deployment configuration to resolve the budget authority public key.

Example structure:

```json
{
  "authorization": {
    "version": "1.0",
    "budgetId": "budget_123",
    "grantId": "grant_abc123",
    "sessionId": "sess_456",
    "actorId": "ev-847",
    "policyHash": "a1b2c3...",
    "scopeId": "sess_456",
    "budgetScope": "SESSION",
    "currency": "USD",
    "minorUnit": 2,
    "maxAmountMinor": "30000000",
    "allowedRails": ["xrpl"],
    "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." }],
    "expiresAt": "2026-03-08T14:00:00Z"
  },
  "issuer": "did:web:fleet.example.com",
  "issuerKeyId": "budget-auth-key-1",
  "signature": "..."
}
```

The SBA ensures that spending remains within defined limits. Verification uses `budgetAuthorizationPublicKey` (resolved from issuer fields or config).

---

## Artifact Relationships

The protocol artifacts form a dependency chain. Each artifact references the previous stage and constrains the next.

```text
PolicyGrant
   ↓
SignedBudgetAuthorization (references grantId)
   ↓
Trust Gateway → XRPL Settlement → Receipt (txHash)
```

### Relationship Rules

**PolicyGrant → SBA**

- `SBA.authorization.grantId` MUST reference a valid `PolicyGrant.grantId`
- the SBA must respect the rail, asset, and policy constraints of the grant

**SBA → Trust Gateway**

- The Trust Gateway verifies the SBA signature and checks that the payment amount ≤ `SBA.authorization.maxAmountMinor`
- The gateway checks that rail and asset are within `SBA.authorization.allowedRails` / `allowedAssets`

The `maxAmountMinor` limit is expressed in the **on-chain asset's atomic units**. The session authority converts the fiat budget to on-chain units at SBA issuance time. Verifiers apply this check statelessly against the current payment with no currency conversion required. See [SignedBudgetAuthorization](./SignedBudgetAuthorization.md#stateless-verification-model) for the full model.

These relationships ensure that each stage of MPCP cryptographically and logically constrains the following stage, preventing unauthorized mutations or spending outside policy limits.

---

# Settlement Verification

Before submitting settlement, the Trust Gateway verifies:

- PolicyGrant schema validity
- PolicyGrant signature validity
- SBA schema validity
- SBA signature validity
- PolicyGrant → SBA linkage (`SBA.authorization.grantId`)
- policy hash consistency
- asset match
- destination match
- amount constraints
- authorization expiration

---

## Verification Algorithm

The Trust Gateway MUST perform the following steps before submitting an XRPL transaction.

### Step 0 — Verify Authorization Artifact Signatures

Verify the cryptographic signatures on all signed authorization artifacts.

Each artifact uses domain-separated hashing. The signed payload differs by artifact structure:

- **PolicyGrant** (flat structure) — Resolve using `grant.issuer` and `grant.issuerKeyId`. Signed payload: `SHA256("MPCP:PolicyGrant:1.0:" || canonicalJson(grantPayload))` where `grantPayload` is all grant fields except `signature`.
- **SignedBudgetAuthorization (SBA)** (envelope structure) — Resolve using `sba.issuer` and `sba.issuerKeyId`. Signed payload: `SHA256("MPCP:SBA:1.0:" || canonicalJson(sba.authorization))` — the inner `authorization` object only.

Resolve the public key (as JWK) for each authority using the HTTPS well-known endpoint or pre-configured keys. See [Key Resolution](./key-resolution.md) for the full algorithm.

```text
verify_signature(grant.signature, SHA256("MPCP:PolicyGrant:1.0:" || canonicalJson(grantPayload)), policyAuthorityPublicKey)
verify_signature(sba.signature,   SHA256("MPCP:SBA:1.0:"         || canonicalJson(sba.authorization)), budgetAuthorizationPublicKey)
```

If any signature verification fails → **reject settlement**.

---

### Step 1 — Verify Grant and Budget Lineage

Ensure that the authorization chain is valid.

```text
sba.authorization.grantId → PolicyGrant
```

Verification rules:

- `SBA.authorization.grantId` MUST reference a valid PolicyGrant
- artifacts MUST NOT be expired

If lineage is invalid → **reject settlement**.

---

### Step 2 — Verify Policy Constraints

Confirm the payment parameters match the authorized constraints.

Checks include:

- rail match: payment rail ∈ `SBA.allowedRails`
- asset match: payment asset ∈ `SBA.allowedAssets` — `kind` and all kind-specific fields must match exactly. See [Asset Matching](#asset).
- destination match
- amount ≤ authorized limit (`payment.amount ≤ SBA.maxAmountMinor`) — both values are in the on-chain asset's atomic units; no currency conversion is required at verification time
- purpose match (when applicable): if `PolicyGrant.allowedPurposes` is present and the settlement request includes a `purpose` field, the gateway SHOULD verify `purpose ∈ PolicyGrant.allowedPurposes`. Reject with `PURPOSE_NOT_ALLOWED` on mismatch. See [PolicyGrant — Purpose Enforcement](./PolicyGrant.md#purpose-enforcement).
- destination enforcement: if `PolicyGrant.destinationAllowlist` is present, the gateway MUST verify `payment.destination ∈ PolicyGrant.destinationAllowlist`. If `PolicyGrant.merchantCredentialIssuer` is present, the gateway MUST verify the destination holds a matching on-chain credential. When both are present, a destination satisfying **either** mechanism is approved. Reject with `DESTINATION_NOT_ALLOWED` or `DESTINATION_NOT_CREDENTIALED` on mismatch. See [PolicyGrant — Destination Enforcement](./PolicyGrant.md#destination-enforcement).
- policyHash consistency: the gateway confirms `PolicyGrant.policyHash` matches the expected policy for this deployment context. A verifier MAY recompute it as `SHA256("MPCP:Policy:<version>:" || canonicalJson(policyDocument))` when the policy document is available.

**Budget verification is stateless.** The gateway checks only that the current payment does not exceed the authorized envelope. The session authority is responsible for tracking cumulative spending across the scope. Gateways MUST NOT maintain a ledger of prior session payments.

If any constraint fails → **reject settlement**.

---

### Step 3 — Verify Expiration

Check expiration fields:

- `PolicyGrant.expiresAt`
- `SBA.expiresAt`

If any artifact is expired → **reject settlement**.

---

### Step 4 — Submit and Return Receipt

If all verification steps succeed, the gateway submits the XRPL transaction:

```text
submit XRPL transaction
return receipt { txHash, ... }
emit settlement event
```

---

# Canonical JSON Definition

## Protocol Identifier & Domain Separation

To prevent cross‑protocol hash collisions, MPCP implementations MUST apply **domain separation** when hashing protocol artifacts.

Hash inputs MUST be prefixed with a protocol‑specific identifier before hashing.

Recommended format:

```text
MPCP:<artifact-type>:<version>:<canonical-json>
```

Example:

```text
MPCP:SBA:1.0:{"actorId":"ev-847","allowedRails":["xrpl"],...}
```

Hash computation example for SBA:

```text
SHA256("MPCP:SBA:1.0:" || canonical_json(sba.authorization))
```

This ensures:

- MPCP hashes cannot collide with hashes from other protocols
- different MPCP artifact types produce distinct hash domains
- future protocol versions remain cryptographically isolated

Implementations MUST apply the same domain prefix rules when generating and verifying hashes.

The version component in the domain prefix MUST use the same semantic version string carried in the artifact, for example `1.0`, `1.1`, or `2.0`. This keeps hashing behavior aligned with MPCP version negotiation and prevents ambiguity between artifact formats.

To ensure deterministic hashing across systems, MPCP defines a **canonical JSON encoding** used when computing artifact hashes.

All implementations MUST apply the same canonicalization rules before hashing.

Canonicalization rules:

1. Object keys MUST be sorted lexicographically.
2. No insignificant whitespace is allowed.
3. Numbers MUST be encoded as strings when representing monetary values.
4. Unicode strings MUST be UTF-8 encoded.
5. Fields with `null` or `undefined` values MUST be omitted.

Example:

Input object:

```json
{
  "destination": "rDest...",
  "amount": "19440000",
  "rail": "xrpl"
}
```

Canonical form:

```text
{"amount":"19440000","destination":"rDest...","rail":"xrpl"}
```

Hash computation example for SBA:

```text
SHA256("MPCP:SBA:1.0:" || canonical_json(sba.authorization))
```

---

# Signature Schemes

MPCP supports multiple cryptographic signature schemes depending on the environment in which the policy authority operates.

Implementations SHOULD support at least one of the following:

### Ed25519

Recommended for most policy authorities.

Advantages:

- fast verification
- small signatures
- widely supported

### secp256k1

Common in blockchain systems including:

- Bitcoin
- Ethereum
- many EVM chains

Useful when authorization artifacts must be verified by smart contracts.

### Verification Requirements

Regardless of scheme, signature verification MUST validate:

- payload integrity
- signer identity
- signature scheme compatibility

---

# Replay Protection

MPCP must prevent the reuse of authorization artifacts across multiple settlements.

Replay protection is enforced through **SBA ID uniqueness** and **transaction binding**.

### SBA ID Uniqueness

Each **SBA** contains a `budgetId`. The Trust Gateway MUST NOT accept the same SBA for more than one settlement submission.

The operator backend SHOULD record `(sba.budgetId, settlementTxId)` at settlement acceptance to prevent the same SBA from being applied to a second settlement.

### Transaction Binding

After settlement execution, the operator backend SHOULD record the settlement transaction identifier against the SBA `budgetId`.

Examples:

- XRPL `txHash`
- Ethereum `transactionHash`

Once a transaction identifier is recorded against a `budgetId`, the operator backend MUST NOT accept a second settlement for the same SBA.

---

# Threat Model

The MPCP protocol is designed to mitigate the following threats.

### Unauthorized Machine Spending

A compromised machine wallet cannot exceed authorized budgets because:

- payments require a valid SBA signed by the session authority
- the Trust Gateway verifies the SBA against the PolicyGrant before submitting

### Transaction Mutation

The Trust Gateway verifies that the payment parameters (rail, asset, amount, destination) match the constraints in the SBA before submitting. Any attempt to exceed the SBA envelope is rejected.

### Replay Attacks

Expired or previously used authorizations cannot be reused due to:

- expiration checks on all artifacts (gateway-enforced, stateless)
- `(budgetId, settlementTxId)` binding recorded by the operator backend at settlement acceptance

### Policy Bypass

Machines cannot bypass policy constraints because every authorization chain must derive from:

```text
PolicyGrant → SBA → Trust Gateway
```

### Purpose Bypass (Agent Compromise)

A compromised agent could skip its own `allowedPurposes` check and issue SBAs for unauthorized
merchant categories. To mitigate this, the Trust Gateway SHOULD enforce `allowedPurposes` from
the PA-signed PolicyGrant before submitting each settlement transaction. When the settlement
request includes a `purpose` field, the gateway checks it against `PolicyGrant.allowedPurposes`
and rejects with `PURPOSE_NOT_ALLOWED` on mismatch. See [PolicyGrant — Purpose Enforcement](./PolicyGrant.md#purpose-enforcement).

### Destination Forgery (Agent Compromise)

A compromised agent could populate the SBA `destinationAllowlist` with an attacker-controlled
address, directing funds away from legitimate merchants. Because the SBA is agent-signed, the
agent controls this field unless bounded by the PA-signed PolicyGrant.

**Mitigation:** The PA-signed `destinationAllowlist` on the PolicyGrant provides a tamper-proof
allowlist. The gateway MUST verify `payment.destination ∈ PolicyGrant.destinationAllowlist`
before settling. For deployments requiring dynamic merchant management, the PA can issue XRPL
Credentials (XLS-70) to approved merchants and reference them via `merchantCredentialIssuer`
and `merchantCredentialType` on the PolicyGrant. See [PolicyGrant — Destination Enforcement](./PolicyGrant.md#destination-enforcement).

### Cumulative Budget Overspend

The Trust Gateway is stateless and checks only that the current payment amount does not exceed `SBA.maxAmountMinor`. It does not track prior payments in the session.

**Session authority responsibility:** The session authority MUST maintain a running total of amounts spent within the budget scope and MUST only issue new SBAs within the remaining authorized envelope.

The reference implementation exposes `cumulativeSpentMinor` in `SettlementVerificationContext` so callers can pass the running total to the gateway for an accurate cumulative check:

```
if (cumulativeSpentMinor + currentPayment > maxAmountMinor) → budget_exceeded
```

In offline or air-gapped deployments, the session authority cannot contact the verifier in real time. In these environments, cumulative enforcement relies on trusted wallet hardware maintaining the spending counter locally.

### Policy Authority Key Compromise

If a PA signing key is compromised, an attacker can forge PolicyGrants with unlimited budgets.
MPCP mitigates this with two complementary revocation mechanisms:

1. **JWKS `active` field** — the PA sets `active: false` on the compromised key in its JWKS
   endpoint. Verifiers MUST reject keys with `active: false`. Verifiers that cache the key set
   will stop trusting the key on their next fetch.
2. **XRPL Credential key lifecycle** — the PA issues a self-referencing on-chain credential for
   each active signing key. On compromise, the PA deletes the credential. Verifiers check the
   ledger for near-instant (ledger finality ~4s) revocation.

Trust Bundles that embedded the key before revocation remain valid until their `expiresAt`.
Deployments SHOULD use short Trust Bundle lifetimes in high-assurance environments. See
[Key Revocation](./key-resolution.md#key-revocation).

### Gateway Seed Compromise

If an attacker obtains the Trust Gateway's XRPL private key, they can submit transactions on
behalf of the gateway — potentially draining all active escrows simultaneously. Per-grant escrow
bounds exposure per grant, but aggregate exposure is the sum of all active `budgetMinor` values.

**Mitigations:** Production gateways SHOULD store the private key in an HSM/KMS. The PA SHOULD
issue an XRPL Credential (XLS-70) to the gateway account; on compromise, the PA deletes the
credential to revoke the gateway's on-chain authorization. Operators SHOULD monitor for
on-chain payments without corresponding SBAs. See [Gateway Seed Security](./trust-model.md#gateway-seed-security).

### Settlement Tampering

Verification ensures that executed settlement transactions match authorized parameters before the session is finalized.

---

# Known Limitations

## Grant Revocation

MPCP does not define a revocation mechanism for PolicyGrants or SBAs. Once issued, an artifact remains valid until its `expiresAt` timestamp passes.

**Mitigation:** Issue short-lived grants (recommended: < 15 minutes for high-risk sessions). In scenarios where immediate revocation is required, the session authority should decline to issue new SBAs; the current grant will expire naturally.

**Revocation extension:** The `revocationEndpoint` field on PolicyGrant supports real-time revocation checks. See the [Human-to-Agent Profile](../profiles/human-agent-profile.md#revocation) for the full revocation contract.

---

These sections define the core interoperability rules required for MPCP implementations across different systems and settlement rails.

---

# Deployment Profiles

MPCP defines deployment profiles based on the actors involved and the connectivity requirements. The Trust Gateway is mandatory in all profiles — the authorization chain ends at the SBA.

| Profile | Description | Typical use |
|---------|-------------|-------------|
| Human-Agent | Human signs PolicyGrant (DID key); AI agent issues SBAs; Trust Gateway settles | AI travel/task delegation |
| Transparent Gateway | Gateway hosts PA internally; budget owner configures via API | SaaS, early-adoption deployments |

See [Human-Agent Profile](../profiles/human-agent-profile.md) and [Transparent Gateway Profile](../profiles/gateway-profile.md) for detailed guidance.

---

# Wire Formats

This section defines the canonical wire-format expectations for MPCP artifacts.

All artifacts SHOULD be represented as UTF-8 JSON documents using the canonical JSON rules defined above when used for hashing or signing.

## Shared Types

### Asset

An `Asset` is a discriminated union object that fully identifies a payment asset by kind. String-only asset references are not valid — structured `Asset` objects MUST be used in all `allowedAssets` arrays and `asset` fields throughout the protocol.

The `kind` field is the discriminator. Three variants are defined:

**XRPL IOU**

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `"IOU"` | Discriminator |
| `currency` | string | Currency code (e.g. `"RLUSD"`, `"USDC"`) |
| `issuer` | string | XRPL issuer address |

**XRP (native)**

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `"XRP"` | Discriminator |

**EVM ERC-20**

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `"ERC20"` | Discriminator |
| `chainId` | number | EVM chain ID (e.g. `1` for Ethereum mainnet) |
| `token` | string | ERC-20 contract address |

Examples:

```json
{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." }
{ "kind": "XRP" }
{ "kind": "ERC20", "chainId": 1, "token": "0xContractAddress..." }
```

#### Asset Matching

Two `Asset` objects match when their `kind` is equal and all kind-specific fields match exactly.

The `∈` operator used in artifact relationship rules (`payment.asset ∈ SBA.allowedAssets`) means: at least one entry in `allowedAssets` matches the payment asset using the rules above.

---

## PolicyGrant Wire Format

```json
{
  "version": "1.0",
  "grantId": "grant_abc123",
  "subjectId": "veh_001",
  "operatorId": "operator_42",
  "scope": "SESSION",
  "allowedRails": ["xrpl"],
  "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." }],
  "policyHash": "sha256(...)",
  "expiresAt": "2026-03-08T14:00:00Z",
  "issuer": "did:web:operator.example.com",
  "issuerKeyId": "policy-auth-key-1",
  "signature": "..."
}
```

- `issuer` — Identifier for the policy authority (e.g. DID, domain, or registry ID). Verifiers use this to resolve the signing key.
- `issuerKeyId` — Identifies the specific key used to sign (for deployments with multiple keys per issuer).
- `signature` — Cryptographic signature over the canonical JSON of the grant payload (all fields except `signature`).

## SignedBudgetAuthorization Wire Format

```json
{
  "authorization": {
    "version": "1.0",
    "budgetId": "budget_123",
    "grantId": "grant_abc123",
    "sessionId": "sess_456",
    "actorId": "ev-847",
    "policyHash": "a1b2c3...",
    "scopeId": "sess_456",
    "budgetScope": "SESSION",
    "currency": "USD",
    "minorUnit": 2,
    "maxAmountMinor": "30000000",
    "allowedRails": ["xrpl"],
    "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." }],
    "expiresAt": "2026-03-08T14:00:00Z"
  },
  "issuer": "did:web:fleet.example.com",
  "issuerKeyId": "budget-auth-key-1",
  "signature": "..."
}
```

## Artifact Bundle

An **artifact bundle** packages complete payment verification data (policyGrant, sba, receipt/txHash, optional ledgerAnchor) into a single JSON object for exchange between systems. See [ArtifactBundle.md](./ArtifactBundle.md) for the canonical format and schema.

---

# Error Codes

MPCP implementations SHOULD expose stable machine-readable error codes during verification and settlement rejection.

Recommended codes:

| Code | Meaning |
|------|---------|
| KEY_REVOKED | Signing key is revoked (`active: false` in JWKS or on-chain credential deleted) |
| POLICY_GRANT_SIGNATURE_INVALID | PolicyGrant signature verification failed |
| SBA_SIGNATURE_INVALID | SBA signature verification failed |
| POLICY_GRANT_NOT_FOUND | Referenced PolicyGrant does not exist |
| SBA_NOT_FOUND | Referenced SBA does not exist |
| ARTIFACT_EXPIRED | One or more artifacts expired |
| POLICY_HASH_MISMATCH | Policy hash does not match authorized policy |
| RAIL_MISMATCH | Payment rail differs from authorization |
| ASSET_MISMATCH | Payment asset differs from authorization |
| DESTINATION_MISMATCH | Payment destination differs from authorization |
| AMOUNT_EXCEEDED | Payment amount exceeds authorized limit |
| TX_REPLAYED | Settlement transaction identifier has already been consumed |
| PURPOSE_NOT_ALLOWED | Settlement request purpose is not in `PolicyGrant.allowedPurposes` |
| DESTINATION_NOT_ALLOWED | Payment destination not in `PolicyGrant.destinationAllowlist` and no credential match |
| DESTINATION_NOT_CREDENTIALED | `merchantCredentialIssuer` is set but destination does not hold a matching on-chain credential |
| SCOPE_UNSUPPORTED | Authorization scope is not supported by the verifier |

Error codes SHOULD remain stable across implementations whenever possible to preserve interoperability.

---

# Reference Verification Pseudocode

The following pseudocode illustrates a minimal verifier implementation.

```text
function verifyAndSettle(grant, sba, payment):
    verifySignature(grant, policyAuthorityPublicKey)
    verifySignature(sba, budgetAuthorizationPublicKey)
    verifyLineage(grant, sba)
    verifyNotExpired(grant, sba)
    verifyPolicyHash(grant, sba)
    verifyBudgetConstraints(sba, payment)

    # Submit XRPL transaction and return receipt
    txHash = xrpl.submitPayment(payment)
    return { txHash }
```

This pseudocode is illustrative only. The Trust Gateway checks signatures, lineage, constraints, and expiration before submitting the XRPL payment.

---

# State Machine

MPCP authorization and settlement artifacts move through a small set of states.

## PolicyGrant

```text
ISSUED → EXPIRED
```

## SignedBudgetAuthorization

```text
ISSUED → EXPIRED
```

## Settlement

```text
PENDING → VERIFIED (txHash returned)
PENDING → REJECTED
```

## State Machine Rules

- An expired grant or SBA MUST NOT authorize settlement. Enforcement: the gateway checks `expiresAt` statelessly.
- A verified settlement MUST bind to exactly one SBA. Enforcement: the operator backend records the binding.
- A rejected settlement MUST NOT advance the session to a closed state.

This state model keeps MPCP deterministic and makes replay protection enforceable without requiring shared state in the verifier.

---

# Optional Policy Attestation

To enhance auditability, MPCP supports anchoring the policy document hash to a public ledger at grant issuance time.

The `anchorRef` field on PolicyGrant points to an on-chain record:

```text
"hcs:{topicId}:{sequenceNumber}"   — Hedera HCS message
"xrpl:nft:{tokenId}"               — XRPL non-transferable NFToken
```

This provides:

- tamper-evident policy history
- public timestamp proofs
- dispute resolution capabilities

See [Policy Anchoring](./policy-anchoring.md) for the full specification.

---

# Security Properties

The protocol prevents:

- unauthorized machine spending
- transaction mutation attacks
- replay of expired authorizations
- exceeding policy budgets
- unauthorized settlement destinations

Because each stage is cryptographically bound, a machine cannot bypass constraints without invalidating verification.

---

# Applications

MPCP can be applied across many autonomous payment scenarios:

- parking systems
- EV charging networks
- tolling infrastructure
- robotic logistics
- fleet management
- IoT service payments
- AI agent marketplaces

---

# Protocol Extensions

MPCP may be extended through additional authorization artifacts that introduce new policy authorities or control layers.

Extensions MUST preserve the core MPCP lineage model and MUST NOT weaken the verification guarantees defined by the protocol.

Current extensions include:

## FleetPolicyAuthorization (FPA)

FleetPolicyAuthorization introduces **fleet‑side policy authority** into MPCP.

In many real-world deployments, machines operate under the control of a **fleet operator** rather than directly under the service provider issuing the PolicyGrant.  
Examples include:

- robotaxi fleets
- delivery fleets
- logistics robots
- autonomous trucking

FleetPolicyAuthorization allows fleets to issue a signed policy artifact that constrains machine payments before operator authorization occurs.

The effective payment policy therefore becomes the **intersection of fleet policy and operator policy**.

```
FleetPolicyAuthorization
        ↓
PolicyGrant
        ↓
SignedBudgetAuthorization
        ↓
Trust Gateway → XRPL Settlement → Receipt
```

The FleetPolicyAuthorization artifact defines constraints such as:

- fleet-level spending caps
- approved service operators
- permitted payment rails
- permitted assets
- geographic restrictions

During settlement verification, implementations MUST ensure that all MPCP artifacts remain compliant with the constraints imposed by the FleetPolicyAuthorization artifact.

The full extension specification is defined in [FleetPolicyAuthorization.md](./FleetPolicyAuthorization.md).

# Future Extensions

Possible extensions include:

- fleet-level authorization hierarchies
- delegated policy authorities
- programmable payment intents
- zero-knowledge compliance proofs
- multi-chain settlement verification
- cross-operator interoperability

---

# Conclusion

The Machine Payment Control Protocol provides a framework for secure, policy-bounded autonomous payments.

By structuring payments as a chain of cryptographically constrained authorizations, MPCP allows machines to transact independently while maintaining strong guarantees around spending limits, policy compliance, and settlement integrity.
