# Trust Bundles

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

## Overview

A **Trust Bundle** is a signed, distributable document that packages trusted issuer public keys and scope metadata for use by MPCP verifiers that cannot perform live key resolution at runtime.

Trust Bundles enable:

- **Offline verification** — artifacts can be verified without network access
- **Deterministic key resolution** — keys are pre-distributed rather than fetched at verify time
- **Scoped trust domains** — each bundle is bounded to a specific category and geography, minimising the blast radius of a compromised issuer

Trust Bundles are **optional** in MPCP, but **REQUIRED** for deployment profiles that operate without network access at verification time.

Trust Bundles are distinct from [ArtifactBundles](./ArtifactBundle.md). An ArtifactBundle packages the payment verification artifacts of a single transaction for audit and dispute use. A Trust Bundle packages the public keys of trusted issuers for verifier configuration — it is an operational input, not a per-transaction artifact.

---

## Purpose

MPCP artifacts (PolicyGrant, SignedBudgetAuthorization, SignedPaymentAuthorization) are signed by different issuers. To verify these signatures, a verifier must obtain the corresponding public key.

In online environments, keys are resolved dynamically via the [HTTPS well-known endpoint](./key-resolution.md#https-well-known-endpoint) or [DID resolution](./key-resolution.md#did-resolution--example-didxrpl).

In offline or constrained environments — embedded devices, vehicle-mounted verifiers, IoT infrastructure with intermittent connectivity — verifiers MUST rely on pre-distributed trust material. Trust Bundles are the standardised mechanism for distributing that material.

---

## Scope

A Trust Bundle is scoped by **policy context**, which may include:

- **category** — the service domain the bundle applies to (e.g., `ev-charging`, `parking`, `tolls`)
- **geography** — optional region or country constraint
- **approved issuers** — the explicit set of issuer identities trusted within this scope

A verifier loads only the bundles relevant to its deployment. A verifier serving EV charging in Germany loads a bundle scoped to `ev-charging / EU / DE`; it does not need to load bundles for other categories or regions.

---

## Structure

A Trust Bundle MUST be a JSON document containing:

- An **issuer identity set** (`approvedIssuers`): the complete list of issuer DIDs authorised for this bundle's scope
- An **embedded key set** (`issuers`): the subset of approved issuers whose key material is pre-distributed in this bundle
- **Bundle metadata**: scope, expiry, and the identity of the bundle signer
- A **signature** over the canonical bundle payload

An issuer that appears in `approvedIssuers` but not in `issuers` is recognised as trusted but its keys are not embedded — verifiers MUST resolve its keys via DID or well-known if connectivity is available, or reject the artifact if offline.

### Example

```json
{
  "version": "1.0",
  "bundleId": "charging-eu-ionity-v1",
  "bundleIssuer": "did:web:consortium.example.com",
  "bundleKeyId": "root-key-1",
  "category": "ev-charging",
  "geography": {
    "region": "EU",
    "countryCodes": ["DE", "NL", "FR"]
  },
  "approvedIssuers": [
    "did:web:ionity.eu",
    "did:web:fleet.example.com"
  ],
  "issuers": [
    {
      "issuer": "did:web:fleet.example.com",
      "keys": [
        {
          "kid": "budget-key-1",
          "use": "sig",
          "kty": "OKP",
          "crv": "Ed25519",
          "x": "base64url..."
        }
      ]
    },
    {
      "issuer": "did:web:ionity.eu",
      "keys": [
        {
          "kid": "policy-key-1",
          "use": "sig",
          "kty": "OKP",
          "crv": "Ed25519",
          "x": "base64url..."
        }
      ]
    }
  ],
  "expiresAt": "2026-06-01T00:00:00Z",
  "signature": "base64url..."
}
```

---

## Fields

### `version`

Semantic version of the Trust Bundle format. MUST be `"1.0"` for this version of the spec.

### `bundleId`

Unique identifier for this bundle. SHOULD be human-readable and include the scope and version.

### `bundleIssuer`

Identifier (domain or DID) of the authority that signed this bundle — e.g., a policy authority, fleet operator, or consortium root. Verifiers use this to look up the bundle signer's key from their pre-configured root key set.

### `bundleKeyId`

The `kid` of the key used to sign this bundle, within the `bundleIssuer`'s key set.

### `category`

The service category this bundle applies to. Informational metadata used for bundle selection.

### `geography`

Optional geographic constraints. Informational metadata used for bundle selection.

### `approvedIssuers`

The complete list of issuer identifiers trusted within this bundle's scope. An artifact whose `issuer` is not present in this list MUST be rejected, even if connectivity is available.

### `issuers`

Array of issuer entries with embedded key material. Each entry contains:

- `issuer` — the issuer identifier (MUST appear in `approvedIssuers`)
- `keys` — array of public keys in JWK format

Issuers present in `approvedIssuers` but absent from `issuers` have no embedded keys; verifiers resolve their keys dynamically if online, or reject the artifact if offline.

### `expiresAt`

ISO 8601 expiration timestamp. Verifiers MUST reject a bundle that has expired.

### `signature`

Signature over the canonical bundle payload by the `bundleIssuer`. See [Signing](#signing) for the exact construction.

---

## Key Format

Public keys MUST be expressed as **JSON Web Keys (JWK)** (RFC 7517).

MPCP implementations MUST support:

| Algorithm | `kty` | `crv` | Notes |
|-----------|-------|-------|-------|
| Ed25519 | `OKP` | `Ed25519` | Recommended |
| ECDSA P-256 | `EC` | `P-256` | Required for compatibility with SBA signing in the reference implementation |
| secp256k1 | `EC` | `secp256k1` | Required for XRPL-based deployments |

All keys MUST include `kid` and `use: "sig"`. Private key material (`d`) MUST NOT be present.

---

## Signing

### Canonical Payload

The signed payload is constructed by:

1. Removing the `signature` field from the bundle document
2. Applying canonical JSON serialisation (see [Hashing](./hashing.md))
3. Prepending the MPCP domain prefix

```
signedBytes = "MPCP:TrustBundle:1.0:" || canonicalJson(bundleWithoutSignature)
```

### Algorithm

The signature MUST use the algorithm implied by the `bundleIssuer`'s key type:

| Key type | Signature algorithm |
|----------|---------------------|
| `OKP / Ed25519` | EdDSA |
| `EC / P-256` | ECDSA with SHA-256 |
| `EC / secp256k1` | ECDSA with SHA-256 |

The `signature` field contains the resulting signature encoded as base64url.

### Trust Model

Verifiers MUST:

1. Obtain the `bundleIssuer`'s public key (identified by `bundleKeyId`) from pre-configured root keys
2. Verify the bundle signature against the canonical payload
3. Reject the bundle if the signature is invalid or the bundle has expired
4. Use embedded keys in `issuers` to verify artifact signatures

**Root key bootstrap:** The public key(s) of bundle signers cannot themselves be distributed in a Trust Bundle — doing so would be circular. Root keys are distributed out-of-band:

- Installed at device manufacture or provisioning time as a firmware constant
- Fetched once over TLS during initial setup and then pinned
- Distributed by the fleet operator or consortium through a separate secure channel

---

## Key Lookup

When resolving an artifact's issuer key, verifiers check loaded bundles before attempting live resolution:

```text
function resolveFromBundle(issuer, issuerKeyId, loadedBundles):
    for each bundle in loadedBundles (sorted by expiresAt desc):
        if bundle is expired: continue
        if issuer not in bundle.approvedIssuers: continue
        entry = bundle.issuers.find(e => e.issuer == issuer)
        if entry is null: continue   # approved but not embedded — fall through
        jwk = entry.keys.find(k => k.kid == issuerKeyId)
        if jwk: return jwk
    return null   # not found in any bundle
```

If multiple non-expired bundles match the issuer, the verifier MUST use the one with the latest `expiresAt`.

This function feeds into the broader [Key Resolution](./key-resolution.md) algorithm as the first step, before HTTPS well-known and DID resolution.

---

## Offline Verification

In offline environments:

- Verifiers MUST rely on loaded Trust Bundles for key resolution
- No network calls (HTTPS well-known, DID resolution) are performed
- Verifiers MUST reject artifacts whose issuer is not covered by any loaded bundle

Verification flow:

```text
artifact → issuer → lookup key in bundle → verify signature → check expiry and constraints
```

### Revocation in Offline Mode

PolicyGrants and SPAs may carry a `revocationEndpoint`. Offline verifiers cannot call this endpoint. Deployments that use offline verification MUST accept the risk that a revoked grant may be accepted — the revoked grant will remain valid until its `expiresAt` expires or the bundle is refreshed and revocation state is checked.

Embedded revocation lists (CRL, bloom filter) are a [planned future extension](#future-extensions). Until that mechanism is available, deployments with strict revocation requirements MUST use online verification.

---

## Lifecycle

Trust Bundles MUST:

- carry a defined `expiresAt`
- be periodically refreshed when connectivity is available

Implementations SHOULD:

- reject expired bundles at load time
- support loading multiple bundles simultaneously (for different scopes or overlapping key rotations)
- begin refreshing a bundle before it expires to avoid a verification gap

Bundle refresh is performed by fetching an updated Trust Bundle document from the bundle issuer's distribution endpoint (deployment-specific) and verifying its signature before replacing the stored bundle.

---

## Security Considerations

- Trust Bundles reduce the trust surface by scoping approved issuers to a specific category and geography
- Compromise of a bundle signer key allows an attacker to distribute bundles with injected issuer keys — short `expiresAt` windows limit the damage window
- Root keys MUST be installed securely and MUST NOT be changeable by software update alone in high-assurance deployments
- Verifiers MUST NOT load unsigned or expired bundles

---

## Future Extensions

Trust Bundles MAY be extended in future versions to support:

- **Embedded revocation lists** — CRL or bloom filter of revoked `grantId` values for offline revocation checking
- **DID document caching** — pre-resolved DID documents for approved issuers
- **Verifiable Credential chains** — VC-based bundle attestation for cross-domain trust
- **Merkle-compressed key sets** — compact representation for constrained devices

---

## See Also

- [Key Resolution](./key-resolution.md) — full key resolution algorithm including Trust Bundle lookup
- [Verification](./verification.md)
- [ArtifactBundle](./ArtifactBundle.md) — distinct concept: per-transaction artifact packaging
- [Lite Profile](../profiles/lite-profile.md)
- [Full Profile](../profiles/full-profile.md)
