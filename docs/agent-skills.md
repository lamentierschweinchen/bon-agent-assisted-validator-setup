# MultiversX AI Skills

AI skill packages give an agent sharper MultiversX-specific knowledge before it runs a BoN session. They are optional but useful whenever the work involves SDK transaction construction, ESDT operations, cross-shard routing, DEX calls, or relayed transactions.

## Official skill set

**[multiversx/mx-ai-skills](https://github.com/multiversx/mx-ai-skills)** — maintained by the MultiversX team.

Covers smart contract development (Rust / `multiversx-sc`), dApp frontend (`sdk-dapp`), security auditing, static analysis, WASM optimisation, and protocol internals (sharding, ESDT, consensus).

Install into a compatible agent environment:

```bash
npx openskills install multiversx/mx-ai-skills
```

Or clone manually and point your agent at the relevant `SKILL.md` files:

```bash
git clone https://github.com/multiversx/mx-ai-skills.git .ai-skills
```

## Community skill set

**[michavie/mx-ai-skills](https://github.com/michavie/mx-ai-skills)** — community-maintained complement.

Focuses on four areas: smart contracts, frontend (React / sdk-dapp), backend SDK usage (Go, Python, TypeScript), and protocol architecture. Useful as a second perspective or when the official set does not cover a specific pattern.

```bash
npx openskills install michavie/mx-ai-skills
```

## Relevance to BoN challenges

These skill sets are primarily aimed at MultiversX developers, not validator operators. The overlap with BoN work is indirect but real:

| Challenge area | Relevant skill coverage |
|---|---|
| C2 — on-chain tasks | sdk-core transaction construction, delegation contract patterns |
| C3 — node operations | Protocol architecture, shard and epoch awareness |
| C4 — stress windows | sdk-core `MoveBalance` / ESDT / relayed patterns, sharding-aware routing, DEX interaction via smart contract calls |

For C1 (initial validator setup), the workspace scripts and playbooks in this repo are more directly applicable than these skill sets.

## How to load

Both repos use the OpenSkills format, compatible with Cursor, Windsurf, Codex, and most AI coding environments. Load before starting a BoN session. If your environment does not support OpenSkills, clone the repo and reference the relevant `SKILL.md` files directly during the session.
