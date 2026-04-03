# Key Resolution

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

## Overview

MPCP artifacts carry two fields that identify the signing authority:

- `issuer` — identifies the authority (domain, HTTPS URL, or DID)
- `issuerKeyId` — selects the specific key within that authority's key set

Verifiers use these two fields to retrieve the public key required to validate the artifact signature.

MPCP defines **HTTPS well-known** as the baseline key resolution mechanism. All conforming implementations MUST support it. DID ([W3C DID Core](https://www.w3.org/TR/did-core/)) resolution and Verifiable Credentials ([W3C VC Data Model](https://www.w3.org/TR/vc-data-model/)) are optional higher-level mechanisms that deployments MAY use in addition.

---

## Canonical Key Format: JWK

MPCP uses **JSON Web Key (JWK)** format (RFC 7517) as the canonical representation for public keys.

All key set documents MUST express public keys as JWK objects. Verifiers MUST accept keys in JWK format.

### Ed25519 (recommended)

```json
{
  "kid": "policy-auth-key-1",
  "use": "sig",
  "kty": "OKP",
  "crv": "Ed25519",
  "x": "base64url-encoded-32-byte-public-key",
  "active": true
}
```

### secp256k1

```json
{
  "kid": "payment-auth-key-1",
  "use": "sig",
  "kty": "EC",
  "crv": "secp256k1",
  "x": "base64url-encoded-x-coordinate",
  "y": "base64url-encoded-y-coordinate",
  "active": true
}
```

Required JWK fields for MPCP keys:

| Field | Description |
|-------|-------------|
| `kid` | Key identifier. MUST match `issuerKeyId` in the artifact. |
| `use` | MUST be `"sig"`. |
| `kty` | Key type. `"OKP"` for Ed25519; `"EC"` for secp256k1. |
| `crv` | Curve. `"Ed25519"` or `"secp256k1"`. |
| `x`   | Public key material (base64url-encoded). |
| `y`   | y-coordinate for EC keys (base64url-encoded). |
| `active` | Optional boolean (default `true`). When `false`, the key is revoked. Verifiers MUST reject signatures made with a key whose `active` field is `false`. See [Key Revocation](#key-revocation). |

Private key material (`d`) MUST NOT be present in key set documents.

---

## HTTPS Well-Known Endpoint

### Endpoint

```
GET https://{issuer-domain}/.well-known/mpcp-keys.json
```

The endpoint MUST be served over HTTPS. Verifiers MUST validate the TLS certificate. Plaintext HTTP MUST NOT be used.

### Deriving the URL from `issuer`

| `issuer` format | Derived URL |
|-----------------|-------------|
| Bare domain: `operator.example.com` | `https://operator.example.com/.well-known/mpcp-keys.json` |
| HTTPS URL: `https://operator.example.com` | `https://operator.example.com/.well-known/mpcp-keys.json` |
| `did:web:operator.example.com` | `https://operator.example.com/.well-known/mpcp-keys.json` |
| `did:web:operator.example.com:path:to:key` | `https://operator.example.com/path/to/key/.well-known/mpcp-keys.json` |

### Key Set Document Format

```json
{
  "version": "1.0",
  "keys": [
    {
      "kid": "policy-auth-key-1",
      "use": "sig",
      "kty": "OKP",
      "crv": "Ed25519",
      "x": "base64url...",
      "active": true
    },
    {
      "kid": "policy-auth-key-2",
      "use": "sig",
      "kty": "EC",
      "crv": "secp256k1",
      "x": "base64url...",
      "y": "base64url...",
      "active": false
    }
  ]
}
```

The document is a plain JSON object. The `keys` array contains one or more JWK entries. An authority MAY publish multiple keys to support key rotation. Keys with `active: false` are retained in the document for audit traceability but MUST NOT be used for signature verification. See [Key Revocation](#key-revocation).

### HTTP Response Requirements

| Requirement | Value |
|-------------|-------|
| Content-Type | `application/json` |
| Status | `200 OK` for valid responses |
| Encoding | UTF-8 |

Verifiers SHOULD cache key set responses according to standard HTTP cache semantics (`Cache-Control`, `ETag`). Verifiers MUST revalidate cached responses before use when they have expired.

---

## Resolution Algorithm

Verifiers MUST attempt resolution in the following priority order:

```text
function resolvePublicKey(issuer, issuerKeyId):
    # 1. Trust Bundle lookup (offline / pre-distributed)
    jwk = resolveFromTrustBundle(issuer, issuerKeyId)
    if jwk:
        if jwk.active == false: raise KEY_REVOKED
        return jwk

    # 2. HTTPS well-known (online)
    url = deriveKeySetUrl(issuer)
    keySetDoc = httpGet(url)               # HTTPS required; TLS validated
    keys = parseKeySet(keySetDoc)
    jwk = keys.find(k => k.kid == issuerKeyId)
    if jwk:
        if jwk.active == false: raise KEY_REVOKED
        return jwk

    # 3. XRPL Credential check (optional, online — see Key Revocation)
    if xrplKeyCredentialCheckEnabled(issuer):
        if not verifyKeyCredential(issuer, issuerKeyId): raise KEY_REVOKED

    # 4. DID resolution (optional, online)
    if issuer starts with "did:" and not "did:web:":
        jwk = resolveDid(issuer, issuerKeyId)   # method-specific; see DID section below
        if jwk: return jwk

    raise KEY_NOT_FOUND
```

If no resolution path succeeds, the verifier MUST fail the signature check and reject the artifact. If a key is found but marked as revoked (`active: false`) or lacks a valid on-chain credential, the verifier MUST reject with `KEY_REVOKED`.

---

## Trust Bundle Resolution

[Trust Bundles](./trust-bundles.md) are the primary resolution mechanism for deployments that operate without network access at verification time.

A Trust Bundle is a signed, distributable document containing the public keys of approved issuers for a given scope. Verifiers load one or more Trust Bundles at startup (or after periodic refresh) and consult them before attempting any live network call.

```text
function resolveFromTrustBundle(issuer, issuerKeyId):
    for each bundle in loadedBundles (sorted by expiresAt desc):
        if bundle is expired: continue
        if issuer not in bundle.approvedIssuers: continue
        entry = bundle.issuers.find(e => e.issuer == issuer)
        if entry is null: continue   # approved but no embedded keys — fall through
        jwk = entry.keys.find(k => k.kid == issuerKeyId)
        if jwk: return jwk
    return null
```

Trust Bundles are optional. If no Trust Bundle is loaded, resolution proceeds directly to the HTTPS well-known step.

See [Trust Bundles](./trust-bundles.md) for the full specification including signing, lifecycle, and offline revocation considerations.

---

## Pre-Configured Keys

Individual keys MAY be pre-configured directly on a verifier, identified by `issuer` + `issuerKeyId` and expressed as JWK objects. When a matching entry is found, the verifier uses it without fetching the well-known endpoint.

Trust Bundles are the recommended mechanism for distributing pre-configured keys at scale. Direct pre-configuration is appropriate for single-key pinning or testing environments.

This supports:

- offline and air-gapped machine wallets
- embedded deployments where network access is unavailable
- pinned deployments where key mutation must be prevented

Pre-configured keys MUST still be expressed in JWK format.

---

## DID and Verifiable Credentials (Optional)

Deployments MAY use [decentralized identifiers (DIDs)](https://www.w3.org/TR/did-core/) or [Verifiable Credentials (VCs)](https://www.w3.org/TR/vc-data-model/) as a higher-level key binding mechanism.

When the `issuer` field carries a `did:` URI other than `did:web:`, verifiers MAY use DID resolution to retrieve the key material. Resolved key material MUST still be expressed and validated as JWK.

VC-based key discovery is outside the core protocol.

DID resolution and VC verification are never required for MPCP compliance. Implementations that support only HTTPS well-known key resolution are fully conformant.

---

## DID Resolution — Example: `did:xrpl`

The following shows how a W3C DID can be resolved to obtain signing keys. The `did:xrpl` method
is used as a concrete example; other DID methods (e.g. `did:hedera`, `did:key`, `did:web`)
follow the same general pattern with method-specific resolution logic as defined by the
[W3C DID Core](https://www.w3.org/TR/did-core/) specification.

### DID Format

```
did:xrpl:{network}:{rAddress}
```

Examples:
- `did:xrpl:mainnet:rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh`
- `did:xrpl:testnet:rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe`

### Network RPC Defaults

| Network | Default RPC Endpoint |
|---------|---------------------|
| `mainnet` | `https://xrplcluster.com` |
| `testnet` | `https://s.altnet.rippletest.net:51234` |

### Resolution Algorithm

1. Parse network and account from DID string
2. Call XRPL `account_objects` JSON-RPC with `type: "DID"` to retrieve the DID object
3. Hex-decode the `DIDDocument` field of the returned DID ledger entry
4. Parse the decoded string as JSON to obtain the DID Document
5. Extract `verificationMethod[0].publicKeyJwk`
6. Return the JWK

```text
function resolveXrplDid(did):
    (network, account) = parseDid(did)
    rpcUrl = networkRpc(network)
    response = xrplRpc(rpcUrl, "account_objects", { account, type: "DID" })
    didObject = response.result.account_objects[0]
    didDocumentJson = hexDecode(didObject.DIDDocument)
    didDocument = JSON.parse(didDocumentJson)
    return didDocument.verificationMethod[0].publicKeyJwk
```

### Reference Implementation

```typescript
import { resolveXrplDid } from "mpcp-service/sdk";

const result = await resolveXrplDid(
  "did:xrpl:mainnet:rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
  { rpcUrl: "https://xrplcluster.com", timeoutMs: 5000 },
);

if ("error" in result) {
  // resolution failed
} else {
  const jwk = result.jwk; // JsonWebKey
}
```

### Error Codes

| Code | Condition |
|------|-----------|
| `invalid_did_format` | DID does not match `did:xrpl:{network}:{rAddress}` |
| `unknown_xrpl_network` | Network is not `mainnet` or `testnet` and no `rpcUrl` provided |
| `xrpl_rpc_fetch_failed` | Network error calling the XRPL JSON-RPC endpoint |
| `xrpl_rpc_http_error` | Non-200 HTTP response from the RPC endpoint |
| `xrpl_did_not_found` | No DID object found for the account |
| `xrpl_did_document_missing` | DIDDocument field absent or empty |
| `xrpl_did_document_invalid_hex` | DIDDocument field is not valid hex |
| `xrpl_did_document_invalid_json` | Decoded DIDDocument is not valid JSON |
| `xrpl_did_no_verification_method` | DID Document has no verificationMethod entries |
| `xrpl_did_no_public_key_jwk` | verificationMethod[0] has no publicKeyJwk |

---

## Error Codes

| Code | Condition |
|------|-----------|
| `KEY_NOT_FOUND` | `issuerKeyId` not present in the resolved key set |
| `KEY_REVOKED` | Key found but `active` is `false`, or XRPL key credential does not exist or is expired |
| `KEY_SET_FETCH_FAILED` | Well-known endpoint unreachable or returned non-200 |
| `KEY_SET_INVALID` | Key set document could not be parsed |
| `KEY_FORMAT_INVALID` | Key entry is not a valid JWK |

---

## Key Revocation

### Overview

If a PA signing key is compromised, an attacker can forge PolicyGrants with unlimited budgets.
MPCP provides two complementary revocation mechanisms — one off-chain (JWKS `active` field) and
one on-chain (XRPL Credentials) — to ensure that revoked keys are rejected as quickly as
possible.

### Mechanism 1: JWKS `active` Field

Every JWK entry in a key set document MAY include an `active` field (boolean, default `true`).
When a PA rotates or revokes a key, it sets `active: false` for that key in the JWKS endpoint
response.

**Verifier behaviour (MUST):**

1. After resolving a key via HTTPS well-known or Trust Bundle, check the `active` field.
2. If `active` is explicitly `false`, reject the artifact with `KEY_REVOKED`.
3. If `active` is absent or `true`, proceed with verification.

**PA behaviour on compromise:**

1. Set `active: false` on the compromised key in the JWKS endpoint immediately.
2. Issue new Trust Bundles that either omit the compromised key or include it with
   `active: false`.
3. Rotate to a new key (`kid`) for all subsequent grant signing.

**Limitations:** Verifiers that cache the key set document will continue to trust the
compromised key until the cache expires. Implementations SHOULD use short `Cache-Control`
`max-age` values (minutes, not hours) for the JWKS endpoint. Trust Bundles that embedded the
key before revocation remain valid until their `expiresAt` — deployments SHOULD use short
Trust Bundle lifetimes (hours, not days) for high-assurance environments.

### Mechanism 2: XRPL Credential Key Lifecycle

For deployments on XRPL, the PA can maintain an on-chain credential for each active signing
key using XLS-70 Credentials. This provides a definitive, ledger-based revocation signal that
does not depend on JWKS cache expiry.

**Setup:**

1. For each active signing key, the PA issues a `CredentialCreate` transaction to its own
   XRPL account:
   - `Issuer` = PA's XRPL address
   - `Subject` = PA's XRPL address (self-issued)
   - `CredentialType` = hex-encoded string `"mpcp:pa-signing-key:{kid}"`
     (e.g. `hex("mpcp:pa-signing-key:policy-auth-key-1")`)
   - Optional `Expiration` aligned with the key's intended lifetime
2. PA calls `CredentialAccept` to activate the credential on-ledger.

**Revocation on compromise:**

1. PA submits `CredentialDelete` for the compromised key's credential.
2. The credential is removed from the ledger immediately.
3. Any verifier or Trust Bundle builder that checks the ledger will see that the credential
   no longer exists.

**Verifier behaviour (SHOULD for XRPL deployments):**

After resolving a key via JWKS or Trust Bundle, and before accepting the key for verification,
the verifier SHOULD check on-chain that the PA holds a valid, non-expired credential for the
key:

```text
function verifyKeyCredential(issuer, issuerKeyId):
    paXrplAddress = resolveXrplAddress(issuer)
    credentialType = hexEncode("mpcp:pa-signing-key:" + issuerKeyId)
    credential = lookupCredential(
        subject: paXrplAddress,
        issuer:  paXrplAddress,
        type:    credentialType
    )
    return credential exists and is not expired
```

If the credential does not exist or is expired, the verifier MUST reject the artifact with
`KEY_REVOKED`.

**Trust Bundle builder behaviour (SHOULD):**

When building or refreshing a Trust Bundle, the builder SHOULD check each included key's
on-chain credential before embedding it. Keys whose credentials have been deleted MUST NOT
be included in new Trust Bundles.

### Combining Both Mechanisms

| Mechanism | Speed of revocation | Requires connectivity | Requires XRPL |
|-----------|--------------------|-----------------------|----------------|
| JWKS `active: false` | Next JWKS fetch (cache-dependent) | Yes | No |
| XRPL Credential delete | Immediate (ledger finality ~4s) | Yes | Yes |

For maximum safety, PA operators SHOULD use both mechanisms simultaneously:

1. Set `active: false` in the JWKS endpoint (covers non-XRPL verifiers).
2. Delete the on-chain credential (covers XRPL-aware verifiers with near-instant effect).
3. Issue updated Trust Bundles omitting the revoked key (covers offline verifiers on next
   bundle refresh).

### Trust Bundle Freshness

Trust Bundles that were signed before a key was revoked will continue to include the
compromised key until they expire. To limit the exposure window:

- Deployments SHOULD set Trust Bundle `expiresAt` to short intervals (hours, not days) in
  high-assurance environments.
- Trust Bundle builders SHOULD check both the JWKS `active` field and the on-chain credential
  for each key before embedding it in a new bundle.
- Verifiers with connectivity SHOULD supplement Trust Bundle lookups with an on-chain credential
  check when available.

---

## See Also

- [Signature Schemes](./mpcp.md#signature-schemes)
- [PolicyGrant](./PolicyGrant.md)
- [SignedBudgetAuthorization](./SignedBudgetAuthorization.md)
- [Trust Bundles](./trust-bundles.md)
