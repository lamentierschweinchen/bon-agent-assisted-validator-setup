# Battle of Nodes — Agent Guide

Complete the MultiversX [Battle of Nodes](https://bon.multiversx.com/) challenges
using an AI agent. The agent handles on-chain setup, node operations, stress windows,
and proof collection. You handle wallet funding and optionally provisioning a server.

## How to start

**If you are an agent**, open [AGENT-START-HERE.md](AGENT-START-HERE.md).

**If you are a human**, point your agent at `AGENT-START-HERE.md` with:

> Read AGENT-START-HERE.md and execute the BoN challenges end to end.
> Pause only for wallet creation, wallet funding, missing keys,
> or server provisioning.

## What this covers

**Challenge 1 — validator setup:**

1. Operator wallet creation or import
2. Validator key creation or import
3. BoN on-chain provider and staking setup
4. Local node path (laptop or terminal)
5. Hosted Ubuntu node path (server)
6. Verification and proof collection

**Challenge 2 — post-validator on-chain tasks:**

7. Community delegation (legacy contract path)
8. Self-delegation with delegation cap checks
9. Undelegation and unbonding
10. Service fee change with contract-level verification
11. Governance vote with proposal freshness checks

**Challenge 3 — validator operations and proof:**

12. Backup node registration and naming
13. Controlled restart drill with real downtime
14. Log-upload strategy for trie sync and redundancy proof

**Challenge 4 — live stress windows:**

15. High-volume intra-shard `MoveBalance`
16. DEX swap load with retry-safe artifacts
17. Cross-shard and relayed workloads
18. Attribution, time-window, restart, and verification traps
19. A reusable transaction sprint harness for large `MoveBalance` windows

## Prerequisites

- [`mxpy`](https://docs.multiversx.com/sdk-and-tools/mxpy/installing-mxpy/) installed
- A funded operator wallet (~2500 EGLD for staking plus gas)
- Optional: an Ubuntu 22.04+ server for a durable validator node

## Challenge 4 Helper

For Challenge 4 style throughput work, the repository now includes a public, generic transaction sprint helper:

- doc: [docs/tx-sprint-harness.md](docs/tx-sprint-harness.md)
- wrapper: [scripts/tx-sprint/tx-sprint](scripts/tx-sprint/tx-sprint)

It is designed for same-shard `MoveBalance` stress windows, crash-safe artifact capture, leader-side funding waves, and quick calibration of gas price, batch size, worker count, and inflight nonce depth.
