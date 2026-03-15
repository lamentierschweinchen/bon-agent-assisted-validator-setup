# Challenge 4 Baseline Learnings

This document preserves the live lessons from the original baseline windows A and B.

For the current evergreen guide that covers stress-window operations more generally, start with [stress-window-learnings.md](stress-window-learnings.md).

This document captures the operational lessons from Battle of Nodes Challenge 4 baseline, Part 1 and Part 2:

1. Window A: high-volume intra-shard `MoveBalance`
2. Window B: DEX smart contract calls

It is written for any AI agent on any operating system.

The goal is to document how to survive the live windows, preserve proof, and interpret ambiguous attribution rules without wasting the opportunity window.

## What Challenge 4 Baseline Actually Tested

Challenge 4 baseline was not only about sending a lot of transactions.

It tested four things at once:

1. time-window discipline
2. transaction attribution through funded challenge addresses
3. sender reliability under gateway and pool pressure
4. whether the validator setup stayed healthy under load

An agent that optimizes only for "send the target count once" will fail more often than an agent that optimizes for recoverability.

## Main Cross-Task Lesson

For live stress windows, successful counted transactions matter more than nominal submissions.

That changes the correct agent behavior:

1. prepare before the window
2. send during the window
3. checkpoint progress during the run
4. verify actual success count
5. top up if needed while time remains

## Time Windows Must Be Treated As Separate Workloads

The baseline challenge used distinct official windows.

Generic learning:

1. do not blend two workload types into one long run
2. prepare separate commands, artifacts, and verification checks for each window
3. if a later window depends on earlier funding or setup rules, resolve that before the later workload opens

For this challenge the separation mattered because:

1. Window A and Window B had different transaction types
2. DEX success did not fix a weak `MoveBalance` submission
3. policy ambiguity around address funding could affect one window differently from the other

## Attribution Rules Were More Important Than Generic Load Generation

The challenge explicitly tied attribution to:

1. the initially registered BoN wallet
2. the funded challenge addresses

Generic learning:

1. treat challenge-address funding as part of the proof model, not as a mere convenience step
2. once a workload starts, avoid changing the funded sender set unless moderator guidance clearly requires it
3. if a moderator clarification introduces stricter timing on funding, prefer the clarification over earlier assumptions

One important wording nuance from the live page was that the challenge addresses were explicitly described as the senders for the `MoveBalance` workloads. That made Window A the most exposed to funding-timing interpretation.

## Challenge Text Can Conflict With Moderator Clarifications

The live page and later clarifications were not perfectly aligned.

Generic learning:

1. save screenshots or text excerpts of the live challenge page
2. treat moderator clarifications as authoritative once published
3. if wording is ambiguous and there is still time, choose the interpretation that is easiest to defend later

The safe default for future agents is:

1. if a workload depends on funded challenge addresses, perform the funding inside the official window or an officially granted extension whenever possible

That is the lowest-risk interpretation even when the original wording is softer.

## Retry And Recovery Logic Are Mandatory

This challenge surfaced the biggest operational lesson of the baseline windows: partial submissions are normal under load.

Generic learning:

1. do not assume one batch run will finish cleanly
2. gateway or pool timeouts are normal enough that retry planning should exist before the window opens
3. overshooting the target can be rational because some submitted transactions will never be counted

Window A demonstrated this clearly:

1. one large submission run timed out partway through
2. a follow-up recovery chunk was needed
3. the combined submission total deliberately overshot the target to absorb loss

## Checkpoint Run Artifacts During The Send Loop

This was the most important tooling lesson from the live run.

Writing artifacts only at the end of a batch is not good enough for a stress window.

Generic learning:

1. checkpoint transaction hashes incrementally during the send loop
2. persist progress after each successful batch or worker completion
3. do not rely on process exit to save proof

Without that, a timeout can erase the only local record of submitted transactions.

For live stress tooling, crash-safe artifact writing is not a nice-to-have. It is part of the challenge strategy.

## Use The Simplest Proven Call Path For DEX Workloads

The DEX window rewarded the most boring reliable implementation, not the most elegant abstraction.

Generic learning:

1. if a raw SDK path is flaky under the target network, keep a proven CLI fallback ready
2. verify the exact pool, token identifiers, gas limit, and function name before the window opens
3. run a real test transaction on the same wallet set before the official window

In this baseline run, the reliable DEX path was a direct `mxpy contract call` style swap with:

1. pool contract fixed
2. `swapTokensFixedInput`
3. `WEGLD-bd4d79` as the input token
4. destination token and minimum out explicitly encoded

That matched the live guidance better than a generic SDK-only abstraction.

## Validator Readiness Around The Stress Window Matters

The live page also attached validator restart requirements around the stress window.

Generic learning:

1. read the page for infrastructure prerequisites, not only transaction targets
2. if the challenge requires a main-node restart before and after the stress window, treat that as part of the workload
3. verify the main validator is healthy before launching the transaction flood

A stress script is only part of the challenge. Node-state preparation can also affect the final acceptance path.

## Submission Count And Success Count Are Different Metrics

This challenge is a good example of why agents need both numbers.

Generic learning:

1. `submitted` means "accepted by the sender path"
2. `success` means "confirmed on-chain and counted"
3. recovery decisions should be based on the success shortfall, not only on the submitted total

Window B showed the ideal case:

1. all 1000 swaps were submitted
2. all 1000 later verified as successful on-chain
3. no recovery chunk was needed

Window A showed the more common stressed case:

1. submissions were enough to clear the target on paper
2. the sender path experienced gateway timeouts
3. artifact reliability mattered as much as raw volume

## Verification Tools Can Fail For Local Environment Reasons

A local verifier that returns `unknown` for every transaction does not always mean the network failed.

Generic learning:

1. separate transaction-status uncertainty from transaction failure
2. if the verification environment has DNS or sandbox restrictions, rerun the proof query from an unrestricted environment before sending unnecessary extra load
3. keep the raw run files so the status pass can be retried safely later

This matters especially for agents running inside restricted desktop or sandboxed environments.

## Cross-Cutting Challenge 4 Baseline Lessons

### 1. Prepare The Sender Set Before You Need It

Wallet generation, funding, wrapping, and nonce sanity checks should be finished before the window whenever the rules allow it.

### 2. Treat Moderator Clarifications As Part Of The Spec

Live competition wording can move. Preserve the original text, but operate against the latest accepted clarification.

### 3. Build For Partial Failure, Not For The Happy Path

Stress windows reward retryability, checkpointing, and fast recovery.

### 4. Use Separate Proof For Separate Workloads

Window A and Window B should each have their own run artifacts, success check, and post-run interpretation.

### 5. Keep The Validator Healthy While Sending

The strongest challenge run is one where the transaction load succeeds and the node remains synced and active throughout.
