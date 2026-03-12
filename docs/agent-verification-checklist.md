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
