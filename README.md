# Battle of Nodes Validator Setup — Agent Guide

Set up a MultiversX [Battle of Nodes](https://bon.multiversx.com/) validator
using an AI agent. The agent handles the on-chain setup, node installation,
and verification. You handle wallet funding and optionally provisioning a server.

## How to start

**If you are an agent**, open [AGENT-START-HERE.md](AGENT-START-HERE.md).

**If you are a human**, point your agent at `AGENT-START-HERE.md` with:

> Read AGENT-START-HERE.md and execute the initial BoN validator setup
> end to end. Pause only for wallet creation, wallet funding, missing keys,
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

## Prerequisites

- [`mxpy`](https://docs.multiversx.com/sdk-and-tools/mxpy/installing-mxpy/) installed
- A funded operator wallet (~2500 EGLD for staking plus gas)
- Optional: an Ubuntu 22.04+ server for a durable validator node
