# PolicyGrant

Artifact Type: MPCP:PolicyGrant

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

---

## Purpose

A **PolicyGrant** represents the result of a policy evaluation performed before a machine is allowed to initiate payment activity.

The PolicyGrant defines the **initial permission envelope** for a session or payment scope. It constrains which rails, assets, and spending limits may later be authorized via the **SignedBudgetAuthorization (SBA)**.

PolicyGrant is typically produced by a policy engine during an **entry phase** when a machine, vehicle, or agent attempts to access a service.

The PolicyGrant is a **signed artifact**. It is signed by the policy authority; verifiers use `issuer` and `issuerKeyId` to resolve the policy authority public key for signature verification.

---

## Problem

In autonomous payment environments (vehicles, robots, AI agents), a system must determine **whether payment activity is allowed before any transaction is authorized**.

Without a formal grant artifact:

- agents may bypass policy
- payment decisions may not be traceable to policy evaluation
- downstream authorizations cannot prove they were derived from policy

PolicyGrant solves this by creating a **verifiable policy snapshot** that later artifacts must reference.

---

## Policy Lifecycle Context

Policy evaluation follows this chain:

```
PolicyGrant
     ↓
SignedBudgetAuthorization (SBA)
     ↓
Trust Gateway → XRPL Settlement
```

PolicyGrant establishes the **upper policy boundary** that subsequent artifacts must respect.

For example:

- allowed rails
- allowed assets
- spending caps
- policy expiration

Downstream artifacts must be **subsets of the PolicyGrant constraints**.

---

## Structure

### PolicyGrant (payload)

| Field | Type | Required | Description |
|------|------|----------|-------------|
| version | string | yes | MPCP semantic version (e.g. "1.0") |
| grantId | string | yes | Unique identifier for the grant |
| policyHash | string | yes | SHA-256 hash of the canonical policy document from which this grant was issued. Computed as `SHA256("MPCP:Policy:<version>:" \|\| canonicalJson(policyDocument))`. Downstream SBA artifacts MUST carry the same value. |
| subjectId | string | yes | Identifier of the entity receiving the grant (vehicle, agent, wallet, etc.) |
| operatorId | string | optional | Service operator identifier |
| scope | string | yes | Scope of the grant (SESSION, VEHICLE, FLEET, etc.) |
| allowedRails | Rail[] | yes | Payment rails permitted by policy |
| allowedAssets | Asset[] | conditional | Allowed assets for on-chain rails |
| maxSpend | object | optional | Spending caps defined by policy |
| expiresAt | string | yes | ISO 8601 expiration timestamp |
| requireApproval | boolean | optional | Indicates that further approval is required before payment |
| reasons | string[] | optional | Policy evaluation reasons |
| issuer | string | yes | Identifier for the policy authority (e.g. DID, domain, or registry ID). Verifiers use this to resolve the signing key. |
| issuerKeyId | string | yes | Identifies the specific key used to sign (for deployments with multiple keys per issuer). |
| signature | string | yes | Cryptographic signature over the canonical JSON of the grant payload (all fields except `signature`). |
| revocationEndpoint | string | optional | **Legacy — HTTP revocation** for non-XRPL rails or transitional deployments. If present, merchants MAY call this URL before accepting payment. **XRPL deployments SHOULD use `activeGrantCredentialIssuer` instead** — see **Revocation** below. |
| activeGrantCredentialIssuer | string | optional | XRPL address of the PA (or delegate) that issues the **active grant** XLS-70 Credential. When present, online verifiers (including the Trust Gateway) MUST treat the grant as revoked if that credential does not exist on the subject's XRPL account. Replaces HTTP `revocationEndpoint` for XRPL-native flows. See **Revocation** below. |
| allowedPurposes | string[] | optional | Merchant category allowlist (e.g. `["travel:hotel", "travel:flight"]`). PA-signed. The agent MUST check purpose before issuing each SBA. The Trust Gateway SHOULD enforce purpose when the settlement request includes a `purpose` field. See **Purpose Enforcement** section below. |
| anchorRef | string | optional | Pointer to an on-chain record of the policy document. Format: `"hcs:{topicId}:{sequenceNumber}"` (Hedera HCS). The historical `xrpl:nft:{tokenId}` pattern is **deprecated** and MUST NOT be used in new deployments; use HCS (or off-chain custody) for policy hash audit and `activeGrantCredentialIssuer` for XRPL grant revocation. See **Policy Document Anchoring** below. |
| budgetMinor | string | optional | PA-signed budget ceiling in the smallest currency unit (e.g. drops for XRP). The Trust Gateway enforces this as a hard ceiling — it is never read from the UI or agent. |
| budgetCurrency | string | optional | Currency of `budgetMinor` (e.g. `"XRP"`). |
| budgetEscrowRef | string | optional | URI reference to the on-chain budget escrow that pre-reserves the full `budgetMinor`. Format: `"{rail}:{mechanism}:{identifier}"` (e.g. `"xrpl:escrow:{account}:{sequence}"`). PA-signed. See [Rails](./rails.md). |
| authorizedGateway | string | optional | XRPL address of the only Trust Gateway authorized to submit payments against this grant's escrow. The gateway rejects payment requests if its own address does not match. PA-signed. |
| destinationAllowlist | string[] | optional | PA-signed allowlist of permitted payment destination addresses (e.g. XRPL `r`-addresses). When present, the Trust Gateway MUST verify that the payment destination is in this list before settling. SBA `destinationAllowlist` MUST be a subset. See **Destination Enforcement** section below. |
| merchantCredentialIssuer | string | optional | XRPL address of the credential issuer for approved merchants. Used with XLS-70 on-chain Credentials for dynamic destination enforcement. See **Destination Enforcement** section below. |
| merchantCredentialType | string | optional | Hex-encoded credential type that approved merchants must hold (e.g. `hex("mpcp:approved-merchant")`). Used with `merchantCredentialIssuer`. |
| subjectCredentialIssuer | string | optional | XRPL address of the credential issuer that attests the subject's identity. When present, the gateway SHOULD verify on-chain that `subjectId`'s XRPL account holds a valid credential from this issuer. See **Subject Attestation** section below. |
| subjectCredentialType | string | optional | Hex-encoded credential type the subject must hold (e.g. `hex("mpcp:fleet-agent")`). Used with `subjectCredentialIssuer`. |
| offlineMaxSinglePayment | string | optional | PA-signed per-transaction cap (in `offlineMaxSinglePaymentCurrency` minor units) for offline merchant acceptance. Offline merchants MUST reject SBAs whose `maxAmountMinor` exceeds this value. Cumulative offline exposure across merchants is only bounded when `offlineMaxCumulativePayment` is present; see **Offline cumulative exposure** below. |
| offlineMaxSinglePaymentCurrency | string | optional | Currency of `offlineMaxSinglePayment` (e.g. `"XRP"`). |
| offlineMaxCumulativePayment | string | optional | PA-signed maximum total amount (in `offlineMaxCumulativePaymentCurrency` minor units) that offline verifiers MAY cumulatively accept for this grant across all offline transactions at this verifier. Merchants SHOULD sum accepted amounts per `grantId` and reject when the next acceptance would exceed this cap. See **Offline cumulative exposure** below. |
| offlineMaxCumulativePaymentCurrency | string | optional | Currency of `offlineMaxCumulativePayment` (e.g. `"XRP"`). If absent while `offlineMaxCumulativePayment` is present, implementations SHOULD use `offlineMaxSinglePaymentCurrency`. |

---

## Example

```json
{
  "version": "1.0",
  "grantId": "grant_7ab3",
  "policyHash": "9f3a0d...",
  "subjectId": "vehicle_1284",
  "operatorId": "operator_12",
  "scope": "SESSION",
  "allowedRails": ["xrpl", "stripe"],
  "allowedAssets": [{ "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer..." }],
  "allowedPurposes": ["transport:toll", "transport:charging", "transport:parking"],
  "destinationAllowlist": ["rChargingStation1", "rTollBooth42"],
  "merchantCredentialIssuer": "rPAMerchantRegistry",
  "merchantCredentialType": "6D7063703A617070726F7665642D6D65726368616E74",
  "activeGrantCredentialIssuer": "rPolicyAuthorityXrpl...",
  "offlineMaxSinglePayment": "5000000",
  "offlineMaxSinglePaymentCurrency": "XRP",
  "offlineMaxCumulativePayment": "15000000",
  "offlineMaxCumulativePaymentCurrency": "XRP",
  "maxSpend": {
    "perTxMinor": "5000",
    "perSessionMinor": "20000"
  },
  "expiresAt": "2026-03-08T14:00:00Z",
  "requireApproval": false,
  "reasons": ["OK"],
  "issuer": "did:web:operator.example.com",
  "issuerKeyId": "policy-auth-key-1",
  "signature": "..."
}
```

---

## Policy Intersection Model

PolicyGrant may represent the intersection of multiple policy sources.

Example policy layers:

- operator policy
- fleet policy
- user policy
- regulatory policy

The effective policy becomes:

```
effectivePolicy =
    operatorPolicy
 ∩  fleetPolicy
 ∩  userPolicy
 ∩  regulatoryPolicy
```

The PolicyGrant stores the **resulting effective constraints**.

---

## Relationship to SBA

A **SignedBudgetAuthorization** must always be a subset of the PolicyGrant.

For example:

```
SBA.allowedRails ⊆ PolicyGrant.allowedRails
SBA.allowedAssets ⊆ PolicyGrant.allowedAssets
SBA.maxAmount ≤ PolicyGrant.maxSpend
```

The SBA must reference the same **policyHash** used to produce the PolicyGrant.

---

## Expiration

PolicyGrant defines the **maximum validity window** for downstream artifacts.

Implementations MUST ensure:

- SBA expiration does not exceed PolicyGrant expiration

---

## Policy Hashing

`policyHash` is the SHA-256 hash of the canonical policy document from which the PolicyGrant was issued.

The policy document is the structured representation of the rules evaluated to produce the grant (operator policy, fleet policy, regulatory constraints, etc.). It MUST be serialized using MPCP canonical JSON before hashing.

Computation:

```
policyHash = SHA256("MPCP:Policy:<version>:" || canonicalJson(policyDocument))
```

Example:

```
policyHash = SHA256("MPCP:Policy:1.0:" || '{"allowedAssets":[...],"allowedRails":[...],...}')
```

The `policyHash` is not a hash of the PolicyGrant artifact itself — it is a hash of the **source policy** that the grant was derived from.

Downstream SBA artifacts MUST carry the same `policyHash`. During settlement verification, the Trust Gateway checks that `PolicyGrant.policyHash` and `SBA.policyHash` are equal, confirming the entire authorization chain derives from the same policy snapshot.

---

## Signing Requirements

PolicyGrant MUST be cryptographically signed by the policy authority. Verifiers that have a public key configured MUST verify the signature and MUST reject unsigned grants.

### Domain Hash

The signed payload uses domain-separated hashing:

```
hash = SHA256("MPCP:PolicyGrant:1.0:" || canonicalJson(grantPayload))
signature = sign(hash, policyAuthorityPrivateKey)
```

where `grantPayload` is all grant fields except `signature`, serialized as canonical JSON.

### Reference Implementation — Environment Variables

The reference implementation (`policyGrant.ts`) exposes signing and verification via environment variables:

| Variable | Purpose |
|----------|---------|
| `MPCP_POLICY_GRANT_SIGNING_PRIVATE_KEY_PEM` | Private key for signing PolicyGrants |
| `MPCP_POLICY_GRANT_SIGNING_PUBLIC_KEY_PEM` | Public key for verifying PolicyGrant signatures. When set, unsigned grants are rejected. |
| `MPCP_POLICY_GRANT_SIGNING_KEY_ID` | Key identifier (default: `mpcp-policy-grant-signing-key-1`) |

Functions:
- `createSignedPolicyGrant(grant)` — signs the grant, returns `SignedPolicyGrant`
- `verifyPolicyGrantSignature(envelope)` — verifies the signature

### Enforcement

If `MPCP_POLICY_GRANT_SIGNING_PUBLIC_KEY_PEM` is set:
- Grants without `issuerKeyId` and `signature` are rejected with `invalid_policy_grant_signature`
- Grants with an invalid signature are rejected with `invalid_policy_grant_signature`

If the env var is not set, signature verification is skipped (backward-compatible mode for environments using pre-validated grants).

If signature verification fails, the verifier MUST reject the grant.

### Key Resolution

Verifiers resolve the public key (as JWK) using `issuer` and `issuerKeyId` via the HTTPS well-known endpoint or pre-configured keys. See [Key Resolution](./key-resolution.md).

---

## Policy Document Anchoring

The `anchorRef` field is an optional pointer to an on-chain record of the policy document that
produced this grant. Two formats are supported:

```
"hcs:{topicId}:{sequenceNumber}"   — Hedera Consensus Service message
```

**Verifier behavior:** The MPCP verifier passes `anchorRef` through without enforcement. It is
informational metadata used by auditors, merchants, and dispute resolution tooling.

See [Policy Anchoring](./policy-anchoring.md) for the full anchoring specification, including
HCS message format and environment variables. **XRPL grant revocation** uses XLS-70 Credentials
(`activeGrantCredentialIssuer`), not NFToken burn.

---

## Revocation

MPCP defines two revocation channels. **XRPL-native deployments SHOULD use Credentials only**
and omit `revocationEndpoint`. Non-XRPL rails MAY use HTTP only.

### XRPL Credential grant revocation (recommended for XRPL)

When `activeGrantCredentialIssuer` is present, the PA (or a delegate controlling that XRPL
account) MUST issue an XLS-70 **CredentialCreate** for each active grant, and the grant
subject (agent / vehicle wallet) MUST **CredentialAccept** it on-ledger.

**Credential binding:**

| Field | Value |
|-------|-------|
| `Issuer` | `PolicyGrant.activeGrantCredentialIssuer` (PA XRPL address) |
| `Subject` | The grant subject's XRPL account — the same on-chain identity that signs or anchors spending for this grant (typically the address in `subjectId` when expressed as an XRPL `r`-address, or as defined by the deployment profile) |
| `CredentialType` | Hex-encoded UTF-8 string: `mpcp:active-grant:` concatenated with the literal `grantId` (same characters as in the PolicyGrant). Example: `hexEncode(UTF8("mpcp:active-grant:" + grantId))` |

**Revocation:** The PA submits **CredentialDelete** for that credential. After ledger finality,
the grant MUST be treated as revoked — no HTTP endpoint is consulted.

**Verifier behaviour (MUST when field is present):** Before accepting a payment or settlement,
online verifiers MUST query the XRPL ledger. If no matching non-expired credential exists for
(`Subject`, `Issuer`, `CredentialType`) → reject with `ACTIVE_GRANT_CREDENTIAL_MISSING`.

The Trust Gateway performs this check in [MPCP verification Step 1](./mpcp.md#step-1--verify-grant-and-budget-lineage).

**Advantages:** On-chain finality (~4s), no hosted revocation HTTP service, composable with other
XLS-70 tooling.

**Offline verifiers:** Cannot query the ledger; they remain subject to the usual offline
revocation limitations (TTL cache, bundle refresh, `expiresAt`).

### Legacy `revocationEndpoint` (HTTP, non-XRPL)

For rails or deployments that do not use XRPL Credentials, the optional `revocationEndpoint`
URL MAY be used. Verifiers and merchants MAY check whether the grant has been revoked before
accepting a payment.

**Endpoint contract:**

```
GET {revocationEndpoint}?grantId={grantId}
Response: { "revoked": boolean, "revokedAt": "ISO8601" }
```

**Verifier behaviour:** The core MPCP verifier pipeline treats this as a separate step (not part
of the synchronous settlement math). Callers MAY use `checkRevocation()` from the SDK.

**Merchant responsibility:** If only `revocationEndpoint` is present (no credential issuer),
merchants SHOULD call it when online. If the endpoint is unreachable, the merchant makes a
risk-based decision (see [Human-to-Agent Profile](../profiles/human-agent-profile.md)).

```javascript
import { checkRevocation } from "mpcp-service/sdk";

const { revoked, revokedAt, error } = await checkRevocation(
  grant.revocationEndpoint,
  grant.grantId,
  { timeoutMs: 3000 }
);
```

### Choosing a mechanism

**New XRPL grants** SHOULD set `activeGrantCredentialIssuer` and omit `revocationEndpoint` so
revocation is ledger-native. **Non-XRPL rails** MAY use `revocationEndpoint` only.

If both fields appear on one grant (e.g. during migration), verifiers that support Credentials
MUST apply the on-chain check when `activeGrantCredentialIssuer` is present; HTTP is optional
redundancy, not a substitute for a missing credential.

### Deprecated: XRPL NFToken burn

Revocation via **burning an NFToken** referenced in `anchorRef` (`xrpl:nft:{tokenId}`) is
**deprecated** and MUST NOT be specified for new grants. Use `activeGrantCredentialIssuer` and
CredentialDelete instead. See [Policy Anchoring](./policy-anchoring.md).

---

## Purpose Enforcement

### Overview

`allowedPurposes` defines the merchant categories a grant permits (e.g. `["transport:toll",
"transport:charging"]`). It is PA-signed and tamper-proof — a compromised agent cannot modify
the list.

Purpose enforcement operates at **two levels**:

| Level | Actor | Enforcement | Trust |
|-------|-------|-------------|-------|
| Agent-side | Agent / Vehicle Wallet | MUST check before issuing each SBA | Untrusted if agent is compromised |
| Gateway-side | Trust Gateway | SHOULD check before submitting settlement | Trusted — agent cannot bypass |

### Agent-Side Enforcement (MUST)

Before issuing an SBA, the agent MUST check whether the merchant category (purpose) is in the
`allowedPurposes` list. If not, the agent MUST refuse to issue an SBA — no payment proceeds.

```javascript
const purposeAllowed = grant.allowedPurposes?.includes(merchantCategory) ?? true;
if (!purposeAllowed) {
  // refuse to issue SBA — purpose not permitted by grant
}
```

### Gateway-Side Enforcement (SHOULD)

When the PolicyGrant contains `allowedPurposes`, the Trust Gateway SHOULD enforce purpose
compliance before submitting each settlement transaction.

The settlement request context (the request from the agent or proxy to the gateway) SHOULD
include a `purpose` field declaring the merchant category for the payment. When present, the
gateway checks:

```
if (policyGrant.allowedPurposes is present)
    and (settlementRequest.purpose is present):
  if settlementRequest.purpose ∉ policyGrant.allowedPurposes:
    → reject with PURPOSE_NOT_ALLOWED
```

If the settlement request does not include a `purpose` field and the grant has `allowedPurposes`,
the gateway MAY reject the request or MAY accept it (backward-compatible mode). Implementations
transitioning to gateway-side enforcement SHOULD log a warning when `purpose` is absent.

### Why Gateway Enforcement Is Needed

`allowedPurposes` was originally specified as agent-enforced only. This is insufficient because
a compromised agent (prompt injection, model manipulation, software vulnerability) can skip its
own purpose check, call `createSba()` for any merchant category, and the gateway — without
purpose enforcement — would sign and submit the payment.

The Trust Gateway is the trust boundary: it holds the settlement keys and the agent cannot
bypass it. The gateway already enforces budget ceiling, SBA validity, and `authorizedGateway`
from the PA-signed grant. Adding purpose enforcement closes the last policy bypass vector
available to a compromised agent.

### Trust Model After Purpose Enforcement

| Enforcement point | What it checks | Trusted? |
|---|---|---|
| Agent (first line) | Purpose, budget, revocation | No — can be bypassed if compromised |
| Trust Gateway | SBA validity, budget ceiling, gateway auth, **purpose** | Yes — holds keys, agent cannot bypass |
| Merchant | SBA + PolicyGrant signatures (offline), on-chain settlement (online) | Yes — independent party |

A compromised agent that skips purpose checking is still bounded by the gateway: the gateway
refuses to submit the payment if the declared purpose is not in the PA-signed `allowedPurposes`.
No XRPL transaction is made.

### Error Code

| Code | Meaning |
|------|---------|
| `PURPOSE_NOT_ALLOWED` | Settlement request `purpose` is not in `PolicyGrant.allowedPurposes` |

---

## Destination Enforcement

### Overview

A compromised agent could populate the SBA `destinationAllowlist` with an attacker-controlled
address, directing funds away from legitimate merchants. Because the SBA is agent-signed, the
agent controls this field.

MPCP addresses this with **two complementary mechanisms**, both PA-signed and tamper-proof:

1. **Static allowlist** — `destinationAllowlist` on the PolicyGrant
2. **On-chain credential registry** — `merchantCredentialIssuer` + `merchantCredentialType`
   fields referencing XRPL Credentials (XLS-70)

Either or both may be present. When both are present, a destination MUST satisfy **at least one**
mechanism.

### Mechanism 1: PA-Signed Static Allowlist

The `destinationAllowlist` field on the PolicyGrant is an array of permitted payment destination
addresses (e.g. XRPL `r`-addresses), signed by the PA.

**Agent responsibility:** When issuing an SBA, the agent MUST set
`SBA.destinationAllowlist ⊆ PolicyGrant.destinationAllowlist`. An SBA that includes a
destination not in the PA-signed list is invalid.

**Gateway enforcement (MUST):** Before submitting settlement, the Trust Gateway MUST verify:

```
if PolicyGrant.destinationAllowlist is present:
  payment.destination ∈ PolicyGrant.destinationAllowlist
  → reject with DESTINATION_NOT_ALLOWED on mismatch
```

**When to use:** Deployments where the set of approved merchants is known at grant issuance and
does not change during the grant's lifetime. Suitable for fleet deployments with a fixed set of
infrastructure providers.

### Mechanism 2: XRPL Credential Merchant Registry

For deployments where the set of approved merchants changes dynamically (merchants onboard or
offboard during a grant's lifetime), the PA can use XRPL Credentials (XLS-70) to maintain a
live, on-chain merchant registry.

**Setup:**

1. PA issues `CredentialCreate` to each approved merchant's XRPL account:
   - `Issuer` = PA's XRPL address
   - `Subject` = merchant's XRPL address
   - `CredentialType` = hex-encoded type string (e.g. `hex("mpcp:approved-merchant")`)
   - Optional `Expiration` for time-bounded approval
2. Merchant calls `CredentialAccept` to activate the credential on-ledger
3. PolicyGrant carries:
   - `merchantCredentialIssuer`: PA's XRPL address
   - `merchantCredentialType`: the hex-encoded credential type

**Gateway enforcement (MUST when fields are present):** Before submitting settlement, the Trust
Gateway MUST verify on-chain that the payment destination account holds a valid, non-expired
credential matching both `merchantCredentialIssuer` and `merchantCredentialType`:

```
if PolicyGrant.merchantCredentialIssuer is present:
  credential = lookupCredential(
    subject:  payment.destination,
    issuer:   PolicyGrant.merchantCredentialIssuer,
    type:     PolicyGrant.merchantCredentialType
  )
  if credential does not exist or is expired:
    → reject with DESTINATION_NOT_CREDENTIALED
```

**Advantages over static allowlist:**

- PA can add new merchants by issuing credentials without reissuing PolicyGrants
- PA can remove merchants by deleting credentials — takes effect immediately on-chain
- Merchant approval is publicly verifiable by any party
- No grant reissuance needed when the merchant set changes

**When to use:** Deployments where merchants are onboarded dynamically, multi-operator
ecosystems, or when the PA wants centralized on-chain control over merchant approval.

### Combining Both Mechanisms

When both `destinationAllowlist` and `merchantCredentialIssuer` are present on a PolicyGrant,
a destination is approved if it satisfies **either** mechanism:

```
approved = (destination ∈ PolicyGrant.destinationAllowlist)
        OR (destination holds matching credential on-chain)
```

This allows deployments to use the static list as a baseline and the credential registry for
dynamic additions.

### Error Codes

| Code | Meaning |
|------|---------|
| `DESTINATION_NOT_ALLOWED` | Payment destination not in `PolicyGrant.destinationAllowlist` and no credential match |
| `DESTINATION_NOT_CREDENTIALED` | `merchantCredentialIssuer` is set but destination does not hold a matching credential |

---

## Subject Attestation

### Overview

The `subjectId` field identifies the entity receiving the grant (vehicle, agent, wallet). By
default, `subjectId` is self-reported and informational only — it cannot be cryptographically
verified. This means a compromised agent sharing a signing key with other agents can issue SBAs
that appear to come from any agent in the fleet.

**Problem:** When multiple agents share the same SBA signing key, revoking a compromised
agent's grant affects all agents using that key. The fleet operator cannot isolate the
compromised agent without disrupting the entire fleet.

### Per-Agent Signing Keys (SHOULD)

Each agent or vehicle wallet SHOULD have a **unique SBA signing key**. This ensures:

- Revoking one agent's grant does not affect other agents
- SBAs can be attributed to a specific agent for audit purposes
- Compromised agents can be isolated without fleet-wide disruption

Fleet operators SHOULD register each agent's public key in the Trust Bundle or JWKS endpoint
under a unique `kid` that includes the agent identity (e.g. `"sba-key:vehicle-1284"`).

### XRPL Credential-Based Subject Attestation (SHOULD for XRPL deployments)

For XRPL deployments, the fleet operator or PA SHOULD issue an on-chain credential to each
agent's XRPL account using XLS-70 Credentials:

- `Issuer` = Fleet operator's or PA's XRPL address
- `Subject` = Agent's XRPL account
- `CredentialType` = hex-encoded type (e.g. `hex("mpcp:fleet-agent")` or
  `hex("mpcp:authorized-agent")`)

The PolicyGrant binds to the specific agent via:

- `subjectCredentialIssuer` — the XRPL address of the credential issuer
- `subjectCredentialType` — the hex-encoded credential type

**Canonical subject identifier (XRPL):** Deployments using credential-based attestation SHOULD
encode `subjectId` as `did:xrpl:{network}:{rAddress}` (classic address `r...` on the intended
ledger, with `{network}` disambiguating mainnet vs testnet or other deployments). This makes the
grant subject align with a verifiable on-chain identity. When `subjectId` uses another format,
implementations MUST still use a single unambiguous mapping from grant subject to the XRPL account
that holds the credential.

**Binding `actorId` to the credential Subject:** When `subjectCredentialIssuer` is present, the
SBA's `authorization.actorId` MUST equal the XRPL **classic address** of the on-chain credential
**Subject** (the account that holds the credential). This prevents a compromised agent that shares
no unique signing key from impersonating another fleet agent's `actorId` while presenting a
different XRPL settlement identity: the gateway correlates the attested account with the
self-reported actor field.

When `PolicyGrant.subjectId` uses the `did:xrpl:{network}:{rAddress}` form, `authorization.actorId`
MUST equal that `{rAddress}`; the gateway MUST reject with `SUBJECT_ACTOR_MISMATCH` if the grant
binds a DID subject and the SBA's `actorId` does not match the DID's address component.

**Gateway enforcement (SHOULD):** Before accepting SBAs from an agent, the gateway SHOULD
verify on-chain that the account `SBA.authorization.actorId` holds a valid, non-expired credential
matching the grant's `subjectCredentialIssuer` and `subjectCredentialType`:

```text
if PolicyGrant.subjectCredentialIssuer is present:
    if PolicyGrant.subjectId matches did:xrpl:*:{rAddress}:
        if SBA.authorization.actorId ≠ rAddress:
            → reject with SUBJECT_ACTOR_MISMATCH
    credential = lookupCredential(
        subject: SBA.authorization.actorId,
        issuer:  PolicyGrant.subjectCredentialIssuer,
        type:    PolicyGrant.subjectCredentialType
    )
    if credential does not exist or is expired:
        → reject with SUBJECT_NOT_ATTESTED
```

**Isolation on compromise:** When a single agent is compromised, the fleet operator:

1. Deletes the agent's on-chain credential via `CredentialDelete`
2. The gateway rejects further SBAs from that agent (credential check fails)
3. Other agents' credentials are unaffected — they continue operating normally
4. No grant reissuance needed for uncompromised agents

### Error codes

| Code | Meaning |
|------|---------|
| `SUBJECT_NOT_ATTESTED` | `subjectCredentialIssuer` is set but the credential Subject account does not hold a matching on-chain credential |
| `SUBJECT_ACTOR_MISMATCH` | `subjectCredentialIssuer` is set and either `SBA.authorization.actorId` does not equal the credential Subject account, or `subjectId` is `did:xrpl:…:{rAddress}` and `actorId` ≠ `{rAddress}` |

---

## Offline cumulative exposure

### Risk

Without a cumulative offline cap, an agent can present SBAs to many offline merchants in
sequence. Each merchant enforces only `offlineMaxSinglePayment` per transaction. The **total**
offline spend can therefore exceed `budgetMinor` until the gateway reconciles on-chain.

### Mitigation: `offlineMaxCumulativePayment`

When the PA includes `offlineMaxCumulativePayment`, offline verifiers that enforce this field
MUST maintain a running total of amounts already accepted for each `grantId` (in the grant's
offline minor units) and MUST reject a new SBA if accepting it would make the cumulative total
exceed `offlineMaxCumulativePayment`.

Currency for the cumulative cap is `offlineMaxCumulativePaymentCurrency`, or
`offlineMaxSinglePaymentCurrency` if the former is absent.

Operators SHOULD set `offlineMaxCumulativePayment` ≤ `budgetMinor` (or lower, to reflect risk
tolerance). Operators SHOULD size `offlineMaxSinglePayment` with the **expected number of
offline touchpoints** per grant in mind — a small per-tx cap with many merchants can still
produce large aggregate exposure if no cumulative field is used.

### Per-verifier scope

The cumulative total is tracked **per offline verifier** (per device). Distinct merchants do
not share state; a fleet-wide cumulative bound requires synchronized infrastructure outside
the scope of this specification. The PA SHOULD set `offlineMaxCumulativePayment` assuming
worst-case fan-out across independent verifiers when modeling exposure.

### Error code

| Code | Meaning |
|------|---------|
| `OFFLINE_CUMULATIVE_EXCEEDED` | Acceptance would exceed `PolicyGrant.offlineMaxCumulativePayment` |

---

## Summary

PolicyGrant establishes the **policy boundary** for machine payments.

It ensures that downstream SBA artifacts are always derived from a **validated policy evaluation**.

---

## See Also

- [MPCP Reference Flow — EV Charging](../architecture/fleet-ev-reference-flow.md) — Demonstrates how PolicyGrant is used during runtime authorization.
