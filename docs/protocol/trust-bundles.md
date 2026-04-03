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

MPCP artifacts (PolicyGrant, SignedBudgetAuthorization) are signed by different issuers. To verify these signatures, a verifier must obtain the corresponding public key.

In online environments, keys are resolved dynamically via the [HTTPS well-known endpoint](./key-resolution.md#https-well-known-endpoint) or [DID resolution](./key-resolution.md#did-resolution--example-didxrpl).

In offline or constrained environments — embedded devices, vehicle-mounted verifiers, IoT infrastructure with intermittent connectivity — verifiers MUST rely on pre-distributed trust material. Trust Bundles are the standardised mechanism for distributing that material.

---

## Scope

A Trust Bundle is scoped by **policy context**, which may include:

- **category** — the service domain the bundle applies to (e.g., `ev-charging`, `parking`, `tolls`)
- **merchant** — optional identity (DID or domain) of the payment-accepting entity this bundle is scoped to
- **geography** — optional region or country constraint
- **approved issuers** — the explicit set of issuer identities trusted within this scope

A verifier loads only the bundles relevant to its deployment. A verifier serving EV charging in Germany loads a bundle scoped to `ev-charging / EU / DE`; it does not need to load bundles for other categories or regions.

Embedded devices that belong to a specific merchant (e.g., an EV charging station managed by Ionity) SHOULD additionally filter by `merchant` to avoid loading key material from competing networks.

---

## Structure

A Trust Bundle MUST be a JSON document containing:

- An **issuer identity set** (`approvedIssuers`): the complete list of issuer DIDs authorised for this bundle's scope
- An **embedded key set** (`issuers`): the subset of approved issuers whose key material is pre-distributed in this bundle
- **Bundle metadata**: scope, expiry, optional issuance time (`issuedAt`), and the identity of the bundle signer
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
  "merchant": "did:web:ionity.eu",
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
          "x": "base64url...",
          "active": true
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
          "x": "base64url...",
          "active": true
        }
      ]
    }
  ],
  "issuedAt": "2026-05-25T00:00:00Z",
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

### `merchant`

Optional. The identity (DID or domain) of the payment-accepting entity this bundle is scoped to. Used by embedded devices (e.g. EV charging stations, parking meters) to filter bundles by the merchant network they belong to.

A device that serves a single merchant SHOULD only load bundles where `merchant` matches its own merchant identity. Bundles without a `merchant` field are unscoped and may be loaded by any verifier within the applicable `category` and `geography`.

Example values: `did:web:ionity.eu`, `pa.acme-parking.com`

### `geography`

Optional geographic constraints. Informational metadata used for bundle selection.

### `approvedIssuers`

The complete list of issuer identifiers trusted within this bundle's scope. An artifact whose `issuer` is not present in this list MUST be rejected, even if connectivity is available.

### `issuers`

Array of issuer entries with embedded key material. Each entry contains:

- `issuer` — the issuer identifier (MUST appear in `approvedIssuers`)
- `keys` — array of public keys in JWK format

Issuers present in `approvedIssuers` but absent from `issuers` have no embedded keys; verifiers resolve their keys dynamically if online, or reject the artifact if offline.

### `issuedAt`

Optional but **SHOULD** be present. ISO 8601 timestamp when the bundle was issued (before signing).
It is included in the signed payload. Verifiers MAY compare `issuedAt` to the device wall clock
as a sanity check — see [Clock sanity checks](#clock-sanity-checks-for-bundles).

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

All keys MUST include `kid` and `use: "sig"`. Private key material (`d`) MUST NOT be present. Keys MAY include `active: boolean` (default `true`). Verifiers MUST reject keys where `active` is `false`. See [Key Revocation](./key-resolution.md#key-revocation).

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
function resolveFromTrustBundle(issuer, issuerKeyId, loadedBundles):
    for each bundle in loadedBundles (sorted by expiresAt desc):
        if bundle is expired: continue
        if issuer not in bundle.approvedIssuers: continue
        entry = bundle.issuers.find(e => e.issuer == issuer)
        if entry is null: continue   # approved but not embedded — fall through
        jwk = entry.keys.find(k => k.kid == issuerKeyId)
        if jwk:
            if jwk.active == false: return REVOKED   # key revoked — reject
            return jwk
    return null   # not found in any bundle
```

If multiple non-expired bundles match the issuer, the verifier MUST use the one with the latest `expiresAt`. If a key is found with `active: false`, the verifier MUST reject the artifact with `KEY_REVOKED` (see [Key Revocation](./key-resolution.md#key-revocation)).

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

PolicyGrants carry `activeGrantCredentialIssuer` (XRPL) for on-chain revocation; historic artifacts may include a legacy `revocationEndpoint` (non-conforming)
(HTTP). Offline verifiers cannot query either. Deployments that use offline verification MUST
accept the risk that a revoked grant may be accepted — the grant remains valid until
`expiresAt` or the bundle is refreshed and revocation state is re-checked when online.

Embedded revocation lists (CRL, bloom filter) are a [planned future extension](#future-extensions). Until that mechanism is available, deployments with strict revocation requirements MUST use online verification.

### Offline SBA replay

**Risk:** An attacker or misconfigured agent could present the **same** SBA (same `budgetId`) to
multiple offline merchants, or repeatedly to one merchant that does not remember past
acceptances. Offline merchants do not share a global ledger of consumed SBAs.

**Mitigation (SHOULD):** Each offline verifier SHOULD maintain a local set (or bounded cache) of
recently seen `budgetId` values (or full SBA fingerprints) for the grants it accepts. If an
incoming SBA reuses an identifier already in the set, the verifier SHOULD reject it as a replay.

This is a **per-device** defense only — two physically separate merchants cannot detect duplicate
presentation of the same SBA without additional infrastructure. That trade-off is inherent to
offline operation. This specification does **not** add a `nonce` or `sequence` field to the SBA
for offline ordering; deployments that need stronger cross-merchant ordering MUST use online
verification or out-of-band coordination.

---

## Lifecycle

Trust Bundles MUST:

- carry a defined `expiresAt`
- be periodically refreshed when connectivity is available

Bundle issuers SHOULD include `issuedAt` so verifiers can enforce maximum validity windows and
clock sanity checks (see [Maximum bundle lifetime, stale bundles, and degraded mode](#maximum-bundle-lifetime-stale-bundles-and-degraded-mode)).

Implementations SHOULD:

- reject expired bundles at load time
- support loading multiple bundles simultaneously (for different scopes or overlapping key rotations)
- begin refreshing a bundle before it expires to avoid a verification gap

Bundle refresh is performed by fetching an updated Trust Bundle document from the bundle issuer's distribution endpoint (deployment-specific) and verifying its signature before replacing the stored bundle.

Verifiers MUST also support an **emergency refresh** mechanism for key compromise scenarios.
See [Bundle Signer Key Compromise](#bundle-signer-key-compromise) for the full procedure.

High-assurance deployments SHOULD set `expiresAt` to short intervals (hours, not days) to limit the window during which a revoked key remains trusted. See [Key Revocation](./key-resolution.md#key-revocation).

---

## Maximum bundle lifetime, stale bundles, and degraded mode

### Stale bundle risk

A merchant that continues to operate with an **outdated** Trust Bundle may trust issuer keys that
have been rotated, revoked, or compromised. The exposure window is bounded by `expiresAt`, but
long-lived bundles increase stale-key risk.

### Recommended maximum validity window

Deployments SHOULD cap the wall-clock span from bundle issuance to `expiresAt` according to risk:

| Deployment profile | Recommended max (`expiresAt` − `issuedAt`) |
|--------------------|-------------------------------------------|
| High-value / regulated (e.g. fleet EV, tolls) | **7 days** or less |
| Lower-assurance IoT or long-interval connectivity | **30 days** or less |

These are operational guidelines, not protocol hard limits. Operators MAY choose shorter windows
for stricter assurance.

### Behaviour when a bundle expires

When the current time is past `expiresAt`, the verifier MUST NOT use the bundle for new offline
verifications.

Implementations SHOULD enter **degraded mode** when the active bundle expires or is withdrawn:
for example, reject all new offline payment attempts, accept only reduced limits, or require
immediate operator intervention. The exact degraded behaviour is deployment-specific but MUST
be documented in the deployment's security policy.

### Refresh on reconnect

When connectivity returns, the verifier MUST attempt to fetch a fresh Trust Bundle before
resuming full offline service. For XRPL deployments, the verifier SHOULD also check the bundle
signer's on-chain key credential (see [Mitigation 3: On-Chain Freshness Signal](#mitigation-3-on-chain-freshness-signal-should-for-xrpl-deployments) under *Bundle Signer Key Compromise*). If the credential no longer exists, the verifier MUST discard the stale bundle and MUST NOT trust it until a new signed bundle is obtained.

---

## Clock sanity checks for bundles

Trust Bundle verification uses the verifier's wall clock for `expiresAt` and optional `issuedAt`
checks. See [Clock synchronization and drift](./verification.md#clock-synchronization-and-drift)
for general guidance.

When `issuedAt` is present, verifiers MAY reject a bundle if the local clock differs from
`issuedAt` by more than the deployment's **clock drift tolerance** (see Verification doc,
typically on the order of **5 minutes**). This detects gross clock skew or manipulation; it is
not a substitute for secure time on the device.

---

## Security Considerations

- Trust Bundles reduce the trust surface by scoping approved issuers to a specific category and geography
- Compromise of a bundle signer key allows an attacker to distribute bundles with injected issuer keys — short `expiresAt` windows limit the damage window. See [Bundle Signer Key Compromise](#bundle-signer-key-compromise) for detailed mitigations
- Root keys MUST be installed securely and MUST NOT be changeable by software update alone in high-assurance deployments
- Verifiers MUST NOT load unsigned or expired bundles
- Trust Bundles that were signed before an issuer key was revoked will continue to include the compromised key until they expire. Deployments SHOULD use short Trust Bundle lifetimes (hours, not days) in high-assurance environments. See [Key Revocation](./key-resolution.md#key-revocation) for guidance on limiting the exposure window
- Trust Bundle builders SHOULD check the JWKS `active` field and, for XRPL deployments, the on-chain key credential before embedding each key in a new bundle

---

## Bundle Signer Key Compromise

### Threat

The `bundleIssuer` (typically a PA, fleet operator, or consortium root) signs Trust Bundles
with a root key. If this key is compromised, an attacker can:

1. Create fraudulent Trust Bundles containing injected issuer keys
2. Distribute them to offline merchants (via the bundle refresh channel)
3. Merchants accept forged SBAs signed by the attacker's injected keys

Offline merchants have no way to distinguish a legitimate bundle from a forged one until the
bundle expires or they reconnect and receive a replacement.

### Exposure Window

The exposure is bounded by the bundle's `expiresAt`. A bundle with a 24-hour lifetime limits
the attacker to 24 hours of forged acceptance. A bundle with a 2-hour lifetime limits it to
2 hours.

### Mitigation 1: Short Bundle Lifetimes (SHOULD)

High-assurance deployments SHOULD set `expiresAt` to short intervals:

| Environment | Recommended max lifetime |
|-------------|-------------------------|
| High-assurance (fleet EV charging, tolls) | 2–6 hours |
| Standard (parking, general IoT) | 12–24 hours |
| Low-assurance (testing, development) | Up to 7 days |

Shorter lifetimes reduce the exposure window but increase the refresh frequency. Deployments
MUST balance security against the connectivity constraints of their merchant devices.

### Mitigation 2: Emergency Bundle Refresh (MUST support)

Verifiers that load Trust Bundles MUST support an emergency refresh mechanism. When a bundle
signer key is compromised, the operator issues a replacement bundle signed with a new key and
triggers an out-of-band refresh:

**Refresh procedure:**

1. Operator rotates the bundle signing key — new key is distributed to verifiers via the
   pre-configured root key set (firmware update, TLS-pinned fetch, or secure channel).
2. Operator issues a new Trust Bundle signed with the new key, with `expiresAt` set to a
   short window.
3. Operator triggers an emergency refresh signal to all verifiers. The signal mechanism is
   deployment-specific:
   - Push notification (MQTT, webhook, SMS)
   - Shortened polling interval (verifier checks every N minutes instead of hours)
   - Physical intervention (firmware flash for high-assurance devices)
4. Verifiers fetch the new bundle, verify its signature against the new root key, and replace
   the compromised bundle.

**Verifier behaviour during key rotation:**

- If the verifier has both an old bundle (signed by the compromised key) and a new bundle
  (signed by the rotated key), it MUST prefer the new bundle.
- If the verifier cannot fetch a new bundle and the old bundle has not yet expired, it MAY
  continue using the old bundle — accepting the residual risk — or it MAY switch to rejecting
  all offline artifacts until a valid bundle is loaded (fail-closed).
- Implementations SHOULD expose a configuration flag for fail-closed vs fail-open behaviour
  during bundle rotation.

### Mitigation 3: On-Chain Freshness Signal (SHOULD for XRPL deployments)

For XRPL deployments, the bundle signer SHOULD maintain an on-chain credential for its active
bundle signing key using XLS-70 Credentials:

- `Issuer` = Bundle signer's XRPL address
- `Subject` = Bundle signer's XRPL address (self-issued)
- `CredentialType` = hex-encoded `"mpcp:trust-bundle-signer:{bundleKeyId}"`

**On compromise:** The signer deletes the credential. Verifiers that reconnect and check the
ledger see that the credential no longer exists.

**Verifier behaviour on reconnect (SHOULD):**

When a verifier that has been operating offline regains connectivity, it SHOULD check the
on-chain credential for the bundle signer's key before continuing to trust the loaded bundle:

```text
function checkBundleFreshness(bundle):
    signerAddress = resolveXrplAddress(bundle.bundleIssuer)
    credentialType = hexEncode("mpcp:trust-bundle-signer:" + bundle.bundleKeyId)
    credential = lookupCredential(
        subject: signerAddress,
        issuer:  signerAddress,
        type:    credentialType
    )
    if credential does not exist or is expired:
        discard bundle — signer key may be compromised
        trigger emergency refresh
```

This provides a definitive, ledger-based signal that is independent of the bundle refresh
channel. Even if the attacker controls the bundle distribution endpoint, they cannot forge
an on-chain credential deletion.

### Mitigation 4: Embedded Revocation Lists (Future Extension)

Trust Bundles MAY include an optional `revokedGrantIds` field containing a list (or compact
bloom filter) of revoked `grantId` values. Offline verifiers that receive a bundle with this
field SHOULD check incoming SBAs against the list and reject any whose `grantId` matches.

```json
{
  "version": "1.0",
  "bundleId": "charging-eu-ionity-v2",
  "revokedGrantIds": ["grant_7ab3", "grant_9f2c"],
  ...
}
```

Alternatively, a **bloom filter** representation reduces bundle size for large revocation lists:

```json
{
  "revokedGrantFilter": {
    "type": "bloom",
    "bits": "base64url-encoded-bit-array",
    "hashCount": 3,
    "size": 1024
  }
}
```

This mechanism is not yet normative. Implementations that support it SHOULD treat it as a
best-effort check — false positives from the bloom filter SHOULD trigger an online revocation
check if connectivity is available, rather than an outright rejection.

### Defense-in-Depth Summary

| Layer | Mechanism | Effect |
|-------|-----------|--------|
| Containment | Short `expiresAt` | Limits exposure window to hours |
| Response | Emergency bundle refresh | Replaces compromised bundle across fleet |
| Detection | On-chain freshness signal | Verifiers detect key compromise on reconnect |
| Prevention | HSM for root keys | Signing key cannot be extracted |
| Future | Embedded revocation lists | Offline grant-level revocation |

---

## Future Extensions

Trust Bundles MAY be extended in future versions to support:

- **Embedded revocation lists** — CRL or bloom filter of revoked `grantId` values for offline revocation checking. See [Mitigation 4](#mitigation-4-embedded-revocation-lists-future-extension) for a preview of the proposed structure
- **DID document caching** — pre-resolved DID documents for approved issuers
- **Verifiable Credential chains** — VC-based bundle attestation for cross-domain trust
- **Merkle-compressed key sets** — compact representation for constrained devices

---

## See Also

- [Key Resolution](./key-resolution.md) — full key resolution algorithm including Trust Bundle lookup
- [Verification](./verification.md)
- [ArtifactBundle](./ArtifactBundle.md) — distinct concept: per-transaction artifact packaging
- [Transparent Gateway Profile](../profiles/gateway-profile.md)
- [Human-Agent Profile](../profiles/human-agent-profile.md)
