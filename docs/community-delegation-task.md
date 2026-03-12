# Community Delegation Task

This note captures the proven BoN flow for the challenge that requires staking to the existing MultiversX Community Delegation.

## What Was Confusing

The challenge wording mixed two different models:

1. It said to "delegate to the existing MultiversX Community Delegation on the BoN shadow fork".
2. It also said to "choose any active legacy staking provider on BoN".

Those are not the same path.

The generic provider flow uses a provider contract from `/providers` and the normal `delegate` call.

The MultiversX Community Delegation on BoN is a legacy delegation contract and uses `stake`, not `delegate`.

## Proven Community Contract

- Identity endpoint:
  - `https://api.battleofnodes.com/identities?size=200&from=0`
  - entry: `identity = "multiversx"`
  - name: `MultiversX Community Delegation 🎖`
- Community identity owner exposed by nodes endpoint:
  - `https://api.battleofnodes.com/nodes?identity=multiversx&size=500&from=0`
  - unique owner: `erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt`

Treat this address as the BoN MultiversX Community Delegation legacy contract:

- `erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt`

## Proven Call Shape

Do not use `mxpy staking-provider delegate` for this task.

The live contract transaction pattern was:

- receiver: `erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt`
- data: `stake`
- value: `10000000000000000000`

Proven command:

```bash
mxpy tx new \
  --proxy 'https://api.battleofnodes.com' \
  --pem '/absolute/path/operator-wallet.pem' \
  --receiver 'erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt' \
  --value '10000000000000000000' \
  --data 'stake' \
  --chain 'B' \
  --send \
  --outfile stake-10-egld-multiversx-community.json
```

## Proof Method

For this legacy contract, the useful query is `getUserStake`.

`getUserActiveStake` returned empty on this contract during testing, so do not rely on it here.

Query:

```bash
mxpy contract query \
  'erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt' \
  --proxy 'https://api.battleofnodes.com' \
  --function 'getUserStake' \
  --arguments 'addr:<YOUR_OPERATOR_ADDRESS>'
```

Example successful return:

```text
[
    "8ac7230489e80000"
]
```

That hex value is:

- `10000000000000000000`
- exactly `10 EGLD`

## Reference Transaction

This is a call-shape reference. Look it up on the BoN explorer to confirm the exact transaction structure that satisfies this task.

- Sender:
  - `<YOUR_OPERATOR_ADDRESS>`
- Receiver:
  - `erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt`
- Tx hash (call-shape reference):
  - `3e8a0a5b0955cbe97a61e322284b7f0afb13facdcffc09e4ab7d1a337842e65b`
- Value:
  - `10000000000000000000`
- Data:
  - `stake`
- Status:
  - `success`

## Important Notes

1. The normal BoN provider list under `/providers` does not make this path obvious.
2. The Community Delegation identity is visible under `/identities`, but the contract address had to be derived through the `nodes?identity=multiversx` owner field.
3. If you already sent `10 EGLD` to a regular provider using `delegate`, that does not satisfy the stricter "MultiversX Community Delegation specifically" interpretation.
4. For this task, the challenge title mattered more than the generic provider wording.
