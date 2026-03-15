# Stress Window Learnings

This document captures the durable lessons from Battle of Nodes live stress-window challenges.

It is written for any AI agent on any operating system.

The goal is not to preserve one dated event schedule. The goal is to document how to prepare, execute, recover, verify, and package proof during timed transaction-load challenges on BoN.

## What Live Stress Challenges Actually Test

A stress challenge is not only about sending a lot of transactions.

In practice, it usually tests several things at once:

1. time-window discipline
2. transaction attribution through the correct funded addresses
3. sender reliability under gateway and pool pressure
4. recovery logic when part of the workload does not land cleanly
5. validator health and post-window operational proof

An agent that optimizes only for "send the target count once" will underperform an agent that optimizes for recoverability, proof, and window hygiene.

## Main Cross-Task Lesson

For live stress windows, counted on-chain success matters more than nominal submission volume.

That means the correct workflow is:

1. prepare the exact sender set before the window
2. fund the exact set the challenge will attribute
3. send during the official window only
4. checkpoint progress while sending
5. measure actual success from saved artifacts
6. top up only if there is a real shortfall and time remains

## Treat Every Window As A Separate Workload

Even when several stress tasks belong to one challenge, the safest operating model is to treat each official window as its own workload.

Generic learning:

1. use a separate wallet manifest per window
2. use separate run artifacts per window
3. verify each window independently
4. do not assume a later workload can rescue an earlier shortfall

This matters because different windows often have different:

1. transaction shapes
2. attribution rules
3. funding requirements
4. relayer requirements
5. smart contract or token prerequisites

## Fresh Funded Address Sets Reduce Attribution Risk

The safest interpretation of BoN stress challenges is verifier-first:

1. create fresh challenge wallets for each window when possible
2. fund that window's wallet set from the registered BoN wallet
3. avoid mixing workloads on the same sender set unless the live rules explicitly allow it

Generic learning:

1. if the page says the latest funded set is what counts, treat that literally
2. if moderators later tighten the funding timing, follow the clarification
3. funding is part of the proof model, not only a setup step

A fresh per-window sender set is usually the lowest-risk attribution strategy.

## Moderator Clarifications Are Part Of The Spec

Live event pages and moderator clarifications do not always align perfectly.

Generic learning:

1. save the challenge wording you relied on
2. treat moderator clarifications as authoritative once published
3. if there is ambiguity and enough time remains, choose the interpretation that is easiest to defend later

For future agents, the safest default is:

1. prefer the stricter interpretation if it can still be executed inside the window
2. if the clarification arrives late, preserve the earlier wording and adapt immediately

## Build For Partial Failure, Not The Happy Path

Under real load, timeouts and partial runs are normal.

Generic learning:

1. expect gateway or pool timeouts
2. expect some submitted transactions to never be counted
3. expect verification tooling to be slower than the send loop
4. expect to need a recovery chunk at least sometimes

This changes how the tooling should be written:

1. make batch sends retry-safe
2. make recovery chunks easy to launch from the same manifest
3. keep commands per window simple enough to restart quickly

Overshooting the target can be rational when the network is under stress, but do it intentionally, not blindly.

## Checkpoint Artifacts During The Send Loop

This is the most important tooling lesson from live BoN windows.

Writing proof only at the end of a large batch is not good enough.

Generic learning:

1. checkpoint transaction hashes incrementally during the run
2. persist progress after every batch or worker completion
3. do not rely on process exit to save the only copy of the run

Without crash-safe artifacts, a timeout can erase the only local evidence of what was submitted.

## Use The Simplest Proven Transaction Path

Stress windows reward boring reliability over elegant abstraction.

Generic learning:

1. keep a direct CLI path available even if an SDK abstraction exists
2. test the exact transaction shape against BoN before the official window
3. if one encoding path fails and another proven path works, use the proven path

This matters especially for:

1. relayed transactions
2. smart contract calls with token transfers
3. contract calls that must match a live example exactly

## Cross-Shard And Relayed Workloads Need Extra Care

Cross-shard, relayed, and smart-contract workloads add more ways to be "almost right" while still missing the verifier's rule.

Generic learning:

1. confirm the sender shard and receiver shard relationship explicitly
2. confirm who pays the fee in relayed flows
3. confirm smart contract arguments and token-transfer encoding from a real successful example
4. for cross-shard contract calls, prefer a sender set that makes the cross-shard property obvious

Do not assume that a successful direct transaction implies the relayed version is encoded correctly.

## Submission Count And Success Count Are Different

Agents need both numbers.

Generic learning:

1. `submitted` means the sender path accepted the transaction
2. `success` means the transaction later confirmed on-chain and should count
3. a run is not finished just because the target number was submitted

The correct recovery decision is based on:

1. verified success shortfall
2. time remaining in the official window
3. whether another chunk from the same manifest is safe and worthwhile

## Verification Tooling Can Be Wrong For Local Reasons

A verifier returning `unknown` for every transaction does not automatically mean the run failed.

Generic learning:

1. distinguish transaction failure from status-query failure
2. if DNS, gateway, or sandbox restrictions impair local verification, keep the raw run files and retry from a cleaner environment later
3. do not send unnecessary extra load just because one local status pass returned `unknown`

Saved run artifacts are the safety net here.

## Network Path Stability Matters More Than Local Node Sync For Scoring

For timed send challenges, the transaction sender path usually matters more than whether the local validator is perfectly synced at that exact moment.

Generic learning:

1. separate validator health from wallet/gateway health in your decision-making
2. an unsynced local node does not automatically block challenge scoring if the challenge is measured by on-chain transactions sent through the gateway
3. gateway reachability, DNS stability, and outbound network consistency can decide the result more than local node sync

That said, validator health still matters for:

1. restart requirements
2. log upload requirements
3. overall challenge acceptance

## Infrastructure Steps Around The Window Are Part Of The Challenge

Stress challenges can include infrastructure prerequisites and postrequisites, not only send targets.

Generic learning:

1. read the page for restart and log-upload requirements, not only tx counts
2. treat pre-window and post-window restarts as part of the official workflow
3. collect the exact main-machine log segment required for upload
4. preserve the exact submitted log bundle separately from runtime folders

If the challenge says the log must be bounded by restarts, build the artifact plan around those restarts from the beginning.

## Keep Window Artifacts And Submission Bundles Separate

A clean runtime folder helps, but the more important rule is preserving the exact proof bundle.

Generic learning:

1. store live run JSON files per window
2. keep the exact uploaded log bundles in a dedicated submissions location
3. avoid reusing or mutating the final uploaded artifact after submission

This makes moderator follow-up and later documentation much easier.

## Cross-Cutting Stress Window Lessons

### 1. Prepare For Attribution Before Throughput

A faster sender with the wrong funded set is worse than a slower sender with correct attribution.

### 2. Use Fresh Wallet Sets Per Window When Possible

This is the cleanest defense against attribution ambiguity.

### 3. Treat Clarifications As Operationally Binding

Live competition rules can move. Keep receipts and adapt quickly.

### 4. Design For Recovery, Not For A Single Perfect Run

Timeouts, retries, and partial landings are normal.

### 5. Preserve Proof While The Run Is Still Happening

Artifacts created only at the end are too fragile.

### 6. Separate Submission From Verification

A send run can be good even when a local verifier is impaired.

### 7. Include Infrastructure Proof In The Plan

Restarts, node health, and log uploads can matter as much as the transaction counts.
