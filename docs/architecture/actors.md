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

> **Note on Actor Identity:** The `actorId` field in SBA artifacts is self-reported by the wallet. Production deployments SHOULD establish actor attestation via device key binding (e.g., a hardware-backed key whose public key is registered with the fleet operator). Without attestation, `actorId` cannot be cryptographically verified and is informational only.

## AI Agent

An AI agent acting under human authorization, using MPCP to bound its spending authority.

**Receives:** PolicyGrant signed by a human principal (DID key)

**Responsibilities:**

- Receives a PolicyGrant from a human principal (DID-signed) and acts as its spending subject
- Acts as **session authority** — creates and signs SBAs (typically with TRIP scope)
- Enforces `allowedPurposes` before issuing each SBA — refuses payments for disallowed merchant categories
- Maintains cumulative spend counter across all sessions in the trip/project
- SHOULD check `revocationEndpoint` before issuing each SBA (agents are online by design)

**Contrast with Vehicle Wallet:**

| | Vehicle Wallet | AI Agent |
|---|----------------|---------|
| Policy authority | Fleet operator | Human (DID) |
| Connectivity | Offline-capable | Online by design |
| Revocation | Not applicable | SHOULD check before each SBA |
| Budget scope | SESSION / DAY | TRIP (multi-day) |

**Examples:** Travel booking agent, subscription manager, event budget agent.

> The `actorId` field in SBA artifacts is used for agent identity (e.g. `"ai-trip-planner-v2"`).
> Agent attestation follows the same key binding recommendations as vehicle wallets.

## Trust Gateway

A mandatory online enforcement actor in MPCP's XRPL profile. The Trust Gateway holds the
XRPL gateway seed and is the only entity that submits payment transactions on behalf of a grant.

**Responsibilities:**

- Creates an XRPL budget escrow at grant issuance, pre-reserving the full `budgetMinor` XRP
- Enforces the PA-signed `budgetMinor` as a hard ceiling — maintains an independent spend counter
- Verifies each SBA signature and purpose before submitting a XRPL Payment transaction
- Attaches `mpcp/grant-id` memo to every XRPL payment for on-chain audit traceability
- Releases the escrow on grant revocation (EscrowFinish with preimage) or expiry (EscrowCancel)
- Rejects payments if `authorizedGateway` in the PA-signed grant does not match its own address

**Why it is mandatory:** Without the Trust Gateway, a compromised or prompt-injected agent could
self-report any budget ceiling. The gateway enforces the PA-signed limit independently — it never
trusts the agent's view of remaining budget. Even if the gateway itself were compromised, the
XRPL escrow provides an on-chain upper bound that the ledger enforces.

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

**Examples:** XRPL + RLUSD, EVM stablecoins, Stripe, hosted providers.

MPCP does not replace settlement systems—it **controls authorization above them**.

## See Also

- [Reference Flow (Fleet EV)](fleet-ev-reference-flow.md) — Full actor interaction in EV charging scenario
- [Reference Flow (Human-Agent)](human-agent-reference-flow.md) — Human-to-AI-agent travel budget scenario
- [System Model](system-model.md)
