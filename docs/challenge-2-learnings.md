# Challenge 2 Learnings

This document captures the operational lessons from completing Battle of Nodes Challenge 2 end to end.

It is written to be useful regardless of:

- which AI agent is used
- which operating system is used
- whether transactions are sent with `mxpy`, another SDK, or manually built payloads

The goal is not to prescribe one exact command set. The goal is to make the task sequence unambiguous and keep agents from failing on the same BoN-specific edge cases.

## What Challenge 2 Actually Tested

Challenge 2 was not one generic "delegation" exercise.

It mixed five different on-chain behaviors:

1. stake into the existing MultiversX Community Delegation
2. delegate to your own staking provider
3. undelegate a small amount
4. change provider config
5. participate in governance with real staking power

An agent that treats these as one repeated "delegate" workflow will make mistakes.

## The Main Cross-Task Lesson

Do not trust challenge wording alone when two things are simultaneously true:

1. the title points at a specific named contract or program
2. the bullet points describe a more generic action

On BoN, that distinction mattered immediately.

The safest pattern is:

1. identify the exact contract or provider that the title refers to
2. verify the call shape from live state or recent successful transactions
3. only then send funds or config changes

## Task 1: MultiversX Community Delegation Was Not A Normal Provider Delegate

The most important Challenge 2 trap was the first task.

The wording looked like a generic delegation task, but the strict interpretation required the existing MultiversX Community Delegation specifically. On BoN, that path behaved like a legacy delegation contract, not a standard provider flow.

Generic learning:

1. a named community delegation may not use the same endpoint, contract family, or method name as a regular staking provider
2. do not assume `delegate` is always the correct transaction just because the challenge text says "delegate"
3. direct contract queries may be a better proof source than indexer/provider APIs

Repository impact:

- keep a dedicated note for this task instead of folding it into the generic provider setup guide
- document how to derive the correct target from live network data, not just from prose

## Task 2: Self-Delegation Depends On Provider Capacity, Not Just Wallet Balance

Delegating to your own provider was straightforward only after one hidden precondition was satisfied: the provider had room to accept the extra stake.

The first self-delegation attempt failed because the provider's total delegation cap was already full.

Generic learning:

1. before self-delegating, check whether the provider can still accept additional stake
2. if the delegation cap is exhausted, a delegate transaction can fail even when the wallet is funded and the provider is otherwise healthy
3. the agent should treat provider config as part of delegation preflight, not as a separate administrative concern

Repository impact:

- add a "cap reached" failure mode and recovery path to the delegation docs
- make agents verify provider capacity before building the final delegation proof

## Task 3: Undelegation Proof Is About Call Data And Success, Not Immediate Liquidity

The undelegation task was simpler, but it still has one important conceptual trap: undelegated funds do not become spendable immediately.

Generic learning:

1. `unDelegate` success is the proof target for this challenge, not withdrawal
2. agents should explicitly distinguish between undelegated amount, unbonding balance, and withdrawn balance
3. challenge wording may require only the undelegation transaction hash and amount, not the later exit from unbonding

Repository impact:

- explain unbonding clearly so users do not panic when funds do not reappear as liquid balance right away
- treat undelegation and withdrawal as separate workflows

## Task 4: Config Changes Should Be Verified At Contract Level If APIs Lag

Changing the service fee exposed another common BoN pattern: indexer-facing APIs can lag behind contract state.

The provider-facing API continued to show the old fee even after the change succeeded. The reliable proof came from the contract config query instead.

Generic learning:

1. when a config change succeeds on-chain but a higher-level API still shows stale data, verify against the contract view first
2. percentage-like values may be encoded as scaled integers, not floating-point numbers
3. agents should document both the human value and the encoded value used in the transaction payload

Repository impact:

- add an encoding note for service fee style values
- add a general rule: when API and contract disagree shortly after a write, prefer contract state for proof

## Task 5: Governance Requires Proposal Freshness And Current Voting Power

The governance task required more than submitting a vote. It depended on two live conditions:

1. the proposal was still active
2. the wallet had voting power derived from the staking state established earlier in the challenge

Generic learning:

1. governance tasks are highly time-sensitive and must be checked against live proposal status before voting
2. staking power should be verified before the vote to avoid sending a valid-looking but ineffective transaction
3. governance completion often depends on earlier challenge tasks being finalized enough to count toward voting power

Repository impact:

- add a short governance preflight checklist
- record that proposal status and voting power are mandatory proof inputs, not optional context

## Cross-Cutting BoN Lessons

These were the patterns that repeated across multiple tasks and are worth documenting prominently.

### 1. Challenge Titles Matter

If a task names a specific delegation, provider type, or contract family, assume that label matters until proven otherwise.

### 2. Live Discovery Beats Assumptions

Use live network state to identify:

- target contract or provider
- whether the provider is active
- whether capacity or configuration blocks the next transaction
- whether the challenge object is still active, such as a governance proposal

### 3. Call Shape Matters As Much As Amount

For challenge proof, these fields are often all equally important:

- receiver
- function name / data field
- encoded arguments
- transferred value
- transaction success

A correct amount sent to the wrong contract or with the wrong method is still a failed challenge submission.

### 4. Indexers Are Helpful, But Contract Views Are The Source Of Truth

Use indexers and convenience APIs for discovery, but fall back to direct contract queries for final proof when state appears stale or ambiguous.

### 5. Encode Units Explicitly

Always document both forms when values are not naturally human-readable:

- human form, such as `10 EGLD`
- encoded integer or hex form used on-chain

This prevents silent mistakes in delegation amounts, undelegation amounts, service fee changes, and governance payloads.

### 6. Keep Proof Collection Separate From Execution

Every task should end with a proof bundle that captures:

- tx hash
- sender
- receiver
- function/data field
- encoded amount or parameter
- direct verification query and result

Agents succeed more reliably when they are instructed to gather proof immediately after each step instead of reconstructing it later.

