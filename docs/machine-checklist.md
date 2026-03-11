# Machine checklist

## For a real validator machine

Current MultiversX guidance for a production node is roughly:

- `4 dedicated CPUs`
- `8 GB RAM` minimum
- `200 GB SSD`
- stable `100 Mbit/s` connectivity

For safety, I would target:

- `4 vCPU`
- `16 GB RAM`
- `250 GB gp3` or better SSD
- a dedicated machine, not shared with other workloads

## Common under-spec examples

- `2 vCPU` / `8 GiB` instances (e.g. `t3.large`, `m7i.large`) miss the `4 CPU` floor and should not be used for a production validator, especially when shared with other workloads.

## Laptop dry run

A laptop is fine for:

- learning the install flow
- generating or inspecting `validatorKey.pem`
- building transaction payloads
- running an observer temporarily

A laptop is not fine for:

- real validator uptime
- networking reliability
- long-running participation while sleeping or roaming

## Minimum manual checks before staking

- the node starts cleanly
- the node is syncing
- you know where `validatorKey.pem` is stored
- you extracted the correct BLS public key
- the staking provider contract address is recorded
- the provider metadata name ends with `BoN`
- at least `2500 EGLD` is in the provider before `stakeNodes`
