# Challenge 2 Playbook

This playbook covers Battle of Nodes Challenge 2, tasks 1 through 5.

It is written for any AI agent on any operating system. `mxpy` commands are examples. If your toolchain differs, apply the same transaction shapes and verification logic.

## Scope

Challenge 2 tests five distinct on-chain behaviors. Do not treat them as one repeated delegation action.

| Task | Action | Key Risk |
|------|--------|----------|
| 1 | Stake 10 EGLD into the MultiversX Community Delegation | Legacy contract — different call shape from normal provider delegation |
| 2 | Delegate 10 EGLD to your own staking provider | Provider delegation cap may already be full |
| 3 | Undelegate 1 EGLD from your own provider | Proof is the `unDelegate` tx, not the eventual withdrawal |
| 4 | Change provider service fee to 7.89% | Fee is a scaled integer on-chain, not a decimal |
| 5 | Vote on an active BoN governance proposal | Requires a live proposal and staking power from earlier tasks |

## Prerequisites

- Operator wallet accessible to the agent
- Staking provider created and funded with at least 2500 EGLD (Challenge 1 complete)
- `mxpy` or equivalent SDK available
- Chain: `B`, proxy: `https://api.battleofnodes.com`

## Preflight Checks Before Every Task

1. Confirm wallet balance covers the transfer plus gas.
2. Identify the exact target contract or provider from live network state, not from memory.
3. Confirm the target is still active (critical for Task 5).
4. Save proof immediately after each transaction confirms. Do not reconstruct it later.

## Task 1: MultiversX Community Delegation

**Do not use `mxpy staking-provider delegate` for this task.**

The MultiversX Community Delegation on BoN is a legacy delegation contract. It uses a different call path from a normal staking provider.

See [community-delegation-task.md](community-delegation-task.md) for contract discovery and the full proven call shape.

**Quick reference:**

- Target contract: `erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt`
- Data field: `stake`
- Value: `10000000000000000000` (10 EGLD in atomic units)

**Proof:**

- Transaction hash with status `success`
- `getUserStake` query on the community contract returns `10000000000000000000`

## Task 2: Self-Delegation

Delegate 10 EGLD to your own staking provider.

**Preflight: verify the provider has remaining delegation capacity before sending.**

If `totalActiveStake` already equals `maxDelegationCap`, the transaction will fail even with a funded wallet.

Check provider state:

```
GET https://api.battleofnodes.com/providers/<YOUR_PROVIDER_ADDRESS>
```

If the cap is full, raise it first:

```bash
mxpy staking-provider modify-total-delegation-cap \
  --proxy "https://api.battleofnodes.com" \
  --pem "/absolute/path/operator-wallet.pem" \
  --chain "B" \
  --delegation-contract "<YOUR_PROVIDER_ADDRESS>" \
  --new-max-delegation-cap <NEW_CAP_IN_EGLD> \
  --send \
  --outfile modify-cap-live.json
```

Then delegate:

```bash
mxpy staking-provider delegate \
  --proxy "https://api.battleofnodes.com" \
  --pem "/absolute/path/operator-wallet.pem" \
  --chain "B" \
  --delegation-contract "<YOUR_PROVIDER_ADDRESS>" \
  --value 10000000000000000000 \
  --send \
  --outfile self-delegate-live.json
```

**Proof:**

- Transaction hash with status `success`
- `value = 10000000000000000000`
- Receiver is your own provider contract

## Task 3: Undelegate

Undelegate 1 EGLD from your own staking provider.

**Important:** undelegated funds enter an unbonding period. They do not appear as spendable balance immediately. The proof for this task is the `unDelegate` transaction itself, not the later withdrawal.

```bash
mxpy staking-provider un-delegate \
  --proxy "https://api.battleofnodes.com" \
  --pem "/absolute/path/operator-wallet.pem" \
  --chain "B" \
  --delegation-contract "<YOUR_PROVIDER_ADDRESS>" \
  --value 1000000000000000000 \
  --send \
  --outfile undelegate-live.json
```

**Proof:**

- Transaction hash with status `success`
- `value = 1000000000000000000` (1 EGLD)
- Receiver is your own provider contract

Do not wait for the unbonding period to end. That is a separate later operation and is not required to complete this task.

## Task 4: Change Service Fee

Change your provider's service fee to 7.89%.

**Encoding:** service fees are stored as scaled integers. The on-chain representation of 7.89% is `789` (percentage × 100, two decimal places).

```bash
mxpy staking-provider change-service-fee \
  --proxy "https://api.battleofnodes.com" \
  --pem "/absolute/path/operator-wallet.pem" \
  --chain "B" \
  --delegation-contract "<YOUR_PROVIDER_ADDRESS>" \
  --new-service-fee 789 \
  --send \
  --outfile change-fee-live.json
```

**Verification:** provider-facing APIs can lag after a fee change. If the API still shows the old fee, query the contract directly:

```bash
mxpy contract query "<YOUR_PROVIDER_ADDRESS>" \
  --proxy "https://api.battleofnodes.com" \
  --function "getServiceFee"
```

Expected return value: `789`

Use the contract query as the authoritative proof source if the API and contract disagree.

**Proof:**

- Transaction hash with status `success`
- `getServiceFee` query returns `789`
- Record both forms: human value `7.89%`, encoded value `789`

## Task 5: Governance Vote

Vote on an active BoN governance proposal.

**Two conditions must be true before voting:**

1. An active proposal exists on BoN.
2. Your wallet has voting power from staking established in earlier tasks.

**Preflight:**

Check for active proposals:

```
GET https://api.battleofnodes.com/governance/proposals?status=Active
```

If no proposals are active, you cannot vote. Do not send a vote transaction against a closed or nonexistent proposal.

Verify your staking power by checking your delegation balance before sending.

**Vote transaction:**

The exact receiver contract, proposal ID, and argument encoding depend on live network state. Retrieve both from the BoN API or network config before building the transaction. Do not hardcode values that may change between rounds.

General shape:

- Receiver: BoN governance contract address (retrieve from network config or live API)
- Function: `vote` with encoded proposal ID and vote option as arguments
- Value: `0`

**Proof:**

- Transaction hash with status `success`
- Proposal ID voted on
- Vote option cast
- Saved API response confirming the proposal was still active at time of vote

## Common Failure Modes

| Failure | Cause | Fix |
|---------|-------|-----|
| Task 1 has wrong effect or fails | Used `delegate` instead of `stake` on legacy contract | Send raw tx with `data = stake` directly to the community contract |
| Task 2 fails with delegation cap error | Provider cap was already full | Check `maxDelegationCap` and raise it before delegating |
| Task 3 funds not visible in wallet | Normal — unbonding period in effect | Proof is the `unDelegate` tx hash, not the balance change |
| Task 4 API shows old fee after change | Indexer lag | Query contract directly with `getServiceFee` |
| Task 5 vote fails or has no effect | Proposal expired, or wallet has no staking power | Check proposal status and delegation balance before sending |

## Proof Bundle Per Task

Collect and save these immediately after each task:

| Task | Required proof |
|------|----------------|
| 1 | tx hash · receiver = community contract · data = `stake` · value = `10000000000000000000` · `getUserStake` query result |
| 2 | tx hash · receiver = your provider · value = `10000000000000000000` · provider state after delegation |
| 3 | tx hash · receiver = your provider · function = `unDelegate` · value = `1000000000000000000` |
| 4 | tx hash · `getServiceFee` result = `789` · human label = `7.89%` |
| 5 | tx hash · proposal ID · vote option · saved proposal status at time of vote |
