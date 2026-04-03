# MPCP specification — SECOP tracker

This file tracks **security operations (SECOP) review** outcomes and spec work items for [mpcp-spec](https://github.com/mpcp-protocol/mpcp-spec). It mirrors the detailed review notes maintained in the MPCP SECOP plan (Cursor plan: *MPCP Spec SECOP Review*) and should be updated when new mitigations land.

## Merged / landed spec PRs (traceability)

| PR | Themes |
|----|--------|
| [#44](https://github.com/mpcp-protocol/mpcp-spec/pull/44) | `budgetId` replay **MUST**; `activeGrantCredentialIssuer`; grant revocation via XLS-70; related doc updates |
| [#45](https://github.com/mpcp-protocol/mpcp-spec/pull/45) | **5a–5c:** actor/`actorId` binding + merchant terminal impersonation + issuer TLS/pinning guidance |
| [#46](https://github.com/mpcp-protocol/mpcp-spec/pull/46) | **6a–6c:** gateway durable spend state; `authorizedGateway` required + optional gateway credentials; mandatory `velocityLimit`; **MPCP v1 XRPL-only** conformance (`allowedRails`, no `revocationEndpoint` on conforming grants) |

## Spec work items (checklist)

Status: **done** | **open**

| ID | Item | SECOP ref | Status |
|----|------|-----------|--------|
| spec-purpose-enforcement | Normative Trust Gateway `allowedPurposes` enforcement | 1a | done |
| spec-destination-allowlist | PA-signed `destinationAllowlist` + merchant XRPL Credentials | 1b | done |
| spec-key-revocation | JWKS `active` + XRPL Credential lifecycle for PA keys | 2a | done |
| spec-offline-replay | Offline SBA replay guidance (`budgetId` dedup, etc.) | 3b | done |
| spec-offline-cumulative | `offlineMaxCumulativePayment` on PolicyGrant | 3a | done |
| spec-budgetid-must | `budgetId` uniqueness / replay **MUST** at gateway | 4a | done |
| spec-clock-guidance | Clock sync + drift tolerance for verifiers | 3d | done |
| spec-gateway-seed-compromise | Gateway seed compromise scenario + HSM + credential de-auth | 2b | done |
| spec-trust-bundle-signer-compromise | Trust Bundle signer compromise + refresh guidance | 2c | done |
| spec-agent-key-compromise | Per-agent keys + subject credentials / attestation | 2d | done |
| spec-authorized-gateway-required | `authorizedGateway` **required**; optional `gatewayCredentialIssuer` / `gatewayCredentialType` | 6b | done |
| spec-gateway-persistence | Durable cumulative spend; restart reconstruction or refuse | 6a | done |
| spec-velocity-limit-mandatory | Required `velocityLimit` on conforming PolicyGrants | 6c | done |
| spec-xrpl-mandatory-v1 | Conformance: `allowedRails` = `["xrpl"]` only; no `revocationEndpoint` on conforming grants | — | done |
| spec-5a-5b-5c | DID/`actorId` binding; merchant impersonation narrative; TLS pinning for JWKS | 5a–5c | done |
| spec-permissioned-domain | XRPL Permissioned Domain as MPCP trust perimeter extension | NEW | open |
| spec-test-vectors | Canonical JSON + verification test vectors directory | 8c / 10b | open |
| spec-budget-clarification | Clarify `budgetMinor` vs `maxSpend` relationship | 10a | open |

## Open follow-ups (from review; not yet tracked as done above)

These remain good next spec issues even when not listed in the checklist:

- **1c** — SBA over-authorization guidance (optional `quoteHash`, etc.)
- **7a / 7b** — Transparent gateway: PA key separation; session token hardening (e.g. DPoP-style)
- **8a / 8b** — JWK `alg` + deprecation; secp256k1 low-S normalization
- **9a / 9b** — Merchant-visible grant subset; privacy / linkability extensions
- **10c** — FPA verification step in pipeline
- **Diagrams** — Some SVGs still mention `revocationEndpoint`; align with v1 credential-only revocation when touched

## Normative pointers

- Conformance (XRPL v1): [PolicyGrant — MPCP conformance](docs/protocol/PolicyGrant.md#mpcp-conformance-mandatory-xrpl)
- Gateway spend + velocity: [Trust Model — Gateway durable spend state](docs/protocol/trust-model.md#gateway-durable-spend-state-must), [PolicyGrant — Velocity limit enforcement](docs/protocol/PolicyGrant.md#velocity-limit-enforcement)
- Settlement verification steps: [mpcp.md — Settlement Verification](docs/protocol/mpcp.md#settlement-verification)
