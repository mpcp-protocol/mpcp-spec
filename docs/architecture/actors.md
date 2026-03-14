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

> **Note on Vehicle Identity:** The `vehicleId` field in SBA artifacts is self-reported by the wallet. Production deployments SHOULD establish vehicle attestation via device key binding (e.g., a hardware-backed key whose public key is registered with the fleet operator). Without attestation, `vehicleId` cannot be cryptographically verified and is informational only.

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

- [Reference Flow](reference-flow.md) — Full actor interaction in EV charging scenario
- [System Model](system-model.md)
