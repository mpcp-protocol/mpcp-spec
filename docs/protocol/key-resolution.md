# Key Resolution

Part of the [Machine Payment Control Protocol (MPCP)](./mpcp.md).

## Overview

MPCP artifacts carry two fields that identify the signing authority:

- `issuer` — identifies the authority (domain, HTTPS URL, or DID)
- `issuerKeyId` — selects the specific key within that authority's key set

Verifiers use these two fields to retrieve the public key required to validate the artifact signature.

MPCP defines **HTTPS well-known** as the baseline key resolution mechanism. All conforming implementations MUST support it. DID resolution and Verifiable Credentials are optional higher-level mechanisms that deployments MAY use in addition.

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
  "x": "base64url-encoded-32-byte-public-key"
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
  "y": "base64url-encoded-y-coordinate"
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
      "x": "base64url..."
    },
    {
      "kid": "policy-auth-key-2",
      "use": "sig",
      "kty": "EC",
      "crv": "secp256k1",
      "x": "base64url...",
      "y": "base64url..."
    }
  ]
}
```

The document is a plain JSON object. The `keys` array contains one or more JWK entries. An authority MAY publish multiple keys to support key rotation.

### HTTP Response Requirements

| Requirement | Value |
|-------------|-------|
| Content-Type | `application/json` |
| Status | `200 OK` for valid responses |
| Encoding | UTF-8 |

Verifiers SHOULD cache key set responses according to standard HTTP cache semantics (`Cache-Control`, `ETag`). Verifiers MUST revalidate cached responses before use when they have expired.

---

## Resolution Algorithm

```text
function resolvePublicKey(issuer, issuerKeyId):
    url = deriveKeySetUrl(issuer)
    keySetDoc = httpGet(url)               # HTTPS required; TLS validated
    keys = parseKeySet(keySetDoc)
    jwk = keys.find(k => k.kid == issuerKeyId)
    if jwk is null:
        raise KEY_NOT_FOUND
    return jwk
```

If the well-known endpoint is unreachable and no pre-configured key is available, the verifier MUST fail the signature check and reject the artifact.

---

## Pre-Configured Keys

Implementations MAY pre-configure keys from trusted sources in lieu of or in addition to well-known lookups.

Pre-configured keys are identified by `issuer` + `issuerKeyId` and expressed as JWK objects. When a pre-configured entry matches the artifact, the verifier uses it directly without fetching the well-known endpoint.

This supports:

- offline and air-gapped machine wallets
- embedded deployments where network access is unavailable
- pinned deployments where key mutation must be prevented

Pre-configured keys MUST still be expressed in JWK format.

---

## DID and Verifiable Credentials (Optional)

Deployments MAY use decentralized identifiers (DIDs) or Verifiable Credentials (VCs) as a higher-level key binding mechanism.

When the `issuer` field carries a `did:` URI other than `did:web:`, verifiers MAY use DID resolution to retrieve the key material. Resolved key material MUST still be expressed and validated as JWK.

VC-based key discovery is outside the core protocol.

DID resolution and VC verification are never required for MPCP compliance. Implementations that support only HTTPS well-known key resolution are fully conformant.

---

## `did:xrpl` DID Resolution

MPCP defines an optional resolution mechanism for `did:xrpl` DIDs, used when XRPL-native policy
authorities issue grants with an XRPL account as the issuer.

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
| `KEY_SET_FETCH_FAILED` | Well-known endpoint unreachable or returned non-200 |
| `KEY_SET_INVALID` | Key set document could not be parsed |
| `KEY_FORMAT_INVALID` | Key entry is not a valid JWK |

---

## See Also

- [Signature Schemes](./mpcp.md#signature-schemes)
- [PolicyGrant](./PolicyGrant.md)
- [SignedBudgetAuthorization](./SignedBudgetAuthorization.md)
- [SignedPaymentAuthorization](./SignedPaymentAuthorization.md)
