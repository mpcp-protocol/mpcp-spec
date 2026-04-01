# Protocol Artifacts

MPCP uses a chain of signed artifacts that progressively constrain payment parameters.

## Pipeline Overview

```
PolicyGrant
    ↓
SignedBudgetAuthorization (SBA)
    ↓
Trust Gateway (verifies + submits settlement)
    ↓
XRPL Receipt (txHash)
```

Each artifact is a subset of the constraints defined by the previous one.

---

## PolicyGrant

The **PolicyGrant** is the result of policy evaluation at session entry. It defines the initial permission envelope:

- **allowedRails** — Which payment rails (xrpl, evm, stripe, hosted) are permitted
- **allowedAssets** — Which assets may be used (array of `Asset` objects with `kind`, and kind-specific fields)
- **policyHash** — Hash of the policy snapshot
- **expiresAt** — Maximum validity for downstream artifacts

The PolicyGrant is signed by the policy authority; verifiers use `issuer` and `issuerKeyId` to resolve the policy authority public key. Downstream artifacts (SBA) must reference this PolicyGrant via `SBA.authorization.grantId` and remain within its constraints.

---

## SignedBudgetAuthorization (SBA)

The **SBA** defines a signed spending envelope for a session or scope:

- **maxAmountMinor** — Maximum spend in the on-chain asset's atomic units (same denomination as `SPA.amount`). The session authority converts the fiat budget to on-chain units at SBA issuance time.
- **allowedRails**, **allowedAssets** — Must be subsets of PolicyGrant
- **destinationAllowlist** — Optional list of permitted destination addresses
- **budgetScope** — SESSION, DAY, VEHICLE, FLEET, or TRIP (multi-session; see [Human-to-Agent Profile](../profiles/human-agent-profile.md#trip-scope-semantics))

The SBA is cryptographically signed. A verifier checks the signature over `SHA256("MPCP:SBA:1.0:" || canonicalJson(authorization))`.

---

## Verification Chain

The Trust Gateway verifier checks:

1. **Schema** — PolicyGrant and SBA are valid
2. **Linkage** — `SBA.authorization.grantId` references a valid PolicyGrant; constraint subsets are respected
3. **Signatures** — PolicyGrant and SBA signatures are valid
4. **Expiration** — No artifact is expired
5. **Budget** — Payment amount ≤ `SBA.maxAmountMinor`

On success, the gateway submits the XRPL transaction and returns the `txHash` as a receipt.

See [Verification](verification.md) for details.

---

## See Also

- [Hashing](hashing.md) — Canonical serialization and domain-separated hashing
- [Verification](verification.md) — Verification algorithm
