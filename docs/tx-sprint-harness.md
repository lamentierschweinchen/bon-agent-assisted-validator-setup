# Transaction Sprint Harness

This document describes the public `tx-sprint` helper in [scripts/tx-sprint/tx-sprint](../scripts/tx-sprint/tx-sprint).

The goal is simple: provide a reusable high-throughput `MoveBalance` sender for Challenge 4 style transaction windows without baking in any private wallets, local absolute paths, or one-off manifests.

## What It Does

The harness supports:

1. fresh wallet generation
2. shard-aware distribution
3. same-shard receiver mapping
4. leader-wallet funding plans
5. nonce-aware funding execution
6. high-throughput `MoveBalance` sending
7. short calibration runs
8. structured parameter sweeps
9. post-run reporting from saved artifacts

All generated outputs default under `artifacts/tx-sprint/`, which keeps the repository clean and makes it easier to ignore private run data.

## Why The Topology Looks This Way

The default sender topology is a same-shard ring.

That means:

1. wallets are balanced across shards
2. each sender has one default receiver on the same shard
3. the receiver list wraps around in a ring

This is deliberate.

For simple `MoveBalance` throughput, same-shard traffic removes cross-shard routing overhead, keeps the transaction shape boring, and makes sender-side attribution and recovery easier.

## Operational Lessons Baked Into The Tool

### 1. Submission Count Is Not Success Count

The harness always writes raw batch artifacts before and after submission so that later verification can distinguish:

1. planned
2. accepted by the sender path
3. ambiguous
4. observed on-chain

### 2. Leader Funding Needs Its Own Strategy

Funding hundreds of wallets from one leader account is not the same problem as sending from hundreds of wallets in parallel.

The public harness funds in leader-side waves and, by default, waits for the leader nonce to advance between funding batches. This is safer than blasting all funding transactions at once and hoping the gateway accepts the full pending nonce range.

### 3. Crash-Safe Artifacts Matter

Each run checkpoints:

1. planned batches
2. batch responses
3. per-transaction append-only records
4. blocked sender records
5. run summary state

This lets you recover from partial failures or verification issues without losing the evidence of what was attempted.

## Command Flow

Use the wrapper:

```bash
./scripts/tx-sprint/tx-sprint
```

If your `multiversx_sdk` install lives in the `mxpy` pipx environment, the wrapper should find it automatically. If not, point it explicitly:

```bash
TX_SPRINT_PYTHON=/path/to/python ./scripts/tx-sprint/tx-sprint --help
```

### 1. Generate A Sender Set

```bash
./scripts/tx-sprint/tx-sprint generate-wallets \
  --count 500 \
  --output-dir ./artifacts/tx-sprint/wallet-sets/tx-sprint-500 \
  --prefix sprint
```

### 2. Build A Flat Funding Plan

```bash
./scripts/tx-sprint/tx-sprint plan-funding \
  --manifest ./artifacts/tx-sprint/wallet-sets/tx-sprint-500/manifest.json \
  --amount-egld 0.20 \
  --label initial-funding
```

### 3. Execute Funding In Leader Waves

```bash
./scripts/tx-sprint/tx-sprint fund-wallets \
  --plan ./artifacts/tx-sprint/wallet-sets/tx-sprint-500/plans/INITIAL.json \
  --leader-pem /absolute/path/to/leader.pem \
  --batch-size 100
```

### 4. Run A Short Calibration

```bash
./scripts/tx-sprint/tx-sprint calibrate \
  --manifest ./artifacts/tx-sprint/wallet-sets/tx-sprint-500/manifest.json \
  --wallet-limit 100 \
  --duration-seconds 120 \
  --gas-price 1000000000 \
  --batch-size 250 \
  --num-workers 8 \
  --inflight-nonces-per-sender 32
```

### 5. Run A Full Window

```bash
./scripts/tx-sprint/tx-sprint run-window \
  --manifest ./artifacts/tx-sprint/wallet-sets/tx-sprint-500/manifest.json \
  --duration-seconds 1800 \
  --gas-price 1500000000 \
  --batch-size 500 \
  --num-workers 12 \
  --inflight-nonces-per-sender 64 \
  --budget-egld 2000
```

### 6. Report The Run

```bash
./scripts/tx-sprint/tx-sprint report-run \
  --run-dir ./artifacts/tx-sprint/runs/live/RUN_ID
```

## Tunable Parameters That Actually Matter

The harness is designed around these knobs:

1. `gas_price`
2. `batch_size`
3. `num_workers`
4. `inflight_nonces_per_sender`
5. sender shard distribution

In practice:

1. increase `gas_price` when the network is contested and you need better inclusion priority
2. reduce `batch_size` first if the gateway starts returning partial or ambiguous results
3. reduce `num_workers` second if ambiguity persists
4. reduce `inflight_nonces_per_sender` only after the first two changes fail to stabilize the sender path

## Measured Example

One BoN test run using this architecture reached:

1. `500` senders
2. same-shard ring topology
3. `gas_price=1_500_000_000`
4. `batch_size=500`
5. `num_workers=12`
6. `inflight_nonces_per_sender=64`

Observed sender-side result:

1. `1,000,000` clean accepted transactions
2. `0` ambiguous batches
3. `0` blocked senders
4. `570s` submission span

Treat that as a useful benchmark, not a guarantee. The right live configuration still depends on whether the network is quiet or heavily contested during the official window.

## Environment Variables

These let you reuse the tool without editing source:

1. `TX_SPRINT_ROOT`
2. `TX_SPRINT_PYTHON`
3. `TX_SPRINT_MXPY`
4. `TX_SPRINT_CHAIN_ID`
5. `TX_SPRINT_GATEWAY`
6. `TX_SPRINT_API`

The defaults are set for the Battle of Nodes environment because this repository is BoN-focused, but every endpoint and output root can be overridden.
