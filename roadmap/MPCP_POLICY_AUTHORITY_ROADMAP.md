# mpcp-policy-authority — Product Roadmap

Deployable backend service implementing the **Policy Authority** actor from the MPCP protocol spec.

The Policy Authority is the entity that evaluates policy, issues `PolicyGrant` artifacts, manages revocation, and anchors policy documents on-chain. This service is the production counterpart to the read-only adapters in `mpcp-reference`.

`mpcp-reference` remains the canonical SDK and protocol library. This service is a consumer of it — no protocol logic is duplicated here.

---

## Guiding Principles

**Backend-first, headless API**
No UI. HTTP API only. Designed to be embedded in operator infrastructure or run as a standalone service.

**Protocol boundary respected**
All artifact construction and verification goes through the `mpcp-reference` SDK. This service owns persistence, signing key management, on-chain write operations, and the HTTP surface.

**Dependency-light**
Fastify for HTTP. Drizzle ORM for storage (SQLite in dev, Postgres in prod). No framework magic.

**Docker-ready from day one**
Dockerfile + docker-compose included in PR1. Local dev with a single command.

---

## Phase 1 — Core Policy Authority API

Goal: A running service that can issue, store, and revoke PolicyGrants.

---

### PR1 — Project Setup

Initialise the repository with the production-ready baseline.

Stack:
- Node.js 22 + TypeScript (ESM)
- Fastify for HTTP
- `mpcp-reference` as an npm dependency (SDK + verifier)
- Drizzle ORM with `better-sqlite3` (dev) / `postgres` (prod)
- Vitest for tests
- Docker + docker-compose for local dev

Files:
```
src/
  server.ts          — Fastify instance + plugin registration
  index.ts           — entrypoint, start server
  config.ts          — env-var configuration (zod-validated)
  db/
    schema.ts        — Drizzle table definitions
    client.ts        — DB connection
Dockerfile
docker-compose.yml
```

Acceptance criteria:
- `npm run dev` starts the server
- `GET /health` returns `{ ok: true, version: "1.0" }`
- `docker-compose up` starts service + db cleanly

---

### PR2 — Policy Document Management

Create, hash, and store policy documents. The Policy Authority is the custodian of full policy documents when grants are issued in hash-only anchor mode.

Endpoints:

```
POST /policies
  Body: { policyDocument: object }
  Returns: { policyHash, storedAt }

GET /policies/:policyHash
  Returns: { policyDocument, policyHash, storedAt }
  404 if not found
```

Implementation:
- `policyHash` computed using `canonicalJson` + SHA-256 from `mpcp-reference` SDK
- Stored in `policies` table with `policyHash` as primary key
- `GET` is the custody retrieval endpoint — auditors verify by hashing the returned document against the on-chain `policyHash`

DB schema:
```typescript
policies: {
  policyHash:   text (PK)
  document:     text (JSON)
  storedAt:     text (ISO 8601)
}
```

Acceptance criteria:
- Same document always produces the same `policyHash`
- `GET` returns the exact document that was `POST`ed
- Duplicate `policyHash` is idempotent (upsert)

---

### PR3 — PolicyGrant Issuance

Issue signed PolicyGrants backed by a stored policy document.

Endpoints:

```
POST /grants
  Body: {
    policyHash: string,
    subjectId: string,
    allowedRails: string[],
    allowedAssets?: Asset[],
    expiresAt: string,
    revocationEndpoint?: string,
    allowedPurposes?: string[],
    anchorRef?: string
  }
  Returns: SignedPolicyGrant

GET /grants/:grantId
  Returns: { grant, issuedAt, status: "active" | "revoked" }
  404 if not found
```

Implementation:
- Uses `createSignedPolicyGrant` from SDK
- Signing key from env: `MPCP_POLICY_GRANT_SIGNING_PRIVATE_KEY_PEM`, `MPCP_POLICY_GRANT_SIGNING_KEY_ID`
- Validates `policyHash` exists in `policies` table before issuing
- Stores issued grant in `grants` table

DB schema:
```typescript
grants: {
  grantId:    text (PK)
  policyHash: text (FK → policies)
  grant:      text (JSON — full SignedPolicyGrant)
  issuedAt:   text (ISO 8601)
  status:     text ("active" | "revoked")
  revokedAt:  text (nullable)
}
```

Acceptance criteria:
- Issued grant passes `verifyPolicyGrant` from SDK
- Grant is rejected if `policyHash` is unknown
- `GET /grants/:grantId` returns full grant + status

---

### PR4 — Revocation Endpoint

Implement the `revocationEndpoint` contract from the MPCP spec.

Endpoints:

```
GET /revoke?grantId={grantId}
  Returns: { revoked: boolean, revokedAt?: string }
  (MPCP revocation check contract — called by merchants)

POST /revoke
  Body: { grantId: string }
  Returns: { revoked: true, revokedAt: string }
  (Authenticated — called by the grant holder / operator)
```

Implementation:
- `GET /revoke` is unauthenticated — any merchant can check
- `POST /revoke` requires API key (PR8)
- Updates `grants.status` and `grants.revokedAt`
- Idempotent: revoking an already-revoked grant returns the original `revokedAt`

Revocation endpoint URL pattern:
```
https://{host}/revoke
```
This URL is placed in `PolicyGrant.revocationEndpoint` at issuance time.

Acceptance criteria:
- `GET /revoke?grantId=unknown` returns `{ revoked: false }`
- `GET /revoke?grantId=revoked` returns `{ revoked: true, revokedAt: "..." }`
- `POST /revoke` on active grant marks it revoked
- `checkRevocation()` from SDK works against this endpoint

---

## Phase 2 — On-Chain Anchoring

Goal: PolicyGrants backed by on-chain proofs. Depends on `mpcp-reference` PR28 (Encrypted Policy Anchoring) being released.

---

### PR5 — HCS Policy Anchoring

Integrate HCS anchoring into the grant issuance flow.

`POST /grants` gains an optional `anchor` field:

```
POST /grants
  Body: {
    ...existing fields,
    anchor?: {
      rail: "hedera-hcs",
      submitMode: "hash-only" | "full-document" | "encrypted",
      encryptionKeyBase64?: string   // required for submitMode="encrypted"
    }
  }
```

If `anchor` is provided:
1. Call `hederaHcsAnchorPolicyDocument` from SDK after grant issuance
2. Set `anchorRef = result.reference` on the issued grant
3. Store `anchorRef` in `grants` table

Env vars (forwarded to SDK):
- `MPCP_HCS_POLICY_TOPIC_ID`
- `MPCP_HCS_OPERATOR_ID`
- `MPCP_HCS_OPERATOR_KEY`
- `HEDERA_NETWORK`

Acceptance criteria:
- Issued grant has `anchorRef: "hcs:{topicId}:{seq}"` when anchor requested
- `submitMode` defaults to `"hash-only"` if not specified
- Anchoring failure does not block grant issuance (graceful degradation with warning in response)

---

### PR6 — XRPL NFT Minting

Mint a non-transferable XRPL NFToken for each issued PolicyGrant. The NFT encodes the revocation mechanism — burning it revokes the grant.

`POST /grants` gains XRPL anchor support:

```
POST /grants
  Body: {
    ...existing fields,
    anchor?: {
      rail: "xrpl-nft",
      submitMode: "hash-only" | "encrypted",
      encryptionKeyBase64?: string,
      ipfsGateway?: string           // for encrypted mode; default: web3.storage
    }
  }
```

Flow:
1. For `"encrypted"` mode: call `xrplEncryptAndStorePolicyDocument` from SDK → get IPFS CID
2. Mint NFToken with `URI = hex("ipfs://{CID}")` and `Flags: tfTransferable=0`
3. Set `anchorRef = "xrpl:nft:{tokenId}"` on the issued grant

XRPL account config:
- `MPCP_XRPL_ISSUER_SEED` — issuer account seed (holds XRP for reserves/fees)
- `MPCP_XRPL_RPC_URL` — default: `https://xrplcluster.com`
- `MPCP_XRPL_NETWORK` — `mainnet` | `testnet`

Revocation via NFT burn:
- `POST /revoke` on a grant with XRPL `anchorRef` burns the NFToken
- Falls back to DB-only revocation if burn fails (with warning in response)

Acceptance criteria:
- Issued grant has `anchorRef: "xrpl:nft:{tokenId}"`
- `checkXrplNftRevocation(tokenId)` from SDK returns `{ revoked: false }` after mint
- `POST /revoke` burns NFT; subsequent `checkXrplNftRevocation` returns `{ revoked: true }`
- Integration tests against XRPL testnet

---

### PR7 — Persistent Document Custody

Replace the in-memory custody model with proper persistent storage and configurable retention.

Changes:
- Policy documents in `policies` table are the persistent custody store
- `GET /policies/:policyHash` is the custody retrieval endpoint — used by auditors
- Add `custodyMode` config: `"public"` (anyone can fetch) | `"authenticated"` (API key required for GET)
- Add optional `retentionDays` config: documents older than N days are soft-deleted (hash retained, document nulled) after the grant expires

DB migration:
```typescript
policies: {
  ...existing,
  deletedAt: text (nullable)  // soft delete timestamp
}
```

Acceptance criteria:
- `GET /policies/:policyHash` works after service restart (persisted)
- Soft-deleted documents return `{ policyHash, available: false }` not 404
- `custodyMode: "authenticated"` blocks unauthenticated `GET /policies/*`

---

## Phase 3 — Production Hardening

Goal: Safe to run in a real deployment.

---

### PR8 — API Authentication

Scope-based API key authentication.

Scopes:
- `grants:write` — issue grants, POST /policies
- `grants:revoke` — POST /revoke
- `grants:read` — GET /grants/*, GET /policies/* (when custodyMode=authenticated)

Key management:
- Keys stored hashed (SHA-256) in `api_keys` table
- `POST /admin/keys` — create key (requires `admin` scope; admin key set via env)
- `DELETE /admin/keys/:keyId` — revoke key

`GET /revoke?grantId=` remains unauthenticated (MPCP spec requirement — merchants must be able to check).

Acceptance criteria:
- Unauthenticated `POST /grants` returns 401
- Valid key with wrong scope returns 403
- Key revocation takes effect immediately

---

### PR9 — Audit Log

Immutable append-only record of all policy authority actions.

Events logged:
- `grant.issued` — grantId, policyHash, subjectId, issuedAt
- `grant.revoked` — grantId, revokedBy, revokedAt, method (endpoint | nft-burn)
- `policy.stored` — policyHash, storedAt
- `anchor.submitted` — grantId, anchorRef, rail, submitMode

Endpoints:
```
GET /audit?grantId={grantId}     — all events for a grant
GET /audit?policyHash={hash}     — all events for a policy
GET /audit?from={iso}&to={iso}   — time-range query
```

DB schema:
```typescript
audit_log: {
  id:        integer (PK, autoincrement)
  event:     text
  payload:   text (JSON)
  createdAt: text (ISO 8601)
}
```

No updates or deletes on this table. Insert-only.

---

### PR10 — Integration Test Suite

End-to-end tests against a real service instance (Docker Compose).

Test scenarios:
- Issue grant → verify with `verifyPolicyGrant` from SDK
- Issue grant → revoke via endpoint → `checkRevocation` returns revoked
- Issue grant with HCS anchor → verify `anchorRef` format
- Issue grant with XRPL NFT anchor → `checkXrplNftRevocation` not revoked → revoke → revoked
- Full settlement chain: issue grant → create SBA → SPA → `verifySettlement` passes

Infrastructure:
- `docker-compose.test.yml` — service + SQLite in one container
- XRPL testnet credentials in CI secrets
- Hedera testnet credentials in CI secrets

---

## Deferred

- **Multi-tenant** — single operator for MVP; multi-tenant key isolation deferred
- **Key rotation** — manual env-var rotation for MVP; automated rotation deferred
- **Webhook notifications** — on grant issuance / revocation; deferred to Phase 4
- **XRPL escrow / conditional payments** — deferred to post-MVP
- **Stellar / EVM profiles** — deferred to post-MVP
