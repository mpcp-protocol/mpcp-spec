
# MPCP Implementation Roadmap

This document defines the implementation plan for the **Machine Payment Control Protocol (MPCP)** reference implementation.

The goal of this roadmap is to evolve MPCP from a **specification and prototype** into a **deterministic, verifiable, production‑ready protocol stack**.

The roadmap is divided into phases. Each phase is intended to be implemented through **small focused PRs** to keep review scope manageable.

---

# Guiding Principles

The implementation roadmap follows several principles:

**Protocol first**  
The protocol specification remains the source of truth. Code must conform to the protocol definitions.

**Determinism**  
All MPCP artifacts must serialize and hash deterministically across implementations.

**Rail agnostic**  
MPCP must remain independent of any specific payment rail.

**Verifiable**  
Every payment decision and settlement must be independently verifiable.

**Small PRs**  
Each feature is implemented in isolated PRs to ensure safe review and easy rollback.

---

# Phase 1 — Protocol Determinism

Goal: Ensure MPCP artifacts produce **deterministic hashes and serialization**.

This phase establishes the foundation required for:

- SettlementIntentHash
- cross‑implementation verification
- distributed anchoring

---

## PR 1 — Canonical Serialization

Create a deterministic JSON canonicalization implementation.

Directory:

src/canonical/

Files:

- canonicalJson.ts
- hash.ts

Responsibilities:

- stable key ordering
- UTF‑8 encoding
- whitespace removal
- deterministic serialization

Example flow:

SettlementIntent

→ canonical JSON

→ SHA256

→ SettlementIntentHash

Acceptance Criteria:

- identical hash across multiple runs
- identical hash across Node versions
- deterministic ordering verified in tests

Tests:

- canonical serialization snapshot tests
- hash stability tests

---

## PR 2 — Artifact Schemas

Define strict schemas for all MPCP artifacts.

Directory:

src/schema/

Schemas:

- PolicyGrant
- BudgetAuthorization
- SignedBudgetAuthorization
- SignedPaymentAuthorization
- SettlementIntent
- FleetPolicyAuthorization

Recommended tooling:

- zod

Responsibilities:

- validate artifact structure
- enforce required fields
- prevent malformed artifacts

Acceptance Criteria:

- all artifacts validate through schema
- invalid artifacts rejected with clear errors

---

## PR 3 — SettlementIntentHash Implementation

Implement deterministic hashing of settlement intents.

Directory:

src/hash/

Functions:

computeSettlementIntentHash(intent)

Responsibilities:

- canonicalize intent
- compute SHA256
- produce deterministic intentHash

Acceptance Criteria:

- identical hash across identical intents
- mismatch detected if any field changes

Tests:

- intent mutation tests
- hash equality tests

---

# Phase 2 — Verification Engine

Goal: Implement a complete **MPCP verification engine**.

The verifier confirms that a settlement is valid according to all prior protocol artifacts.

---

## PR 4 — Core Verifier

Directory:

src/verify/

Functions:

- verifyPolicyGrant()
- verifyBudgetAuthorization()
- verifyPaymentAuthorization()
- verifySettlementIntent()
- verifySettlement()

Responsibilities:

Verify that:

- artifacts form a valid chain
- spending limits are respected
- policies are satisfied

Acceptance Criteria:

- settlement verification returns deterministic result
- clear failure reasons provided

---

## PR 5 — MPCP Verifier CLI

Create a command line verifier tool.

Directory:

src/cli/

Example usage:

npx mpcp verify settlement.json

Output example:

✔ intent hash valid

✔ SPA signature valid

✔ budget within limits

✔ policy grant valid

MPCP verification PASSED

Purpose:

- debugging
- dispute resolution
- protocol compliance checks

### PR 5A — CLI Explain Mode

Enhance the MPCP verifier CLI with an **explain mode** that provides step‑by‑step diagnostics for verification results.

Example usage:

npx mpcp verify settlement.json --explain

Example output:

MPCP Verification Report

✔ PolicyGrant.schema
✔ SignedBudgetAuthorization.schema
✔ SignedPaymentAuthorization.schema
✔ SettlementIntent.schema
✔ SignedBudgetAuthorization.valid
✘ SettlementIntent.intentHash mismatch
  Expected: 5d9b3c...
  Actual:   a1c82f...

Verification FAILED

Purpose:

- provide detailed debugging information
- help fleet operators diagnose payment failures
- support dispute investigation and audit workflows

Implementation:

Add a detailed verification report structure:

```
type VerificationCheck = {
  name: string           // Artifact.check (e.g. SettlementIntent.intentHash)
  phase: "schema" | "linkage" | "hash" | "policy"  // ordering: schema → linkage → hash → policy
  valid: boolean
  reason?: string
  expected?: unknown
  actual?: unknown
}

type DetailedVerificationReport = {
  valid: boolean
  checks: VerificationCheck[]  // sorted by phase
}
```

Verification check ordering: schema → linkage → hash → policy

Verification check naming: Artifact.check (e.g. PolicyGrant.schema, SignedBudgetAuthorization.schema, SettlementIntent.intentHash)

JSON output (`--json`): `{ "valid": boolean, "checks": VerificationCheck[] }`

Add a new verifier function: verifySettlementDetailed()

The CLI should render human‑readable output when `--explain` is used and machine‑readable JSON when `--json` is used.

Acceptance Criteria:

- CLI supports `--explain` flag
- CLI supports `--json` flag
- verification output clearly identifies the failing artifact
- verification checks are deterministically ordered by phase
- JSON output conforms to DetailedVerificationReport structure

---

## PR 6 — Protocol Conformance Tests

Directory:

test/protocol/

Tests:

- intent hash correctness
- policy grant validation
- budget authorization limits
- SPA verification
- settlement verification

Acceptance Criteria:

- full protocol verification suite passes

---

# Phase 3 — Developer Adoption

Goal: Make MPCP easy to integrate.

---

## PR 7 — SDK Improvements

Expand the SDK to support:

- artifact construction
- artifact signing
- verification helpers

Directory:

src/sdk/

Add helpers:

createPolicyGrant()

createBudgetAuthorization()

createSignedPaymentAuthorization()

createSettlementIntent()

computeIntentHash()

---

## PR 8 — End‑to‑End Example

Create a full working example flow.

Directory:

examples/parking-session/

Artifacts:

- fleet-policy.json
- policy-grant.json
- budget-auth.json
- signed-budget-auth.json
- spa.json
- settlement-intent.json
- settlement.json

Purpose:

Provide a full reference flow for developers.

### PR 8A — Autonomous Spend Guardrails Demo

Introduce a reference demonstration that highlights MPCP's core capability for **Machine Wallet Guardrails** — the ability for autonomous systems to spend money safely within cryptographically enforced limits.

Background:

Autonomous machines (robotaxis, delivery robots, charging systems, parking meters) must often perform payments without human approval. The primary risk for fleet operators is **unbounded or fraudulent machine spending**.

MPCP addresses this by enforcing a chain of authorization artifacts:

FleetPolicy → PolicyGrant → BudgetAuthorization → SignedPaymentAuthorization → Settlement

Each step progressively constrains the machine's spending ability through:

- maximum spend limits
- allowed payment rails
- allowed assets
- destination allowlists
- expiration times
- cryptographic signatures

This forms a **machine‑enforced spending sandbox**.

Example scenario:

A robotaxi performs autonomous payments during a trip:

vehicle arrives at parking

→ parking meter issues payment request

→ vehicle evaluates policy constraints

→ vehicle signs SPA within its authorized budget

→ parking meter verifies MPCP artifact chain

→ gate opens

No centralized payment API is required.

Demo Architecture:

Reference components may include:

- autonomous vehicle agent (wallet + MPCP SDK)
- parking / charging / toll service endpoint
- MPCP verifier
- settlement rail (XRPL, Stripe, etc.)

The demo should illustrate:

- policy‑limited autonomous spending
- local verification of MPCP artifacts
- tamper‑resistant authorization chains

Purpose:

### PR 8B — Automated Fleet Payment Demo

Create a runnable demonstration showing how an autonomous fleet vehicle performs a real MPCP‑controlled payment during operation.

Goal:

Demonstrate the complete **machine‑to‑machine payment loop** using MPCP artifacts and local verification.

Example Flow:

Robotaxi enters a parking facility

→ parking meter or gate sends payment request

→ vehicle evaluates its fleet policy and session budget

→ vehicle generates SettlementIntent

→ vehicle signs SignedPaymentAuthorization (SPA)

→ payment is executed on the configured settlement rail

→ parking system verifies MPCP artifact chain

→ gate opens

Components:

The demo should include minimal reference services:

- **Vehicle Agent**
  - MPCP SDK
  - wallet / signing keys
  - policy + budget enforcement

- **Parking / Charging Service**
  - payment request endpoint
  - MPCP verification endpoint

- **Verifier**
  - validates PolicyGrant → SBA → SPA → SettlementIntent chain

- **Settlement Rail Adapter**
  - mock rail or XRPL reference implementation

Key Behaviors to Demonstrate:

- autonomous payment authorization within fleet limits
- enforcement of session budgets
- deterministic SettlementIntent hashing
- verification without centralized payment infrastructure
- tamper detection if artifacts are modified

Deliverables:

- runnable demo script
- architecture diagram
- example MPCP artifact bundle
- documentation describing the end‑to‑end flow

Purpose:

Provide a **clear real‑world demonstration** of MPCP enabling autonomous machine payments for fleet systems such as robotaxis, delivery robots, charging infrastructure, and logistics automation.

This demo will serve as the primary reference for developers, partners, and mobility companies evaluating MPCP.

### PR 8C — Fleet Spend Policy Simulator

Create a lightweight tool that allows developers and fleet operators to simulate MPCP spend policies before deploying them to real vehicles or robots.

Goal:

Make it easy to test **machine wallet guardrails** and spending policies in a safe environment.

Background:

Fleet operators need confidence that their policies will behave correctly before allowing autonomous machines to spend money in the real world. A simulation environment allows policies to be tested against many payment scenarios.

Capabilities:

The simulator should allow users to define a fleet policy and test it against simulated payment requests.

Example policy:

maxSessionSpend: $30  
allowedRails: XRPL  
allowedAssets: RLUSD  
destinations: parking, charging, toll  

Example simulated events:

- parking payment request ($2.50)
- toll payment request ($6.00)
- charging payment request ($18.00)
- unexpected vendor request ($50.00)

The simulator evaluates the MPCP chain:

FleetPolicy → PolicyGrant → BudgetAuthorization → SignedPaymentAuthorization

and reports whether each payment would be allowed or rejected.

Features:

- define fleet policies interactively
- simulate payment requests
- visualize policy enforcement
- show MPCP artifact chain produced for each decision
- demonstrate when and why payments are rejected

Deliverables:

- CLI or small web interface
- example fleet policies
- example payment scenarios
- documentation explaining policy behavior


Purpose:

Help fleet operators and developers **understand and validate MPCP spending guardrails** before deploying them to real autonomous systems. The simulator provides a safe environment to experiment with policies, visualize how MPCP artifact chains are produced, and verify that machines will only authorize payments that comply with fleet constraints. It also serves as an educational reference demonstrating how MPCP enforces policy-driven machine spending.


### PR 8D — Offline Payment Authorization

Add documentation and example flows demonstrating how MPCP enables **offline machine payments** using pre-authorized spending envelopes.

Goal:

Allow autonomous systems (vehicles, robots, devices) to complete payments even when temporary network connectivity is unavailable.

Background:

Autonomous fleets frequently operate in environments where network connectivity may be intermittent or unavailable, such as:

- underground parking garages
- tunnels
- charging facilities
- dense urban environments
- rural infrastructure

Traditional payment systems rely on centralized approval APIs, which prevents transactions from completing when connectivity is lost.

MPCP solves this by allowing machines to hold **pre-authorized spending budgets** that can be used locally.

Example Flow:

Vehicle begins trip with a valid policy chain:

FleetPolicy  
→ PolicyGrant  
→ BudgetAuthorization  

Vehicle enters an underground parking garage where connectivity is unavailable.

Parking meter issues a payment request.

Vehicle evaluates the request locally:

- within authorized budget
- destination allowed
- asset and rail permitted

Vehicle signs a SignedPaymentAuthorization (SPA) and executes the settlement.

Parking system verifies the MPCP artifact chain and allows entry.

Payment succeeds **without contacting any centralized backend service**.

Key Behaviors to Demonstrate:

- local authorization decisions using BudgetAuthorization
- deterministic verification of MPCP artifacts
- successful payment execution during network outage
- later reconciliation once connectivity returns

Deliverables:

- documentation describing offline MPCP payment flows
- extension of the parking demo to simulate offline mode
- example artifact bundle demonstrating offline authorization

Purpose:

Show that MPCP enables **resilient autonomous payments** for machines operating in real-world environments where connectivity cannot always be guaranteed.

---

## PR 9 — Integration Tests

Simulate a full MPCP lifecycle.

Test flow:

fleet policy

→ policy grant

→ budget authorization

→ SPA

→ settlement intent

→ settlement verification

Acceptance Criteria:

- full lifecycle passes verification

---

# Phase 4 — Protocol Network Effects

Goal: Enable MPCP to operate in **multi‑party environments**.

---

## PR 10 — Intent Anchoring

Add optional support for publishing intent hashes to distributed ledgers.

Possible rails:

- Hedera HCS
- XRPL
- EVM

Purpose:

Provide:

- public auditability
- dispute protection
- replay protection

---

## PR 11 — Dispute Verification

Add tooling to verify disputed settlements.

Functions:

verifyDisputedSettlement()

Inputs:

- settlement
- artifacts
- ledger anchor

Output:

verified / invalid

---

## PR 12 — Fleet Operator Tooling

Add features for fleet operators.

Examples:

- fleet policy dashboards
- payment audit trails
- settlement verification logs

---

# Phase 5 — External Adoption & Productionization

Goal: Enable independent implementations, ecosystem adoption, and production deployment of the MPCP protocol.

This phase focuses on turning the MPCP reference implementation into a protocol that can be safely implemented by third parties. It introduces interoperability artifacts, production integrations, deployment profiles, and documentation required for real‑world adoption.

That’s where MPCP stops being “a strong reference implementation” and starts becoming something other teams can adopt safely.

I’d structure it like this:

⸻

PR12A — Artifact Bundle Specification ✓

Define a canonical MPCP **artifact bundle format** used to exchange complete payment verification data between systems. Implemented: `src/schema/artifactBundle.ts`, `doc/protocol/ArtifactBundle.md`.

Example bundle contents:

• policyGrant  
• signedBudgetAuthorization  
• signedPaymentAuthorization  
• settlementIntent  
• settlement  
• optional ledgerAnchor  

Purpose:
• standardize how MPCP artifacts are packaged for verification  
• support dispute resolution workflows  
• enable deterministic protocol test vectors  
• simplify developer tooling and debugging

Deliverables:
• bundle schema definition
• example artifact bundles
• verifier support for bundle inputs

⸻

PR13 — Golden Protocol Vectors

Freeze a set of canonical MPCP test vectors.

Examples:
	•	valid settlement
	•	valid settlement with intent
	•	expired grant
	•	budget exceeded
	•	payment auth mismatch
	•	intent hash mismatch

Purpose:
	•	let other implementations validate compatibility
	•	prevent regressions
	•	create a real interoperability target

This is probably the highest-value next PR.

⸻

PR14 — Real Ledger Anchor Adapters ✓

Move beyond the mock anchor and implement at least one real adapter. Implemented: Hedera HCS adapter (`hederaHcsAnchorIntentHash`, `verifyHederaHcsAnchor`), `verifyDisputedSettlementAsync`. Requires `npm install @hashgraph/sdk`.

Best order:
	•	Hedera HCS
	•	XRPL
	•	EVM later

Purpose:
	•	make anchoring real
	•	support actual dispute/audit workflows
	•	prove MPCP works off-repo

⸻

PR15 — Reference Profiles ✓

Define named MPCP deployment profiles. Implemented: `doc/architecture/REFERENCE_PROFILES.md`, `profiles/` (fleet-offline, parking, charging, hosted-rail), `policy-summary --profile <name>` validation.

Examples:
	•	XRPL Stablecoin Profile
	•	Fleet Offline Profile
	•	Parking Profile
	•	Charging Profile
	•	Hosted Rail Profile

Purpose:
	•	reduce ambiguity
	•	make integration easier
	•	let adopters choose a profile instead of inventing their own rules

This is a big adoption unlock.

⸻

PR16 — Compatibility / Versioning Policy ✓

Add a formal compatibility policy for:
	•	artifact versions
	•	verifier behavior
	•	profile evolution
	•	future extensions

Purpose:
	•	tell implementers what is stable
	•	define how 1.0, 1.1, 2.0 evolve
	•	make MPCP feel like a real protocol standard

Implemented: `doc/architecture/COMPATIBILITY_AND_VERSIONING.md`.

⸻

PR17 — Reference API / Service Layer ✓

You already have protocol + verifier + SDK.
This PR would define a lightweight service facade, like:
	•	issue budget
	•	verify settlement
	•	verify dispute
	•	anchor intent

Purpose:
	•	make MPCP easy for backend teams to adopt
	•	avoid everyone inventing their own wrapper layer

Implemented: `src/service/`, `mpcp-service/service` export, `doc/architecture/REFERENCE_SERVICE_API.md`.

⸻

PR18 — Public Protocol Site / Docs Portal ✓

Turn the docs into something publishable.

Could include:
	•	protocol overview
	•	artifact specs
	•	examples
	•	profiles
	•	vectors
	•	verifier usage

Purpose:
	•	external credibility
	•	onboarding
	•	partner friendliness

Implemented: `docs/` with overview (what-is-mpcp, problem, comparison-with-agent-protocols), protocol (artifacts, hashing, verification, anchoring), guides (build-a-machine-wallet, fleet-payments, dispute-resolution), examples (parking, charging, fleet), reference (sdk, service-api, cli). Comparison doc explains how MPCP differs from x402, AP2.

⸻

PR19 — Documentation Site Deployment ✓

Deploy the docs site so it is publicly accessible (e.g., GitHub Pages). Implemented: `mkdocs.yml`, `docs-requirements.txt`, `.github/workflows/deploy-docs.yml`. Enable GitHub Pages (Settings → Pages → Source: GitHub Actions) to publish.

Purpose:
	•	make docs discoverable
	•	provide a canonical URL for the protocol site
	•	complete the "publishable" goal of PR18

⸻

PR20 — Golden Protocol Vectors ✓

Freeze a set of canonical MPCP test vectors for interoperability and regression testing. Implemented: `vectors/` (manifest.json, valid-settlement.json, expired-grant.json, budget-exceeded.json, intent-hash-mismatch.json, settlement-mismatch.json), `test/vectors/goldenVectors.test.ts`.

Vectors:
	•	valid settlement (with intent hash)
	•	expired grant
	•	budget exceeded
	•	intent hash mismatch
	•	settlement mismatch (payment auth)

Purpose:
	•	let other implementations validate compatibility
	•	prevent regressions
	•	create a real interoperability target

⸻

---

# Phase 6 — Adoption Acceleration

Goal: Turn MPCP from a published protocol into something that is easy to evaluate, explain, and adopt across machine-wallet, fleet, and payment-rail ecosystems.

This phase focuses on visual communication, real-world deployment profiles, and ecosystem positioning so that MPCP can be understood and adopted by external developers, mobility operators, and payment infrastructure teams.

⸻

PR21 — Payment Profiles Expansion

Expand reference profiles so MPCP is immediately usable for real payment ecosystems.

Initial focus:
	•	XRPL Stablecoin Profile
	•	RLUSD / issued-asset payment constraints
	•	wallet and verifier expectations for stablecoin settlement

Future candidates:
	•	Stellar stablecoin profile
	•	Hedera stablecoin profile
	•	EVM stablecoin settlement profile

Purpose:
	•	make MPCP concrete for real settlement rails
	•	reduce ambiguity for implementers
	•	provide a clear starting profile for stablecoin-based machine payments

Deliverables:
	•	profile document(s)
	•	example bundle(s)
	•	verification guidance for each supported profile

⸻

PR22 — Layer-1 Evaluation for Payment Profiles

Research which layer-1 and payment ecosystem should be prioritized next for MPCP deployment profiles beyond XRPL.

Candidate ecosystems:
	•	XRPL
	•	Hedera
	•	Stellar
	•	EVM stablecoin rails

Evaluation criteria:
	•	stablecoin support and issuer ecosystem
	•	payment UX and settlement finality
	•	fees and predictability
	•	compliance / allowlist features
	•	offline and verifier friendliness
	•	developer tooling and integration simplicity

Purpose:
	•	identify the strongest next ecosystem for MPCP adoption
	•	justify profile prioritization with explicit criteria
	•	position MPCP clearly relative to existing payment stacks

Deliverables:
	•	research document comparing candidate ecosystems
	•	recommended next profile target
	•	short rationale for why that ecosystem best fits MPCP

⸻

PR23 — Machine Wallet Guardrails

Document and demonstrate how MPCP acts as a **machine wallet guardrail layer**.

Concept:
A machine wallet should not send funds unless payment requests satisfy:
	•	PolicyGrant constraints
	•	SignedBudgetAuthorization session limits
	•	SignedPaymentAuthorization approval rules

Purpose:
	•	show MPCP as a practical machine-wallet security model
	•	highlight bounded authorization and spend limits
	•	make the protocol attractive to fleet and robotics teams

Deliverables:
	•	doc / guide describing the guardrail model
	•	wallet integration example
	•	threat-model notes for overspend and misuse prevention

⸻

PR24 — Automated Fleet Payment Demo

Create a visual end-to-end demonstration of a real MPCP-controlled fleet payment.

Example flow:
	•	vehicle arrives at charger / parking facility
	•	service requests payment
	•	fleet policy engine issues / validates artifacts
	•	vehicle signs payment authorization
	•	settlement executes
	•	verifier confirms the chain

Purpose:
	•	show a complete real-world machine payment flow
	•	provide a compelling demo for developers, partners, and mobility teams
	•	make MPCP instantly understandable in one scenario

Deliverables:
	•	runnable demo
	•	visual walkthrough
	•	companion documentation and screenshots

⸻

PR25 — MPCP Conformance Badge

Define a lightweight conformance process for external implementations.

Concept:
Implementations that pass MPCP golden vectors and required verification checks may claim compatibility.

Purpose:
	•	enable ecosystem credibility
	•	encourage compatible third-party implementations
	•	create a simple interoperability signal

Deliverables:
	•	conformance criteria
	•	basic badge / claim format
	•	documentation for how external implementations validate compatibility

⸻

PR26 — Human-to-Agent Delegation Profile ✓ Implemented

Extend MPCP to support human DID principals delegating bounded spending authority to AI agents.

Implemented:
- `revocationEndpoint` field on PolicyGrant — human can cancel mid-delegation via wallet service
- `allowedPurposes` field on PolicyGrant — merchant category allowlist (agent-enforced, audit trail)
- `TRIP` budget scope — multi-day/multi-session spending envelopes for travel and project budgets
- `checkRevocation()` SDK utility — async endpoint check; verifier stays stateless and synchronous
- Human-to-agent delegation profile doc (`docs/profiles/human-agent-profile.md`)
- Human-to-agent demo (`examples/human-agent-trip/`) — Alice delegates $800 Paris trip budget to AI agent
- Comparison doc updated with ACP, TAPC, MCP positioning and "Why MPCP for agent spending" section
- `actors.md` updated with AI Agent actor

Known Limitation resolved:
- `revocationEndpoint` is now defined in the spec and reference implementation.
  The MPCP verifier remains stateless; callers perform revocation checks as a separate step.

⸻

# Expected Outcome

After completion of this roadmap MPCP will provide:

- a formal protocol specification
- deterministic artifact hashing
- a reference verifier
- an SDK
- integration examples

This enables MPCP to serve as a **machine‑to‑machine payment control protocol** for autonomous systems.

---

# Long Term Vision

MPCP aims to become a **standard protocol for autonomous machine payments** including:

- autonomous vehicles
- delivery robots
- machine marketplaces
- energy infrastructure

The reference implementation in this repository serves as the foundation for that ecosystem.
