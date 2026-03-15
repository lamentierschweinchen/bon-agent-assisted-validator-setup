# Verification Checklist

Use this checklist after the agent finishes the initial setup.

## On-Chain Proof

The following must be true:

1. provider creation transaction succeeded
2. provider metadata transaction succeeded
3. provider name contains `BoN`
4. add-nodes transaction succeeded
5. delegate top-up transaction succeeded
6. provider stake reached at least `2500 EGLD`
7. stake-nodes transaction succeeded

## Community Delegation Proof

If the task is specifically the existing MultiversX Community Delegation, use [community-delegation-task.md](community-delegation-task.md).

The proven BoN-specific checks were:

1. send the transaction to `erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt`
2. use `data = stake`
3. use `value = 10000000000000000000`
4. verify transaction status is `success`
5. verify `getUserStake(addr:<wallet>)` on that contract returns a nonzero amount

## Required Artifacts

Keep:

1. transaction hashes
2. signed JSON outputs or command outputs
3. the resolved delegation contract address
4. the BLS public key

Useful checks:

- `mxpy staking-provider get-contract-address --proxy https://api.battleofnodes.com --create-tx-hash <HASH>`
- `curl -sS https://api.battleofnodes.com/transactions/<HASH>?withResults=true`
- `curl -sS https://api.battleofnodes.com/accounts/<BECH32>`

## Node Proof

The following must be true:

1. the node process or systemd service is running
2. the node display name contains `BoN`
3. logs show the BoN version string
4. logs show `trie sync in progress`
5. the node later exits bootstrap and serves heartbeat/status normally

## Local API Checks

```bash
curl -sS -i http://127.0.0.1:8080/node/status
curl -sS -i http://127.0.0.1:8080/node/heartbeatstatus
```

Interpretation:

- `{"error":"node is starting"}` means bootstrap is still in progress
- a structured JSON response means the node API is ready

## Common Failure Modes

1. Wrong amount units on `create-new-delegation-contract`
   - On BoN, the proven working `--value` form was atomic units, not plain `1250`

2. Correct provider, wrong node name
   - provider metadata does not set the running node display name
   - `NodeDisplayName` or `--display-name` must also contain `BoN`

3. Waiting forever for final proof
   - the node may be healthy but still bootstrapping
   - logs with `trie sync in progress` are good
   - use a snapshot if time matters

4. Manual BLS-signature dead end
   - do not generate the `addNodes` signature by hand if `mxpy` can do it from `--validators-pem`

## Done State

The initial setup is done when:

1. the provider exists on BoN
2. the provider and node names both include `BoN`
3. the node is added and staked
4. the node is running on BoN with the BoN version
5. proof artifacts are saved

---

## Challenge 2 Verification

Use this section after completing Challenge 2 tasks 1 through 5.

For the full task sequence and commands, see [challenge-2-playbook.md](challenge-2-playbook.md).

### Per-Task Proof Requirements

For every task, verify and record:

1. the exact receiver contract or provider address
2. the exact function name or data field
3. the exact encoded amount or parameter
4. transaction status is `success` on-chain
5. the follow-up state query from the correct source (contract query, not only API)

### Task 1: Community Delegation

- receiver: `erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt`
- data: `stake`
- value: `10000000000000000000`
- `getUserStake` query returns `10000000000000000000`

Note: if the API query `getUserActiveStake` returns empty on this contract, use `getUserStake` instead.

### Task 2: Self-Delegation

- receiver: your own staking provider contract
- value: `10000000000000000000`
- transaction status: `success`
- confirm provider capacity was available before the transaction (cap check)

### Task 3: Undelegation

- receiver: your own staking provider contract
- function: `unDelegate`
- value: `1000000000000000000`
- transaction status: `success`
- funds may not appear as spendable balance immediately — the `unDelegate` tx hash is the proof, not the balance change

### Task 4: Service Fee Change

- transaction status: `success`
- `getServiceFee` contract query returns `789`
- human form: `7.89%`, encoded form: `789`
- if the provider API shows a stale fee, the contract query is the authoritative proof source

### Task 5: Governance Vote

- transaction status: `success`
- proposal ID voted on
- vote option cast
- saved evidence that the proposal was still active at time of vote

### Challenge 2 Done State

Challenge 2 is complete when:

1. community delegation tx confirmed with correct receiver, data, and value
2. self-delegation tx confirmed with correct provider and amount
3. undelegation tx confirmed with correct provider and amount
4. service fee change confirmed — `getServiceFee` returns `789`
5. governance vote confirmed against an active proposal
6. proof bundle saved for all five tasks

---

## Challenge 3 Verification

Use this section after completing the backup-node, restart-drill, and log-upload tasks.

### Backup Node Proof

Verify and record:

1. main and backup nodes are both registered under the same provider
2. main and backup names follow the required pattern with `BoN` before the numeric suffix
3. live heartbeat shows both names active
4. provider contract or equivalent direct state query confirms the backup node exists even if a summary API lags

### Restart Drill Proof

Verify and record:

1. primary node stopped for the required downtime
2. old log ends with graceful shutdown
3. new log begins with startup after the required delay
4. post-restart node returned to synced and active state

### Log Upload Proof

Verify and record:

1. uploaded archive contains a backup-node log
2. uploaded archive contains `trie sync in progress`
3. uploaded archive contains `generated BLS private key for redundancy handler`
4. exact submitted archive is preserved locally

### Challenge 3 Done State

Challenge 3 is complete when:

1. backup node is live under the same provider with the correct naming pattern
2. controlled restart drill is proven by real logs
3. uploaded archive contains the required backup and trie-sync evidence
4. the proof bundle is saved locally

---

## Challenge 4 Stress Window Verification

Use this section after completing one or more live stress windows.

### Pre-Window Checks

Before launching a workload, verify:

1. official window start and end time
2. current funded challenge-address set and its attribution path back to the registered wallet
3. main validator is healthy if the page requires node restarts around the window
4. run artifacts will be written incrementally during the send loop

### Any `MoveBalance` Window

Verify and record:

1. sender addresses are challenge addresses funded from the registered wallet
2. sender and receiver satisfy the required shard relationship for that window
3. submitted run artifacts exist even if the sender path times out
4. actual on-chain success count is measured after the run

### Any DEX Window

Verify and record:

1. target contract or pool matches the live task
2. function and token-transfer shape match the live task
3. submitted run artifacts exist and include transaction hashes
4. actual on-chain success count is measured after the run

### Any Relayed Window

Verify and record:

1. relayer-paid fee path matches the live task
2. sender and relayer roles are captured in the proof artifacts
3. relayed transaction encoding was tested before the official window
4. follow-up success checks are measured from the saved run artifacts

### Infrastructure And Log Proof

Verify and record:

1. any required pre-window and post-window main-node restarts were actually performed
2. the main validator log segment covering the stress window was preserved
3. the exact uploaded log bundle is kept separately from runtime folders

### Interpretation Rules

1. `submitted` is not the same as `success`
2. gateway or sender timeouts do not automatically mean the workload failed
3. if a verifier tool returns `unknown` because of local environment restrictions, rerun the status pass from an unrestricted environment before sending unnecessary recovery load
4. use success shortfall, not submission count alone, to decide whether another chunk is needed

### Challenge 4 Done State

Challenge 4 is complete when:

1. each qualifying window workload was sent inside its official time window and attributed correctly
2. per-window run artifacts are saved
3. on-chain success counts have been measured or can be measured from the saved artifacts
4. any required restart and log-upload proof is preserved
