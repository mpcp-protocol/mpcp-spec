# Actors

MPCP defines several actor types that participate in machine payment flows.

## Fleet Operator

Owns and manages the autonomous fleet (vehicles, robots, agents).

**Responsibilities:**

- Defines vehicle payment policies
- Sets spending limits
- Restricts allowed vendors and locations
- Issues PolicyGrant artifacts

**Examples:** Robotaxi fleet, delivery fleet, autonomous logistics fleet.

## Vehicle Wallet (Machine Wallet)

Resides in each machine (EV, robot, IoT device) and enforces MPCP constraints.

**Responsibilities:**

- Enforces policy constraints
- Manages payment budgets
- Issues SignedBudgetAuthorization (SBA) per payment request
- Submits SBAs to the Trust Gateway for settlement

The wallet is the MPCP actor that signs SignedBudgetAuthorizations. Settlement is executed by the Trust Gateway.

> **Note on Actor Identity:** The `actorId` field in SBA artifacts is self-reported by the wallet unless bound by stronger policy. Production deployments SHOULD establish actor attestation via device key binding (e.g., a hardware-backed key whose public key is registered with the fleet operator). Without attestation, `actorId` cannot be cryptographically verified and is informational only.
>
> **XRPL DID (recommended):** For XRPL deployments using credential-based subject attestation, `PolicyGrant.subjectId` SHOULD use the canonical form `did:xrpl:{network}:{rAddress}` (where `{network}` identifies the intended ledger, e.g. `main` or `test`, and `{rAddress}` is the agent's classic address). This aligns the grant subject with verifiable on-chain identity. The SBA `actorId` MUST then equal the same `{rAddress}` so the Trust Gateway can correlate the signed authorization with the credential **Subject** account.
>
> **Per-agent keys (SHOULD):** Each vehicle or agent SHOULD have a unique SBA signing key. Shared keys prevent isolation of a compromised agent — revoking the shared key disrupts all agents using it. For XRPL deployments, the fleet operator SHOULD issue an XLS-70 Credential to each agent's account (`CredentialType = hex("mpcp:fleet-agent")`). The PolicyGrant can bind to the agent via `subjectCredentialIssuer` and `subjectCredentialType`. On compromise of one agent, the operator deletes that agent's credential — other agents are unaffected. See [Subject Attestation](../protocol/PolicyGrant.md#subject-attestation).

## AI Agent

An AI agent acting under human authorization, using MPCP to bound its spending authority.

**Receives:** PolicyGrant signed by a human principal (DID key)

**Responsibilities:**

- Receives a PolicyGrant from a human principal (DID-signed) and acts as its spending subject
- Acts as **session authority** — creates and signs SBAs (typically with TRIP scope)
- Enforces `allowedPurposes` before issuing each SBA — refuses payments for disallowed merchant categories (first line of defense; the Trust Gateway independently enforces the same check)
- Declares the payment `purpose` in each settlement request so the Trust Gateway can verify it against the PA-signed `allowedPurposes`
- Sets SBA `destinationAllowlist` as a subset of the PolicyGrant's PA-signed `destinationAllowlist` (when present)
- Maintains cumulative spend counter across all sessions in the trip/project
- SHOULD verify grant is not revoked before issuing each SBA — on XRPL, active-grant credential lookup when `activeGrantCredentialIssuer` is set (conforming grants omit `revocationEndpoint`; agents are online by design)

**Contrast with Vehicle Wallet:**

| | Vehicle Wallet | AI Agent |
|---|----------------|---------|
| Policy authority | Fleet operator | Human (DID) |
| Connectivity | Offline-capable | Online by design |
| Revocation | Not applicable | SHOULD check before each SBA |
| Budget scope | SESSION / DAY | TRIP (multi-day) |

**Examples:** Travel booking agent, subscription manager, event budget agent.

> The `actorId` field in SBA artifacts is used for agent identity (e.g. `"ai-trip-planner-v2"`).
> Agent attestation follows the same per-agent key and XRPL Credential recommendations as
> vehicle wallets. See [Subject Attestation](../protocol/PolicyGrant.md#subject-attestation).

## Trust Gateway

A mandatory online enforcement actor in MPCP's XRPL profile. The Trust Gateway holds the
XRPL gateway seed and is the only entity that submits payment transactions on behalf of a grant.

**Responsibilities:**

- Creates an XRPL budget escrow at grant issuance, pre-reserving the full `budgetMinor` XRP
- Enforces the PA-signed `budgetMinor` as a hard ceiling — maintains a **durable** independent spend counter (survives restart; see [Trust Model — Gateway durable spend state](../protocol/trust-model.md#gateway-durable-spend-state-must))
- Enforces PA-signed `velocityLimit` (see [PolicyGrant — Velocity limit enforcement](../protocol/PolicyGrant.md#velocity-limit-enforcement))
- Verifies each SBA signature before submitting a XRPL Payment transaction
- Enforces `allowedPurposes` from the PA-signed grant — rejects payments whose declared purpose is not in the allowlist (see [Purpose Enforcement](../protocol/PolicyGrant.md#purpose-enforcement))
- Enforces `destinationAllowlist` and/or `merchantCredentialIssuer` from the PA-signed grant — rejects payments to unapproved destinations (see [Destination Enforcement](../protocol/PolicyGrant.md#destination-enforcement)); this is the authoritative check against **merchant terminal impersonation** at settlement (see [Threat Model — Merchant terminal impersonation](../protocol/mpcp.md#merchant-terminal-impersonation-interaction-layer))
- When `subjectCredentialIssuer` is present on the grant, verifies `SBA.authorization.actorId` matches the attested XRPL credential Subject and rejects with `SUBJECT_ACTOR_MISMATCH` or `SUBJECT_NOT_ATTESTED` as defined in [Subject Attestation](../protocol/PolicyGrant.md#subject-attestation)
- Attaches `mpcp/grant-id` memo to every XRPL payment for on-chain audit traceability
- Releases the escrow on grant revocation (EscrowFinish with preimage) or expiry (EscrowCancel)
- Rejects payments if `authorizedGateway` in the PA-signed grant does not match its own XRPL address (**required** on conforming grants)
- When `gatewayCredentialIssuer` and `gatewayCredentialType` are present, verifies its XRPL account holds the matching on-chain credential before each settlement (see [Gateway credential binding](../protocol/PolicyGrant.md#gateway-credential-binding-optional))

**Why it is mandatory:** Without the Trust Gateway, a compromised or prompt-injected agent could
self-report any budget ceiling. The gateway enforces the PA-signed limit independently — it never
trusts the agent's view of remaining budget. Even if the gateway itself were compromised, the
XRPL escrow provides an on-chain upper bound that the ledger enforces.

**Key security:** The gateway's XRPL private key SHOULD be stored in an HSM or KMS. The PA
SHOULD issue an XRPL Credential to the gateway account (`CredentialType = hex("mpcp:authorized-gateway")`);
on compromise, the PA deletes the credential to revoke the gateway's on-chain authorization.
See [Gateway Seed Security](../protocol/trust-model.md#gateway-seed-security).

**Required for:** Online payments, budget enforcement, escrow create/cancel.

**Optional for:** Offline signature-only mode — merchants can accept payments without the gateway
using Trust Bundle key verification + `offlineMaxSinglePayment` cap, accepting reduced guarantees
(SBA signature valid, but cumulative budget not verified).

> **Trust level:** The Trust Gateway sits between the Policy Authority and the Agent in the
> trust hierarchy. It can enforce PA policy but cannot forge PolicyGrant signatures.
> See [Trust Model](../protocol/trust-model.md).

## Service Provider

The entity that receives payment for a service (parking, charging, tolls).

**Responsibilities:**

- Requests payment authorization
- Verifies MPCP artifact chain
- Provides or denies service based on verification

**Examples:** Charging network operator, parking operator, toll system.

## Route / Dispatch System

(Optional) Determines routing and service requirements.

**Responsibilities:**

- Determines charging/parking locations along route
- Identifies approved service networks
- Provides trip metadata to the vehicle

May influence PolicyGrant constraints.

## MPCP Verifier

Validates the full authorization chain.

**Verification may occur:**

- Inside the service provider backend
- Inside a dedicated MPCP verification service
- During post-transaction auditing

## Settlement Rail

Executes the actual payment.

**Examples:** XRPL native XRP and IOUs (e.g. RLUSD).

MPCP does not replace settlement systems—it **controls authorization above them**.

## See Also

- [Reference Flow (Fleet EV)](fleet-ev-reference-flow.md) — Full actor interaction in EV charging scenario
- [Reference Flow (Human-Agent)](human-agent-reference-flow.md) — Human-to-AI-agent travel budget scenario
- [System Model](system-model.md)
