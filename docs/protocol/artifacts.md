# Protocol Artifacts

MPCP uses a chain of signed artifacts that progressively constrain payment parameters.

## Pipeline Overview

```
PolicyGrant
    ↓
SignedBudgetAuthorization (SBA)
    ↓
SignedPaymentAuthorization (SPA)
    ↓
Settlement
    ↓
Verification
```

Each artifact is a subset of the constraints defined by the previous one.

---

## PolicyGrant

The **PolicyGrant** is the result of policy evaluation at session entry. It defines the initial permission envelope:

- **allowedRails** — Which payment rails (xrpl, evm, stripe, hosted) are permitted
- **allowedAssets** — Which assets (IOU, ERC20, etc.) may be used
- **policyHash** — Hash of the policy snapshot
- **expiresAt** — Maximum validity for downstream artifacts

The PolicyGrant is signed by the policy authority; verifiers use `issuer` and `issuerKeyId` to resolve the policy authority public key. Downstream artifacts (SBA, SPA) must reference the same `policyHash` and remain within these constraints.

---

## SignedBudgetAuthorization (SBA)

The **SBA** defines a signed spending envelope for a session or scope:

- **maxAmountMinor** — Maximum spend in minor units (e.g., 3000 = $30.00)
- **allowedRails**, **allowedAssets** — Must be subsets of PolicyGrant
- **destinationAllowlist** — Optional list of permitted destination addresses
- **budgetScope** — SESSION, DAY, VEHICLE, or FLEET

The SBA is cryptographically signed. A verifier checks the signature over `SHA256("MPCP:SBA:1.0:" || canonicalJson(authorization))`.

---

## SignedPaymentAuthorization (SPA)

The **SPA** binds a specific settlement to the authorization chain:

- **decisionId** — Links to the policy decision
- **rail**, **asset**, **amount**, **destination** — Settlement parameters
- **intentHash** — Optional binding to canonical settlement intent for replay protection and dispute resolution

The SPA is signed over `SHA256("MPCP:SPA:1.0:" || canonicalJson(authorization))`. When present, `intentHash` ensures the executed settlement matches the authorized intent.

---

## Settlement Intent

The **SettlementIntent** describes what will be (or was) executed. It is hashed to produce `intentHash`:

```json
{
  "version": "1.0",
  "rail": "xrpl",
  "amount": "19440000",
  "destination": "rDest...",
  "asset": { "kind": "IOU", "currency": "RLUSD", "issuer": "rIssuer" }
}
```

The intentHash binds the SPA to this exact settlement, enabling deterministic verification and optional ledger anchoring.

---

## Verification Chain

A verifier checks:

1. **Schema** — All artifacts are valid
2. **Linkage** — PolicyGrant → SBA → SPA are consistent (sessionId, policyHash, constraints)
3. **Signatures** — PolicyGrant, SBA, and SPA signatures are valid
4. **Expiration** — No artifact is expired
5. **Settlement match** — Executed settlement matches SPA (and intentHash if present)

See [Verification](verification.md) for details.

---

## See Also

- [Hashing](hashing.md) — Canonical serialization and domain-separated hashing
- [Verification](verification.md) — Verification algorithm
- [Anchoring](anchoring.md) — Optional intent attestation
