# Dispute Resolution

When a settlement is disputed, MPCP supports verification of the full authorization chain plus optional on-chain audit.

## Verification Flow

1. **PolicyGrant signature** — Verify the PA-signed grant (issuer key via Trust Bundle or HTTPS well-known)
2. **SBA signature** — Verify the machine-signed per-payment authorization
3. **XRPL on-chain evidence** — Sum all XRPL Payments with `mpcp/grant-id` memo matching the `grantId`; verify total ≤ `budgetMinor`
4. **Policy anchor** (optional) — If the PolicyGrant has an `anchorRef`, verify the policy hash matches the on-chain record

## Usage

### Verify Authorization Chain

```javascript
import { verifyPolicyGrant, verifySignedSessionBudgetAuthorization } from "mpcp-service/sdk";

// Verify PA-signed PolicyGrant
const grantValid = await verifyPolicyGrant(policyGrant);

// Verify machine-signed SBA against the grant
const sbaResult = await verifySignedSessionBudgetAuthorization(sba, {
  policyGrant,
});

if (grantValid && sbaResult.valid) {
  // Authorization chain is intact
}
```

### On-Chain Audit via mpcp/grant-id Memo

The Trust Gateway attaches an `mpcp/grant-id` memo to every XRPL Payment it submits. Auditors can independently sum all payments linked to a grant:

```
GET /account_tx (XRPL JSON-RPC)
→ filter by MemoType = hex("mpcp/grant-id"), MemoData = hex(grantId)
→ sum(Amount) ≤ policyGrant.budgetMinor   (escrow guarantee)
```

The on-chain escrow provides a hard upper bound — the sum can never exceed `budgetMinor` because that amount was pre-reserved at grant issuance.

### Verify Policy Anchor (Optional HCS)

If the PolicyGrant includes an `anchorRef` pointing to a Hedera HCS record:

```javascript
// Auditor retrieves full policy document from the PA/custodian
// Then verifies the hash matches the on-chain anchor:
// GET https://testnet.mirrornode.hedera.com/api/v1/topics/{topicId}/messages/{seq}
// Decode message, verify policyHash matches policyGrant.policyHash
```

See [Policy Anchoring](../protocol/policy-anchoring.md) for the full verification procedure.

## Evidence Bundle

For dispute resolution, collect the following bundle per disputed payment:

| Item | Source |
|------|--------|
| PolicyGrant | PA server or on-chain anchor |
| SBA | Machine wallet / merchant storage |
| XRPL transaction | Ledger (filtered by `mpcp/grant-id` memo) |
| Policy document (optional) | PA custodian — hash must match `policyGrant.policyHash` |
| Revocation / liveness | On-chain active-grant credential status at time of authorization (conforming grants) |

## Failure Reasons

| Reason | Meaning |
|--------|---------|
| `policy_grant_invalid` | PolicyGrant signature does not verify |
| `policy_grant_expired` | Grant was expired at time of payment |
| `sba_invalid` | SBA signature does not verify |
| `sba_grant_mismatch` | SBA `grantId` does not match PolicyGrant |
| `sba_amount_exceeded` | SBA `maxAmountMinor` exceeded the quoted amount |
| `destination_not_in_allowlist` | Payment destination not in SBA `destinationAllowlist` |
| `destination_not_allowed` | Payment destination not in PA-signed `PolicyGrant.destinationAllowlist` and no on-chain credential match |
| `destination_not_credentialed` | `merchantCredentialIssuer` set but destination lacks matching on-chain credential |
| `purpose_not_allowed` | Payment purpose not in `PolicyGrant.allowedPurposes` |
| `budget_exceeded` | Sum of on-chain payments > `budgetMinor` (Trust Gateway failure) |
| `grant_revoked` | Revocation endpoint returned `{ revoked: true }` |
| `active_grant_credential_missing` | On-chain active-grant credential absent or expired (`ACTIVE_GRANT_CREDENTIAL_MISSING`) |
| `offline_cumulative_exceeded` | Offline acceptance would exceed `PolicyGrant.offlineMaxCumulativePayment` |
| `offline_sba_replay` | Same SBA / `budgetId` was already accepted at this verifier (local deduplication) |

## See Also

- [Policy Anchoring](../protocol/policy-anchoring.md) — HCS anchoring; XRPL Credentials for revocation
- [Trust Model](../protocol/trust-model.md) — Escrow as proof-of-reservation; on-chain audit
- [Rails](../protocol/rails.md) — `mpcp/grant-id` memo format
- [ArtifactBundle](../protocol/ArtifactBundle.md) — Packaging artifacts for audit
