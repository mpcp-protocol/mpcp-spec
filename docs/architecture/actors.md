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
- Manages charging/payment budgets
- Issues SignedBudgetAuthorization and SignedPaymentAuthorization
- Executes settlement transactions

The wallet is the MPCP actor that signs SignedBudgetAuthorization and SignedPaymentAuthorization.

> **Note on Actor Identity:** The `actorId` field in SBA artifacts is self-reported by the wallet. Production deployments SHOULD establish actor attestation via device key binding (e.g., a hardware-backed key whose public key is registered with the fleet operator). Without attestation, `actorId` cannot be cryptographically verified and is informational only.

## AI Agent

An AI agent acting under human authorization, using MPCP to bound its spending authority.

**Receives:** PolicyGrant signed by a human principal (DID key)

**Responsibilities:**

- Receives a PolicyGrant from a human principal (DID-signed) and acts as its spending subject
- Acts as **session authority** — creates and signs SBAs (typically with TRIP scope)
- Acts as **payment decision service** — enforces `allowedPurposes` and signs SPAs
- Maintains cumulative spend counter across all sessions in the trip/project
- SHOULD check `revocationEndpoint` before signing each SPA (agents are online by design)

**Contrast with Vehicle Wallet:**

| | Vehicle Wallet | AI Agent |
|---|----------------|---------|
| Policy authority | Fleet operator | Human (DID) |
| Connectivity | Offline-capable | Online by design |
| Revocation | Not applicable | SHOULD check before each payment |
| Budget scope | SESSION / DAY | TRIP (multi-day) |

**Examples:** Travel booking agent, subscription manager, event budget agent.

> The `actorId` field in SBA artifacts is used for agent identity (e.g. `"ai-trip-planner-v2"`).
> Agent attestation follows the same key binding recommendations as vehicle wallets.

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

- [Reference Flow](fleet-ev-reference-flow.md) — Full actor interaction in EV charging scenario
- [System Model](system-model.md)
