# Verification

MPCP settlement verification ensures that an executed transaction matches the authorization chain.

## Verification Pipeline

The Trust Gateway verifier runs checks in order:

1. **Schema** — PolicyGrant and SBA parse and validate against expected structure
2. **Signatures** — PolicyGrant and SBA signatures are valid (resolve public keys via `issuer` + `issuerKeyId` using the [Key Resolution](./key-resolution.md) algorithm; in offline deployments, keys are resolved from a pre-loaded [Trust Bundle](./trust-bundles.md))
2a. **Fleet policy (optional)** — When the deployment requires **[FleetPolicyAuthorization](./FleetPolicyAuthorization.md) (FPA)**, verify FPA signature, expiration, and [§6 verification rules](./FleetPolicyAuthorization.md#6-verification-rules) (intersection with PolicyGrant; spending caps vs **`budgetMinor`**, not **`maxSpend`** alone). See [mpcp.md — Step 0a](./mpcp.md#step-0a--fleet-policy-authorization-optional).
3. **Linkage** — `SBA.authorization.grantId` references a valid PolicyGrant; constraint subsets are respected
4. **Conformance (MPCP v1)** — PolicyGrant satisfies [MPCP conformance](./PolicyGrant.md#mpcp-conformance-mandatory-xrpl): `allowedRails` is exactly `["xrpl"]`; `authorizedGateway` and `velocityLimit` present; `revocationEndpoint` absent.
5. **Policy** — Budget limits, rail/asset/destination constraints, expiration; `authorizedGateway` matches this gateway; when `gatewayCredentialIssuer` / `gatewayCredentialType` are set, verify gateway on-chain credential; enforce `velocityLimit`; when `subjectCredentialIssuer` is present, confirm `authorization.actorId` equals the XRPL classic address of the credential Subject (see [Subject Attestation](./PolicyGrant.md#subject-attestation)); durable `budgetMinor` spend state (see [Trust Model — Gateway durable spend state](./trust-model.md#gateway-durable-spend-state-must))
6. **Purpose** — When `PolicyGrant.allowedPurposes` is present and the settlement request includes a `purpose` field, verify `purpose ∈ allowedPurposes`. See [PolicyGrant — Purpose Enforcement](./PolicyGrant.md#purpose-enforcement).
7. **Destination** — When `PolicyGrant.destinationAllowlist` or `PolicyGrant.merchantCredentialIssuer` is present, verify the payment destination is approved. See [PolicyGrant — Destination Enforcement](./PolicyGrant.md#destination-enforcement).
8. **Grant liveness (XRPL Credential)** — When `PolicyGrant.activeGrantCredentialIssuer` is present, verify the active-grant XLS-70 Credential exists on the subject's XRPL account for this `grantId`. Reject with `ACTIVE_GRANT_CREDENTIAL_MISSING` if absent or expired. See [PolicyGrant — Revocation](./PolicyGrant.md#revocation).

If any check fails, verification fails with a specific reason. On success, the gateway submits the XRPL transaction and returns the `txHash` receipt.

## Verification contexts

### Full-chain (Trust Gateway or merchant holds PolicyGrant + SBA)

Use the **Verification Pipeline** above. Verifiers MUST validate the PolicyGrant PA signature and
that SBA fields are subsets of (or consistent with) the grant.

### SBA-only merchant context

When using [gateway-only PolicyGrant presentation](./PolicyGrant.md#merchant-privacy-and-grant-presentation-policygrant-exposure), the merchant receives **only the SBA** (which includes `grantId` and `policyHash`). Verifiers MUST:

- Verify the **SBA signature** using Trust Bundle or configured session-authority keys.
- Verify **`expiresAt`** and payment envelope fields (`maxAmountMinor`, `allowedRails`, `allowedAssets`, optional `destinationAllowlist` on the SBA).
- Treat **`policyHash`** as an opaque commitment; MAY compare it to a **published policy registry** if the deployment provides one.

Verifiers MUST **NOT** claim **PolicyGrant signature verification** or hidden **subset** checks
(`allowedPurposes`, PA-signed `destinationAllowlist` not mirrored on the SBA, `budgetMinor`,
`velocityLimit`, etc.) in this context — those are enforced by the **Trust Gateway** when the full
grant is presented at settlement.

## Clock synchronization and drift

Artifact validity (`expiresAt` on PolicyGrant, SBA, and Trust Bundle) is evaluated against the
verifier's notion of **current time**.

**Online verifiers (SHOULD):** Use an NTP-synchronized or otherwise trusted time source. The
Trust Gateway and Policy Authority servers SHOULD not rely solely on unsynchronized host clocks.

**Offline or embedded verifiers (SHOULD):** Use a hardware-backed real-time clock (RTC) where
available. Pure software clocks are easier to manipulate.

**Drift tolerance:** When comparing timestamps, implementations SHOULD allow a configurable
**clock drift tolerance**. A default tolerance of **±300 seconds (5 minutes)** is RECOMMENDED
unless a deployment's security policy specifies otherwise — i.e. treat an artifact as not yet
expired if `now + tolerance < expiresAt`, and as expired if `now − tolerance > expiresAt`
(using consistent comparison semantics for the deployment).

**Threat model:** A malicious actor with OS-level control can skew local time and make expired
artifacts appear valid or vice versa. MPCP assumes the verifier's execution environment is
within the deployment's trust boundary; mitigations are operational (secure boot, RTC, NTP,
monitoring), not additional protocol fields.

## What Is Verified

| Check | Description |
|-------|-------------|
| PolicyGrant schema | Parses and validates against expected structure |
| PolicyGrant signature | Signature valid; expiresAt not passed; constraints valid |
| SBA schema | Parses and validates against expected structure |
| SBA signature | Signature valid; expiresAt not passed; in full-chain mode, `authorization.grantId` references the presented PolicyGrant |
| SBA → budget | Current payment amount ≤ `maxAmountMinor`; rail (`["xrpl"]` only), asset, destination in allowlists. Trust Gateway also enforces durable cumulative spend vs `budgetMinor`, `velocityLimit`, and gateway binding. Session authority tracks SBA-scope cumulative totals. |
| Purpose | When `PolicyGrant.allowedPurposes` is present and settlement request includes `purpose`: verify `purpose ∈ allowedPurposes`. Reject with `PURPOSE_NOT_ALLOWED` on mismatch. |
| Destination | When `PolicyGrant.destinationAllowlist` is present: verify `payment.destination ∈ destinationAllowlist`. When `PolicyGrant.merchantCredentialIssuer` is present: verify destination holds a matching on-chain credential. If both are set, either match suffices. Reject with `DESTINATION_NOT_ALLOWED` or `DESTINATION_NOT_CREDENTIALED`. |
| Grant liveness | When `PolicyGrant.activeGrantCredentialIssuer` is present: verify on-chain active-grant credential for this `grantId`. Reject with `ACTIVE_GRANT_CREDENTIAL_MISSING` if revoked. |

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
