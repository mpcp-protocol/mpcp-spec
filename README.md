# MPCP Specification

**Canonical specification for the Machine Payment Control Protocol (MPCP).**

MPCP defines a cryptographically verifiable authorization chain for machine-to-service payments. This repository contains the protocol specification, architecture documentation, and conceptual guides.

## Contents

- **[docs/](docs/)** — Protocol specification and documentation
  - **overview/** — Problem statement, design goals, what is MPCP
  - **architecture/** — System model, actors, flows
  - **protocol/** — Artifact definitions (PolicyGrant, SBA, SPA, SettlementIntent, etc.)
  - **guides/** — Conceptual guides (machine wallets, fleet payments, dispute resolution)
- **[diagrams/](diagrams/)** — Architecture and flow diagrams
- **[roadmap/](roadmap/)** — Implementation roadmap

## Reference Implementation

The [mpcp-reference](https://github.com/mpcp-protocol/mpcp-reference) repository provides the reference implementation in TypeScript.

## Documentation

- [Specification index](docs/index.md)
- [VERSIONING.md](VERSIONING.md) — Compatibility and versioning policy
- [CONTRIBUTING.md](CONTRIBUTING.md) — How to contribute

## License

MIT — see [LICENSE](LICENSE).
