# Battle of Nodes Agent Handoff

This document is the entry point for an agent that needs to replicate the initial Battle of Nodes validator setup with minimal user help.

If you are the agent, read this file first, then open the linked Markdown files in the order listed below. Do not start by improvising from generic MultiversX docs. This repository captures the BoN-specific details and the command paths that were validated in practice.

## Challenge 1 Goal

Complete the initial BoN validator setup:

1. Create or import an operator wallet.
2. Create or import a validator key.
3. Create a staking provider on the BoN network.
4. Set provider metadata so the name contains `BoN`.
5. Add the node to the provider.
6. Ensure the provider holds at least `2500 EGLD`.
7. Stake the node.
8. Start a BoN node with a node name containing `BoN`.
9. Collect proof artifacts for both on-chain setup and node runtime.

## Challenge 2 Goal

Complete five distinct on-chain tasks on top of the existing validator setup:

1. Stake 10 EGLD into the MultiversX Community Delegation on BoN.
2. Delegate 10 EGLD to your own staking provider.
3. Undelegate 1 EGLD from your own provider.
4. Change your provider service fee to 7.89%.
5. Vote on an active BoN governance proposal.

Start at [docs/challenge-2-playbook.md](docs/challenge-2-playbook.md).

## Challenge 3 Goal

Complete the validator-operations challenge on top of the existing provider:

1. register and run a backup node under the same provider
2. rename main and backup nodes to the required `BoN` naming pattern
3. complete the controlled restart drill with real downtime
4. upload the required backup and trie-sync logs

Start with [docs/challenge-3-learnings.md](docs/challenge-3-learnings.md).

## Challenge 4 Goal

Prepare and execute live BoN stress windows:

1. high-volume `MoveBalance`
2. DEX smart contract calls
3. cross-shard transaction windows
4. relayed `MoveBalance` windows
5. relayed DEX smart contract call windows

Treat each official window as a separate workload with separate sender attribution, proof, recovery, and post-window log handling.

Start with [docs/stress-window-learnings.md](docs/stress-window-learnings.md).

If the current stress task is primarily a high-volume `MoveBalance` sender challenge, also open [docs/tx-sprint-harness.md](docs/tx-sprint-harness.md).

## Read Order

**Challenge 1 — initial validator setup:**

1. [docs/bon-network-reference.md](docs/bon-network-reference.md)
2. [docs/agent-manual-steps.md](docs/agent-manual-steps.md)
3. [docs/agent-onchain-sequence.md](docs/agent-onchain-sequence.md)
4. [docs/agent-official-resources.md](docs/agent-official-resources.md)
5. [docs/agent-node-local.md](docs/agent-node-local.md)
6. [docs/agent-node-hosted.md](docs/agent-node-hosted.md)
7. [docs/agent-verification-checklist.md](docs/agent-verification-checklist.md)

**Challenge 2 — delegation, undelegation, service fee, governance:**

8. [docs/challenge-2-playbook.md](docs/challenge-2-playbook.md)
9. [docs/community-delegation-task.md](docs/community-delegation-task.md) (Task 1 deep dive)
10. [docs/challenge-2-learnings.md](docs/challenge-2-learnings.md) (cross-task patterns and traps)

**Challenge 3 — backup nodes, restart drill, log upload:**

11. [docs/challenge-3-learnings.md](docs/challenge-3-learnings.md)

**Challenge 4 — live stress windows:**

12. [docs/stress-window-learnings.md](docs/stress-window-learnings.md)
13. [docs/tx-sprint-harness.md](docs/tx-sprint-harness.md)

Then inspect these workspace helpers before taking action:

1. [scripts/run-laptop-dry-run.sh](scripts/run-laptop-dry-run.sh)
2. [scripts/extract-bls-pubkey.sh](scripts/extract-bls-pubkey.sh)
3. [scripts/build-provider-txs.sh](scripts/build-provider-txs.sh)
4. [scripts/build-add-node-tx.sh](scripts/build-add-node-tx.sh)
5. [node-challenge/install-bon-node.sh](node-challenge/install-bon-node.sh)
6. [node-challenge/verify-bon-node.sh](node-challenge/verify-bon-node.sh)
7. [scripts/tx-sprint/tx-sprint](scripts/tx-sprint/tx-sprint)

## Agent Rules

1. Prefer the workspace scripts and proven command paths over rewriting everything from scratch.
2. Treat the BoN network as chain `B` and use `https://api.battleofnodes.com` unless a newer official BoN instruction overrides it.
3. Ensure both the provider name and the running node display name contain `BoN`, preferably as a suffix.
4. Use official MultiversX docs and repos as the primary external sources.
5. Minimize user interruptions. The only normal pause points are:
   - no wallet exists yet
   - the wallet is unfunded
   - no validator key exists yet
   - a real hosted server is needed and has not been provisioned
6. Do not ask the user to calculate BLS signatures manually. `mxpy staking-provider add-nodes --validators-pem ...` handles that.

## BoN Values That Matter

- Chain ID: `B`
- API / proxy: `https://api.battleofnodes.com`
- `mx-chain-scripts` variables:
  - `ENVIRONMENT="mainnet"`
  - `OVERRIDE_CONFIGVER="v1.11.0.3-bon"`
  - `NODE_EXTRA_FLAGS="-log-save"`
- Naming requirement:
  - provider name contains `BoN`
  - node display name contains `BoN`

## Decision Tree

### Option A: Local terminal-only setup

Use this when:

- the goal is to prove setup from a laptop or local terminal
- there is no Ubuntu host yet
- the agent needs to validate the flow end to end before moving to a server

Path:

1. Complete the on-chain provider steps.
2. Build and run the native node locally.
3. Wait for sync or restore a snapshot if time matters.

Use [docs/agent-node-local.md](docs/agent-node-local.md).

### Option B: Real hosted validator node

Use this when:

- the goal is durable uptime
- the challenge requires a stable synced node and heartbeat
- an Ubuntu server is available

Path:

1. Complete the on-chain provider steps.
2. Install the BoN node with `mx-chain-scripts`.
3. Verify service state, heartbeat, logs, and sync.

Use [docs/agent-node-hosted.md](docs/agent-node-hosted.md).

## Minimal End-to-End Workflow

1. Check whether the workspace already contains an operator wallet PEM and a validator PEM.
2. If not, stop at [docs/agent-manual-steps.md](docs/agent-manual-steps.md) and request only the missing prerequisite.
3. Extract the BLS public key with [scripts/extract-bls-pubkey.sh](scripts/extract-bls-pubkey.sh).
4. Build the provider-creation and staking transactions with `mxpy` or the local scripts.
5. Send `create-new-delegation-contract`.
6. Resolve the new delegation contract address using `mxpy staking-provider get-contract-address`.
7. Send `set-metadata`.
8. Send `delegate` to reach at least `2500 EGLD` total.
9. Send `add-nodes`.
10. Send `stake-nodes`.
11. Start the node using either the local or hosted path.
12. Collect verification artifacts.

## Proven BoN-Specific On-Chain Notes

These were the most important live findings from this workspace and should be treated as operational facts unless BoN changes its rules:

1. `mxpy staking-provider create-new-delegation-contract --value` behaved as an atomic-unit field on BoN.
2. The proven working create/top-up split for `2500 EGLD` total stake was:
   - create provider: `1252000000000000000000`
   - top up delegate: `1248000000000000000000`
3. `--total-delegation-cap 2500` remained in human EGLD units when used with `mxpy`.
4. `add-nodes` worked directly from `validatorKey.pem`; no separate BLS signing utility was needed.
5. The separate "MultiversX Community Delegation" task on BoN used a legacy delegation contract and a raw `stake` transaction, not the normal staking-provider `delegate` command.

Do not hide those details behind generic docs. They are the difference between a plausible runbook and one that actually works.

## Suggested Prompts For Another Agent

**Challenge 1:**

`Read AGENT-START-HERE.md in the Battle of Nodes workspace and execute the initial BoN validator setup end to end. Use the local scripts and linked docs first. Minimize manual steps and pause only for wallet creation, wallet funding, missing keys, or hosted server provisioning.`

**Challenge 2:**

`Read AGENT-START-HERE.md in the Battle of Nodes workspace, then open docs/challenge-2-playbook.md and execute Challenge 2 tasks 1 through 5. Collect proof for each task immediately after execution. Pause only if a wallet is unfunded or no active governance proposal exists.`

**Challenge 3:**

`Read AGENT-START-HERE.md in the Battle of Nodes workspace, then open docs/challenge-3-learnings.md and execute the backup-node, restart-drill, and log-upload tasks. Optimize for accepted proof surfaces: naming, heartbeat, real restart logs, and required uploaded log phrases.`

**Challenge 4:**

`Read AGENT-START-HERE.md in the Battle of Nodes workspace, then open docs/stress-window-learnings.md and execute the live stress windows. Prepare retry-safe tooling, preserve incremental run artifacts, use fresh attributed sender sets per window, and verify on-chain success counts before deciding whether to top up.`
