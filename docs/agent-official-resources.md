# Official Resources For Agents

This is the external resource index for the BoN validator setup. Every link here is either official MultiversX documentation, an official repo, or a BoN endpoint that proved relevant in practice.

## Competition

- [Battle of Nodes](https://bon.multiversx.com/)
  - challenge overview
  - naming rules
  - validator track context

## On-Chain Provider Setup

- [Staking Providers / Delegation Manager](https://docs.multiversx.com/validators/delegation-manager/)
  - provider lifecycle
  - `createNewDelegationContract`
  - `setMetaData`
  - `addNodes`
  - `stakeNodes`

- [Metadata section](https://docs.multiversx.com/validators/delegation-manager/#metadata)
  - naming and metadata fields

- [mxpy CLI](https://docs.multiversx.com/sdk-and-tools/mxpy/mxpy-cli/)
  - wallet commands
  - transaction signing
  - staking-provider subcommands

## Wallets And Keys

- [Validator keys](https://docs.multiversx.com/validators/key-management/validator-keys/)
  - validator key generation
  - fresh validator key path

- [mxpy wallet commands](https://docs.multiversx.com/sdk-and-tools/mxpy/mxpy-cli/#creating-wallets)
  - `wallet new`
  - `wallet convert`

## Node Operations

- [Manage a validator node](https://docs.multiversx.com/validators/nodes-scripts/manage-node/)
  - operational node lifecycle

- [System requirements](https://docs.multiversx.com/validators/system-requirements/)
  - hardware baseline

- [mx-chain-scripts](https://github.com/multiversx/mx-chain-scripts)
  - official install/update/start flow for Ubuntu

## Source Build / Native Local Path

- [mx-chain-go](https://github.com/multiversx/mx-chain-go)
  - source build path
  - native binary

- [mx-chain-mainnet-config](https://github.com/multiversx/mx-chain-mainnet-config)
  - config bundle
  - BoN override tag

## BoN Runtime Endpoints

- [BoN API root](https://api.battleofnodes.com/)
- [BoN network config](https://api.battleofnodes.com/network/config)

The following endpoint patterns are useful later:

- `GET /accounts/<bech32>`
- `GET /transactions/<hash>?withResults=true`
- local node:
  - `http://127.0.0.1:8080/node/status`
  - `http://127.0.0.1:8080/node/heartbeatstatus`

## Snapshots And Docker

- [BoN shard snapshots](https://shadowfork-running-archives.fra1.digitaloceanspaces.com/shadowfork-bon/10-Mar-2026-14-03/)
  - optional sync acceleration

- [BoN Docker image](https://hub.docker.com/layers/multiversx/chain-mainnet/v1.11.0.3-bon/images/sha256-b1fdd9de01cb35ddffbdb7c549f6ac722e76f515a615b92155cea231fe7e9b2f)
  - optional container path if the operator chooses Docker instead of native build or `mx-chain-scripts`

## AI Skills For Agents

Optional skill packages that give an agent sharper MultiversX context. Useful before C2–C4 work involving SDK transactions, ESDT, or DEX calls.

- [multiversx/mx-ai-skills](https://github.com/multiversx/mx-ai-skills) — official MultiversX skill set (smart contracts, sdk-dapp, protocol internals, auditing)
- [michavie/mx-ai-skills](https://github.com/michavie/mx-ai-skills) — community complement (contracts, frontend, backend SDKs, protocol architecture)

See [agent-skills.md](agent-skills.md) for install instructions and BoN-specific relevance notes.

## Local Workspace References

These are not official docs, but they are the most useful local references in this workspace:

- [README.md](../README.md)
- [finding-values.md](finding-values.md)
- [machine-checklist.md](machine-checklist.md)
