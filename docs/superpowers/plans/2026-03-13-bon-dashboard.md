# Battle of Nodes Dashboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-page live analytics dashboard for the Battle of Nodes shadow fork, showing 10 real-time network stats with a supernova theme.

**Architecture:** Next.js 15 App Router with a single `/api/snapshot` Route Handler that aggregates data from the BoN public API (`https://api.battleofnodes.com`), caches server-side with 15s TTL, and serves a `DashboardSnapshot` JSON. The client polls this endpoint every 15 seconds and renders stats with animated numbers.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS v4, Framer Motion

**Spec:** `docs/superpowers/specs/2026-03-13-bon-dashboard-design.md`
**Data reference:** `docs/dashboard-handoff.md`

---

## File Structure

```
bon-dashboard/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # Root layout: Inter font, metadata, html/body
│   │   ├── page.tsx                # Server component: background shell, renders <Dashboard />
│   │   ├── globals.css             # Tailwind directives + supernova theme CSS custom properties + starfield
│   │   └── api/
│   │       └── snapshot/
│   │           └── route.ts        # GET handler: returns cached DashboardSnapshot
│   ├── components/
│   │   ├── AnimatedNumber.tsx      # Framer Motion count-up number
│   │   ├── LiveIndicator.tsx       # Pulsing cyan/amber dot
│   │   ├── StatCard.tsx            # Reusable stat card: label, number, subtitle, accent
│   │   ├── HeroStat.tsx            # Large centerpiece number (Nodes Online)
│   │   ├── EpochProgress.tsx       # Progress bar with gradient + time remaining
│   │   ├── Header.tsx              # Logo mark, title, live indicator, subtitle
│   │   ├── TransactionRow.tsx      # 3-column transaction stats
│   │   ├── Footer.tsx              # Powered by, API link, data freshness
│   │   └── Dashboard.tsx           # Client orchestrator: useSnapshot, renders all children
│   ├── lib/
│   │   ├── constants.ts            # All BoN constants from handoff doc
│   │   ├── types.ts                # DashboardSnapshot type + BonNode type
│   │   ├── aggregator.ts           # Fetch all BoN API endpoints, compute derived metrics
│   │   └── cache.ts                # In-memory stale-while-revalidate cache
│   └── hooks/
│       └── useSnapshot.ts          # Client-side polling hook (fetches /api/snapshot every 15s)
├── public/
│   └── favicon.svg                 # Supernova-themed favicon
├── next.config.ts
├── package.json
├── tsconfig.json
└── .gitignore
```

---

## Chunk 1: Project Scaffold, Constants, and Types

### Task 1: Create Next.js project and install dependencies

**Files:**
- Create: `bon-dashboard/` (entire project scaffold)

- [ ] **Step 1: Scaffold Next.js project**

Run from `/Users/ls/Documents/MultiversX`:

```bash
npx create-next-app@latest bon-dashboard \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --no-import-alias \
  --use-npm
```

Accept defaults. This creates the full Next.js 15 scaffold with App Router, TypeScript, Tailwind, and ESLint.

- [ ] **Step 2: Install Framer Motion**

```bash
cd bon-dashboard
npm install framer-motion
```

- [ ] **Step 3: Install Inter font**

Next.js includes `next/font` built-in. No extra package needed — we'll configure it in `layout.tsx` later.

- [ ] **Step 4: Verify project builds**

```bash
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 5: Create initial GitHub repo and push**

```bash
cd bon-dashboard
git add -A
git commit -m "chore: scaffold Next.js 15 project with Tailwind and Framer Motion"
```

Note: The user will create the GitHub repo and add remote manually. Just commit locally for now.

---

### Task 2: Constants file

**Files:**
- Create: `src/lib/constants.ts`

- [ ] **Step 1: Create `src/lib/constants.ts`**

```ts
// src/lib/constants.ts

/** BoN API base URL. */
export const BON_API_BASE = "https://api.battleofnodes.com";

/** Official Battle of Nodes launch moment (Unix timestamp). 2026-03-11 13:00:00 UTC. */
export const BON_LAUNCH_TS = 1773234000;

/** Launch happened inside this epoch. */
export const BON_LAUNCH_EPOCH = 2033;

/**
 * Exact network-wide count of blocks with timestamp >= BON_LAUNCH_TS inside epoch 2033.
 * Derived via descending-order binary search on /blocks?epoch=2033.
 */
export const BON_LAUNCH_PARTIAL_BLOCKS_E2033 = 9456;

/** Public API replication can lag slightly. Avoid exact-zero sync comparisons. */
export const SYNC_TOLERANCE_BLOCKS = 2;

/** Backup naming convention used by the validator track. */
export const BACKUP_NAME_REGEX = /-backup-BoN-/i;

/** Editorial classification: identities considered official infrastructure. */
export const OFFICIAL_INFRA_IDENTITIES = new Set(["multiversx"]);

/** Editorial classification: name patterns considered official infrastructure. */
export const OFFICIAL_INFRA_NAME_PATTERNS = [/^DO-SHADOWFORK-BON-ID-/i];

/** Editorial classification: owner addresses considered official infrastructure. */
export const OFFICIAL_INFRA_OWNERS = new Set<string>([]);

/** Editorial classification: provider addresses considered official infrastructure. */
export const OFFICIAL_INFRA_PROVIDERS = new Set<string>([]);

/** Client polling interval in milliseconds. */
export const SNAPSHOT_POLL_MS = 15_000;

/** Server-side cache TTL in milliseconds. */
export const CACHE_TTL_MS = 15_000;

/** Stale data threshold in milliseconds. If snapshot is older than this, show stale indicator. */
export const STALE_THRESHOLD_MS = 60_000;
```

- [ ] **Step 2: Verify file compiles**

```bash
npx tsc --noEmit src/lib/constants.ts
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add src/lib/constants.ts
git commit -m "feat: add BoN constants from handoff spec"
```

---

### Task 3: Types file

**Files:**
- Create: `src/lib/types.ts`

- [ ] **Step 1: Create `src/lib/types.ts`**

```ts
// src/lib/types.ts

/** The server-side aggregated snapshot returned by /api/snapshot. */
export type DashboardSnapshot = {
  generatedAt: string;
  nodesOnline: number;
  nodesSynced: number;
  backupCoveragePct: number;
  backupCoverageProviders: {
    covered: number;
    total: number;
  };
  distinctActiveOperators: number;
  communityRunNodesOnline: number;
  transactionsSinceLaunch: number;
  successfulTxLast24h: number;
  scCallsLast24h: number;
  blocksSinceLaunch: number;
  epoch: {
    number: number;
    roundsPassed: number;
    roundsPerEpoch: number;
    progressPct: number;
    remainingMs: number | null;
  };
};

/** Shape of a node object from the BoN /nodes API. Only the fields we use. */
export type BonNode = {
  name?: string;
  shard: number;
  type: string;
  status: string;
  online: boolean;
  nonce?: number;
  owner?: string;
  identity?: string;
  provider?: string;
};

/** Shape of /network/status/{shard} response. */
export type NetworkStatusResponse = {
  data: {
    status: {
      erd_nonce: number;
      erd_epoch_number: number;
      erd_rounds_passed_in_current_epoch: number;
      erd_rounds_per_epoch: number;
    };
  };
};

/** Shape of /network/config response (subset). */
export type NetworkConfigResponse = {
  data: {
    config: {
      erd_round_duration: string;
    };
  };
};
```

- [ ] **Step 2: Verify file compiles**

```bash
npx tsc --noEmit src/lib/types.ts
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add src/lib/types.ts
git commit -m "feat: add DashboardSnapshot and API response types"
```

---

## Chunk 2: Server-Side Data Layer

### Task 4: Cache module

**Files:**
- Create: `src/lib/cache.ts`

- [ ] **Step 1: Create `src/lib/cache.ts`**

```ts
// src/lib/cache.ts

import { CACHE_TTL_MS } from "./constants";

type CacheEntry<T> = {
  data: T;
  timestamp: number;
};

let entry: CacheEntry<unknown> | null = null;
let refreshPromise: Promise<unknown> | null = null;

/**
 * Stale-while-revalidate cache.
 *
 * - If cache is fresh (< TTL), return cached data.
 * - If cache is stale (>= TTL), return stale data AND trigger a background refresh.
 * - If cache is empty, await the fetch and populate.
 *
 * @param fetcher - async function that produces fresh data
 * @returns the cached or freshly fetched data
 */
export async function getOrRefresh<T>(fetcher: () => Promise<T>): Promise<T> {
  const now = Date.now();

  // Cache hit: fresh
  if (entry && now - entry.timestamp < CACHE_TTL_MS) {
    return entry.data as T;
  }

  // Cache hit: stale — return stale, refresh in background
  if (entry) {
    if (!refreshPromise) {
      refreshPromise = fetcher()
        .then((data) => {
          entry = { data, timestamp: Date.now() };
        })
        .catch((err) => {
          console.error("[cache] background refresh failed:", err);
        })
        .finally(() => {
          refreshPromise = null;
        });
    }
    return entry.data as T;
  }

  // Cache miss: await fresh data
  const data = await fetcher();
  entry = { data, timestamp: Date.now() };
  return data;
}
```

- [ ] **Step 2: Verify file compiles**

```bash
npx tsc --noEmit src/lib/cache.ts
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add src/lib/cache.ts
git commit -m "feat: add stale-while-revalidate cache module"
```

---

### Task 5: Aggregator module

**Files:**
- Create: `src/lib/aggregator.ts`

This is the core data layer. It fetches all BoN API endpoints in parallel and computes all 10 stats.

- [ ] **Step 1: Create `src/lib/aggregator.ts`**

```ts
// src/lib/aggregator.ts

import {
  BON_API_BASE,
  BON_LAUNCH_TS,
  BON_LAUNCH_EPOCH,
  BON_LAUNCH_PARTIAL_BLOCKS_E2033,
  SYNC_TOLERANCE_BLOCKS,
  BACKUP_NAME_REGEX,
  OFFICIAL_INFRA_IDENTITIES,
  OFFICIAL_INFRA_NAME_PATTERNS,
  OFFICIAL_INFRA_OWNERS,
  OFFICIAL_INFRA_PROVIDERS,
} from "./constants";
import type {
  DashboardSnapshot,
  BonNode,
  NetworkStatusResponse,
  NetworkConfigResponse,
} from "./types";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BON_API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`BoN API error: ${res.status} ${path}`);
  return res.json() as Promise<T>;
}

async function fetchNumber(path: string): Promise<number> {
  const res = await fetch(`${BON_API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`BoN API error: ${res.status} ${path}`);
  const text = await res.text();
  return Number(text);
}

async function fetchAllNodes(): Promise<BonNode[]> {
  const allNodes: BonNode[] = [];
  let from = 0;
  const size = 500;

  while (true) {
    const page = await fetchJson<BonNode[]>(
      `/nodes?size=${size}&from=${from}&fields=name,shard,type,status,online,nonce,owner,identity,provider`
    );
    allNodes.push(...page);
    if (page.length < size) break;
    from += size;
  }

  return allNodes;
}

function isSynced(
  node: BonNode,
  shardNonces: Record<number, number>
): boolean {
  const shardNonce = shardNonces[node.shard];
  return (
    node.online === true &&
    typeof node.nonce === "number" &&
    typeof shardNonce === "number" &&
    shardNonce - node.nonce >= 0 &&
    shardNonce - node.nonce <= SYNC_TOLERANCE_BLOCKS
  );
}

function isOfficialInfra(node: BonNode): boolean {
  const identity = (node.identity || "").toLowerCase();
  const name = node.name || "";

  return (
    OFFICIAL_INFRA_IDENTITIES.has(identity) ||
    OFFICIAL_INFRA_NAME_PATTERNS.some((re) => re.test(name)) ||
    OFFICIAL_INFRA_OWNERS.has(node.owner || "") ||
    OFFICIAL_INFRA_PROVIDERS.has(node.provider || "")
  );
}

async function computeBlocksSinceLaunch(
  currentEpoch: number
): Promise<number> {
  let total = BON_LAUNCH_PARTIAL_BLOCKS_E2033;

  // Fetch block counts for each epoch since launch in parallel
  const epochs: number[] = [];
  for (let e = BON_LAUNCH_EPOCH + 1; e <= currentEpoch; e++) {
    epochs.push(e);
  }

  const counts = await Promise.all(
    epochs.map((e) => fetchNumber(`/blocks/count?epoch=${e}`))
  );

  for (const count of counts) {
    total += count;
  }

  return total;
}

export async function buildSnapshot(): Promise<DashboardSnapshot> {
  const after24h = Math.floor(Date.now() / 1000) - 86400;

  // Fetch ALL endpoints in parallel — nodes, shard statuses, tx counts, config
  const [
    nodes,
    nodesOnline,
    status0,
    status1,
    status2,
    statusMeta,
    transactionsSinceLaunch,
    successfulTxLast24h,
    scCallsLast24h,
    networkConfig,
  ] = await Promise.all([
    fetchAllNodes(),
    fetchNumber("/nodes/count?online=true"),
    fetchJson<NetworkStatusResponse>("/network/status/0"),
    fetchJson<NetworkStatusResponse>("/network/status/1"),
    fetchJson<NetworkStatusResponse>("/network/status/2"),
    fetchJson<NetworkStatusResponse>("/network/status/4294967295"),
    fetchNumber(`/transactions/count?after=${BON_LAUNCH_TS}`),
    fetchNumber(`/transactions/count?status=success&after=${after24h}`),
    fetchNumber(
      `/transactions/count?isScCall=true&status=success&after=${after24h}`
    ),
    fetchJson<NetworkConfigResponse>("/network/config"),
  ]);

  // Build shard nonce map
  const shardNonces: Record<number, number> = {
    0: status0.data.status.erd_nonce,
    1: status1.data.status.erd_nonce,
    2: status2.data.status.erd_nonce,
    4294967295: statusMeta.data.status.erd_nonce,
  };

  // Stat 2: Nodes Fully Synced
  const nodesSynced = nodes.filter((n) => isSynced(n, shardNonces)).length;

  // Stat 3: Backup Coverage %
  const onlineMainProviders = new Set(
    nodes
      .filter(
        (n) =>
          n.online === true &&
          n.provider &&
          n.type === "validator" &&
          !BACKUP_NAME_REGEX.test(n.name || "")
      )
      .map((n) => n.provider!)
  );

  const onlineBackupProviders = new Set(
    nodes
      .filter(
        (n) =>
          n.online === true &&
          n.provider &&
          BACKUP_NAME_REGEX.test(n.name || "")
      )
      .map((n) => n.provider!)
  );

  const coveredCount = [...onlineMainProviders].filter((p) =>
    onlineBackupProviders.has(p)
  ).length;

  const backupCoveragePct =
    onlineMainProviders.size === 0
      ? 0
      : (100 * coveredCount) / onlineMainProviders.size;

  // Stat 4: Distinct Active Operators
  const distinctActiveOperators = new Set(
    nodes
      .filter((n) => n.online === true && !!n.owner)
      .map((n) => n.owner!)
  ).size;

  // Stat 5: Community-Run Nodes Online
  const communityRunNodesOnline = nodes.filter(
    (n) => n.online === true && !isOfficialInfra(n)
  ).length;

  // Stat 9: Blocks Since Launch
  const currentEpoch = statusMeta.data.status.erd_epoch_number;
  const blocksSinceLaunch = await computeBlocksSinceLaunch(currentEpoch);

  // Stat 10: Epoch Progress
  const metaStatus = statusMeta.data.status;
  const roundsPassed = metaStatus.erd_rounds_passed_in_current_epoch;
  const roundsPerEpoch = metaStatus.erd_rounds_per_epoch;
  const epochProgressPct = (100 * roundsPassed) / roundsPerEpoch;

  const roundDurationMs = Number(
    networkConfig.data.config.erd_round_duration
  );
  const remainingRounds = roundsPerEpoch - roundsPassed;
  const remainingMs = roundDurationMs > 0 ? remainingRounds * roundDurationMs : null;

  return {
    generatedAt: new Date().toISOString(),
    nodesOnline,
    nodesSynced,
    backupCoveragePct,
    backupCoverageProviders: {
      covered: coveredCount,
      total: onlineMainProviders.size,
    },
    distinctActiveOperators,
    communityRunNodesOnline,
    transactionsSinceLaunch,
    successfulTxLast24h,
    scCallsLast24h,
    blocksSinceLaunch,
    epoch: {
      number: currentEpoch,
      roundsPassed,
      roundsPerEpoch,
      progressPct: epochProgressPct,
      remainingMs,
    },
  };
}
```

- [ ] **Step 2: Verify file compiles**

```bash
npx tsc --noEmit src/lib/aggregator.ts
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add src/lib/aggregator.ts
git commit -m "feat: add BoN data aggregator with all 10 stat computations"
```

---

### Task 6: API Route Handler

**Files:**
- Create: `src/app/api/snapshot/route.ts`

- [ ] **Step 1: Create `src/app/api/snapshot/route.ts`**

```ts
// src/app/api/snapshot/route.ts

import { NextResponse } from "next/server";
import { getOrRefresh } from "@/lib/cache";
import { buildSnapshot } from "@/lib/aggregator";
import type { DashboardSnapshot } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const snapshot = await getOrRefresh<DashboardSnapshot>(buildSnapshot);
    return NextResponse.json(snapshot, {
      headers: {
        "Cache-Control": "public, s-maxage=10, stale-while-revalidate=30",
      },
    });
  } catch (err) {
    console.error("[/api/snapshot] Error:", err);
    return NextResponse.json(
      { error: "Failed to fetch dashboard data" },
      { status: 502 }
    );
  }
}
```

- [ ] **Step 2: Verify the project builds**

```bash
npm run build
```

Expected: Build succeeds. The `/api/snapshot` route is listed in the build output.

- [ ] **Step 3: Test the endpoint locally**

```bash
npm run dev &
sleep 3
curl -sS http://localhost:3000/api/snapshot | head -c 500
kill %1
```

Expected: JSON response containing `generatedAt`, `nodesOnline`, and other snapshot fields. The numbers should be reasonable (nodesOnline > 0, epoch number > 2033).

- [ ] **Step 4: Commit**

```bash
git add src/app/api/snapshot/route.ts
git commit -m "feat: add /api/snapshot route handler with caching"
```

---

## Chunk 3: Client Hook and UI Components

### Task 7: Client polling hook

**Files:**
- Create: `src/hooks/useSnapshot.ts`

- [ ] **Step 1: Create `src/hooks/useSnapshot.ts`**

```tsx
// src/hooks/useSnapshot.ts

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { DashboardSnapshot } from "@/lib/types";
import { SNAPSHOT_POLL_MS } from "@/lib/constants";

export function useSnapshot() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchSnapshot = useCallback(async () => {
    try {
      const res = await fetch("/api/snapshot");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: DashboardSnapshot = await res.json();
      setSnapshot(data);
      setError(null);
    } catch (err) {
      console.error("[useSnapshot] fetch failed:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      // Keep showing last known data — don't clear snapshot
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchSnapshot();

    // Poll every SNAPSHOT_POLL_MS
    intervalRef.current = setInterval(fetchSnapshot, SNAPSHOT_POLL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchSnapshot]);

  return { snapshot, error };
}
```

- [ ] **Step 2: Verify file compiles**

```bash
npx tsc --noEmit src/hooks/useSnapshot.ts
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add src/hooks/useSnapshot.ts
git commit -m "feat: add useSnapshot client polling hook"
```

---

### Task 8: AnimatedNumber component

**Files:**
- Create: `src/components/AnimatedNumber.tsx`

- [ ] **Step 1: Create `src/components/AnimatedNumber.tsx`**

```tsx
// src/components/AnimatedNumber.tsx

"use client";

import { useEffect, useRef } from "react";
import { useMotionValue, useSpring, useTransform, motion } from "framer-motion";

type Props = {
  value: number;
  /** Format as percentage with one decimal (e.g., "37.4%"). */
  percentage?: boolean;
  className?: string;
};

export function AnimatedNumber({ value, percentage, className }: Props) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { duration: 800, bounce: 0 });
  const display = useTransform(spring, (v) => {
    if (percentage) return `${v.toFixed(1)}%`;
    return Math.round(v).toLocaleString();
  });
  const prevValue = useRef(0);

  useEffect(() => {
    if (value !== prevValue.current) {
      motionValue.set(value);
      prevValue.current = value;
    }
  }, [value, motionValue]);

  return <motion.span className={className}>{display}</motion.span>;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/AnimatedNumber.tsx
git commit -m "feat: add AnimatedNumber component with Framer Motion spring"
```

---

### Task 9: LiveIndicator component

**Files:**
- Create: `src/components/LiveIndicator.tsx`

- [ ] **Step 1: Create `src/components/LiveIndicator.tsx`**

```tsx
// src/components/LiveIndicator.tsx

"use client";

type Props = {
  stale?: boolean;
};

export function LiveIndicator({ stale }: Props) {
  const color = stale ? "#f59e0b" : "#23f0c7";

  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="relative flex h-2 w-2"
        aria-label={stale ? "Data may be stale" : "Live"}
      >
        <span
          className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
          style={{ backgroundColor: color }}
        />
        <span
          className="relative inline-flex h-2 w-2 rounded-full"
          style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
        />
      </span>
      <span className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>
        {stale ? "STALE" : "LIVE"}
      </span>
    </span>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/LiveIndicator.tsx
git commit -m "feat: add LiveIndicator pulsing dot component"
```

---

### Task 10: StatCard component

**Files:**
- Create: `src/components/StatCard.tsx`

- [ ] **Step 1: Create `src/components/StatCard.tsx`**

```tsx
// src/components/StatCard.tsx

"use client";

import { AnimatedNumber } from "./AnimatedNumber";

type Props = {
  label: string;
  value: number | null;
  subtitle?: string;
  accentColor: string;
  percentage?: boolean;
  tooltip?: string;
};

export function StatCard({
  label,
  value,
  subtitle,
  accentColor,
  percentage,
  tooltip,
}: Props) {
  return (
    <div
      className="rounded-2xl border p-5 backdrop-blur-md transition-colors hover:border-opacity-50"
      style={{
        background: `${accentColor}0a`,
        borderColor: `${accentColor}3d`,
      }}
    >
      <div className="flex items-center gap-1.5">
        <div
          className="text-[10px] font-medium uppercase tracking-[2px]"
          style={{ color: accentColor }}
        >
          {label}
        </div>
        {tooltip && (
          <span
            className="cursor-help text-[10px] opacity-40 hover:opacity-70"
            title={tooltip}
          >
            &#9432;
          </span>
        )}
      </div>
      <div className="mt-1.5 text-3xl font-extrabold text-white">
        {value !== null ? (
          <AnimatedNumber value={value} percentage={percentage} />
        ) : (
          <span className="inline-block h-8 w-20 animate-pulse rounded bg-white/10" />
        )}
      </div>
      {subtitle && (
        <div className="mt-1 text-[11px] text-white/35">{subtitle}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/StatCard.tsx
git commit -m "feat: add StatCard reusable component"
```

---

### Task 11: HeroStat component

**Files:**
- Create: `src/components/HeroStat.tsx`

- [ ] **Step 1: Create `src/components/HeroStat.tsx`**

```tsx
// src/components/HeroStat.tsx

"use client";

import { AnimatedNumber } from "./AnimatedNumber";

type Props = {
  value: number | null;
};

export function HeroStat({ value }: Props) {
  return (
    <div className="py-8 text-center">
      <div
        className="text-[10px] font-medium uppercase tracking-[3px]"
        style={{ color: "#ff8c42" }}
      >
        Nodes Online Now
      </div>
      <div
        className="mt-2 text-[44px] font-black leading-none tracking-tight text-white
                    md:text-[48px] lg:text-[56px]"
        style={{
          textShadow:
            "0 0 40px rgba(255,255,255,0.3), 0 0 80px rgba(232,96,28,0.15)",
        }}
      >
        {value !== null ? (
          <AnimatedNumber value={value} />
        ) : (
          <span className="inline-block h-14 w-32 animate-pulse rounded bg-white/10" />
        )}
      </div>
      <div className="mt-1 text-[13px] text-white/40">across 4 shards</div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/HeroStat.tsx
git commit -m "feat: add HeroStat centerpiece component"
```

---

### Task 12: EpochProgress component

**Files:**
- Create: `src/components/EpochProgress.tsx`

- [ ] **Step 1: Create `src/components/EpochProgress.tsx`**

```tsx
// src/components/EpochProgress.tsx

"use client";

import { AnimatedNumber } from "./AnimatedNumber";

type Props = {
  epoch: {
    number: number;
    roundsPassed: number;
    roundsPerEpoch: number;
    progressPct: number;
    remainingMs: number | null;
  } | null;
};

function formatRemaining(ms: number | null): string {
  if (ms === null || ms <= 0) return "";
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) return `~${hours}h ${minutes}m remaining`;
  return `~${minutes}m remaining`;
}

export function EpochProgress({ epoch }: Props) {
  if (!epoch) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
        <div className="h-24 animate-pulse rounded bg-white/5" />
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-[10px] font-medium uppercase tracking-[2px] text-white/50">
          Epoch {epoch.number.toLocaleString()}
        </div>
        <div className="text-xs text-white/40">
          {formatRemaining(epoch.remainingMs)}
        </div>
      </div>

      {/* Progress bar */}
      <div className="relative h-2 overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{
            width: `${Math.min(epoch.progressPct, 100)}%`,
            background: "linear-gradient(90deg, #e8601c, #ff8c42, #ffffff)",
          }}
        >
          {/* Leading edge dot */}
          <div
            className="absolute right-0 top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-white"
            style={{
              boxShadow:
                "0 0 12px #fff, 0 0 24px rgba(232,96,28,0.6)",
            }}
          />
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between">
        <div className="text-xl font-bold text-white">
          <AnimatedNumber value={epoch.progressPct} percentage />
        </div>
        <div className="text-[11px] text-white/30">
          {epoch.roundsPassed.toLocaleString()} /{" "}
          {epoch.roundsPerEpoch.toLocaleString()} rounds
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/EpochProgress.tsx
git commit -m "feat: add EpochProgress bar component"
```

---

### Task 13: Header component

**Files:**
- Create: `src/components/Header.tsx`

- [ ] **Step 1: Create `src/components/Header.tsx`**

```tsx
// src/components/Header.tsx

"use client";

import { LiveIndicator } from "./LiveIndicator";

type Props = {
  stale: boolean;
};

export function Header({ stale }: Props) {
  return (
    <header className="flex items-center justify-between border-b border-white/[0.06] pb-4">
      <div className="flex items-center gap-3">
        {/* Supernova logo mark */}
        <div
          className="h-7 w-7 rounded-full"
          style={{
            background:
              "radial-gradient(circle, #ffffff 15%, #ff8c42 40%, #e8601c 65%, transparent 100%)",
            boxShadow: "0 0 20px rgba(232,96,28,0.5)",
          }}
        />
        <span className="text-base font-bold tracking-wide text-white">
          Battle of Nodes
        </span>
        <LiveIndicator stale={stale} />
      </div>
      <div className="hidden text-[11px] tracking-[1px] text-white/30 sm:block">
        SHADOW FORK ANALYTICS
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/Header.tsx
git commit -m "feat: add Header component with logo and live indicator"
```

---

### Task 14: TransactionRow component

**Files:**
- Create: `src/components/TransactionRow.tsx`

- [ ] **Step 1: Create `src/components/TransactionRow.tsx`**

```tsx
// src/components/TransactionRow.tsx

"use client";

import { AnimatedNumber } from "./AnimatedNumber";

type TxStat = {
  label: string;
  value: number | null;
};

type Props = {
  stats: TxStat[];
};

export function TransactionRow({ stats }: Props) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 text-center"
        >
          <div className="text-[9px] font-medium uppercase tracking-[2px] text-white/45">
            {stat.label}
          </div>
          <div className="mt-1.5 text-[22px] font-extrabold text-white">
            {stat.value !== null ? (
              <AnimatedNumber value={stat.value} />
            ) : (
              <span className="inline-block h-6 w-16 animate-pulse rounded bg-white/10" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/TransactionRow.tsx
git commit -m "feat: add TransactionRow 3-column component"
```

---

### Task 15: Footer component

**Files:**
- Create: `src/components/Footer.tsx`

- [ ] **Step 1: Create `src/components/Footer.tsx`**

```tsx
// src/components/Footer.tsx

"use client";

import { useState, useEffect, useRef } from "react";
import { STALE_THRESHOLD_MS } from "@/lib/constants";

type Props = {
  generatedAt: string | null;
};

export function Footer({ generatedAt }: Props) {
  const [secondsAgo, setSecondsAgo] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!generatedAt) return;

    const updateAge = () => {
      const age = Date.now() - new Date(generatedAt).getTime();
      setSecondsAgo(Math.floor(age / 1000));
    };

    updateAge();
    timerRef.current = setInterval(updateAge, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [generatedAt]);

  const isStale =
    secondsAgo !== null && secondsAgo * 1000 > STALE_THRESHOLD_MS;

  const freshnessText =
    secondsAgo === null
      ? ""
      : secondsAgo <= 1
        ? "Updated just now"
        : `Updated ${secondsAgo}s ago`;

  return (
    <footer className="mt-8 border-t border-white/[0.06] pt-4 text-center text-[11px] text-white/30">
      <div className="flex flex-col items-center gap-2 sm:flex-row sm:justify-between">
        <span>
          Powered by{" "}
          <span className="text-white/50">MultiversX</span>
        </span>
        <a
          href="https://api.battleofnodes.com/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="underline decoration-white/20 hover:text-white/50"
        >
          BoN API Docs
        </a>
        <span className={isStale ? "text-amber-400/70" : ""}>
          {freshnessText}
          {isStale && " · Data may be stale"}
        </span>
      </div>
    </footer>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/Footer.tsx
git commit -m "feat: add Footer with data freshness counter"
```

---

## Chunk 4: Dashboard Assembly, Styling, and Verification

### Task 16: Dashboard orchestrator

**Files:**
- Create: `src/components/Dashboard.tsx`

- [ ] **Step 1: Create `src/components/Dashboard.tsx`**

```tsx
// src/components/Dashboard.tsx

"use client";

import { useState, useEffect } from "react";
import { useSnapshot } from "@/hooks/useSnapshot";
import { STALE_THRESHOLD_MS } from "@/lib/constants";
import { Header } from "./Header";
import { HeroStat } from "./HeroStat";
import { StatCard } from "./StatCard";
import { TransactionRow } from "./TransactionRow";
import { EpochProgress } from "./EpochProgress";
import { AnimatedNumber } from "./AnimatedNumber";
import { Footer } from "./Footer";

export function Dashboard() {
  const { snapshot } = useSnapshot();
  const [isStale, setIsStale] = useState(false);

  // Re-evaluate staleness every second so the header dot turns amber in real-time
  useEffect(() => {
    const check = () => {
      if (!snapshot) return setIsStale(false);
      const age = Date.now() - new Date(snapshot.generatedAt).getTime();
      setIsStale(age > STALE_THRESHOLD_MS);
    };
    check();
    const timer = setInterval(check, 1000);
    return () => clearInterval(timer);
  }, [snapshot]);

  const s = snapshot;

  return (
    <div className="mx-auto max-w-[1100px] px-4 py-6 sm:px-6">
      <Header stale={isStale} />

      {/* Hero: Nodes Online */}
      <HeroStat value={s?.nodesOnline ?? null} />

      {/* Primary Stat Grid 2x2 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <StatCard
          label="Fully Synced"
          value={s?.nodesSynced ?? null}
          subtitle={
            s ? `${((s.nodesSynced / s.nodesOnline) * 100).toFixed(0)}% of online` : undefined
          }
          accentColor="#23f0c7"
        />
        <StatCard
          label="Community Nodes"
          value={s?.communityRunNodesOnline ?? null}
          subtitle="independent operators"
          accentColor="#00b4d8"
          tooltip="Excludes known official MultiversX infrastructure nodes. Counts online nodes not matching official identity patterns."
        />
        <StatCard
          label="Backup Coverage"
          value={s?.backupCoveragePct ?? null}
          subtitle={
            s
              ? `${s.backupCoverageProviders.covered} / ${s.backupCoverageProviders.total} providers`
              : undefined
          }
          accentColor="#e8601c"
          percentage
        />
        <StatCard
          label="Active Operators"
          value={s?.distinctActiveOperators ?? null}
          subtitle="distinct owners"
          accentColor="#ff8c42"
        />
      </div>

      {/* Transaction Stats Row */}
      <div className="mt-3">
        <TransactionRow
          stats={[
            { label: "TX Since Launch", value: s?.transactionsSinceLaunch ?? null },
            { label: "Successful TX 24h", value: s?.successfulTxLast24h ?? null },
            { label: "SC Calls 24h", value: s?.scCallsLast24h ?? null },
          ]}
        />
      </div>

      {/* Epoch Progress */}
      <div className="mt-3">
        <EpochProgress epoch={s?.epoch ?? null} />
      </div>

      {/* Blocks Since Launch */}
      <div className="mt-3 text-center">
        <span className="text-[10px] font-medium uppercase tracking-[2px] text-white/30">
          Blocks Since Launch
        </span>
        <span className="ml-2 text-sm font-bold text-white/70">
          {s ? (
            <AnimatedNumber value={s.blocksSinceLaunch} />
          ) : (
            <span className="inline-block h-4 w-20 animate-pulse rounded bg-white/10" />
          )}
        </span>
      </div>

      <Footer generatedAt={s?.generatedAt ?? null} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/Dashboard.tsx
git commit -m "feat: add Dashboard orchestrator component"
```

---

### Task 17: Global styles — supernova theme

**Files:**
- Modify: `src/app/globals.css`

- [ ] **Step 1: Replace `src/app/globals.css`**

Replace the entire file contents with:

```css
/* src/app/globals.css */

@import "tailwindcss";

/* Supernova theme custom properties */
:root {
  --space-deep: #020b18;
  --space-mid: #0a1a35;
  --supernova-orange: #e8601c;
  --flare-orange: #ff8c42;
  --core-white: #ffffff;
  --mvx-cyan: #23f0c7;
  --mvx-blue: #00b4d8;
}

html,
body {
  margin: 0;
  padding: 0;
  min-height: 100vh;
  background: linear-gradient(160deg, var(--space-deep) 0%, var(--space-mid) 100%);
  color: white;
}

/* Star field background */
body::before {
  content: "";
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(1px 1px at 10% 15%, rgba(255,255,255,0.8) 0%, transparent 100%),
    radial-gradient(1px 1px at 25% 45%, rgba(255,255,255,0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 50% 10%, rgba(255,255,255,0.6) 0%, transparent 100%),
    radial-gradient(1px 1px at 75% 35%, rgba(255,255,255,0.3) 0%, transparent 100%),
    radial-gradient(1px 1px at 90% 70%, rgba(255,255,255,0.5) 0%, transparent 100%),
    radial-gradient(1px 1px at 35% 85%, rgba(255,255,255,0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 60% 60%, rgba(255,255,255,0.25) 0%, transparent 100%),
    radial-gradient(1px 1px at 5% 55%, rgba(255,255,255,0.5) 0%, transparent 100%),
    radial-gradient(1px 1px at 42% 30%, rgba(255,255,255,0.35) 0%, transparent 100%),
    radial-gradient(1px 1px at 80% 50%, rgba(255,255,255,0.45) 0%, transparent 100%),
    radial-gradient(1px 1px at 15% 90%, rgba(255,255,255,0.3) 0%, transparent 100%),
    radial-gradient(1px 1px at 95% 25%, rgba(255,255,255,0.55) 0%, transparent 100%),
    radial-gradient(1.5px 1.5px at 80% 90%, rgba(35,240,199,0.5) 0%, transparent 100%),
    radial-gradient(1.5px 1.5px at 15% 70%, rgba(0,180,216,0.4) 0%, transparent 100%);
}

/* Supernova glow at top */
body::after {
  content: "";
  position: fixed;
  top: -100px;
  left: 50%;
  transform: translateX(-50%);
  width: 800px;
  height: 400px;
  pointer-events: none;
  z-index: 0;
  background: radial-gradient(
    ellipse,
    rgba(232, 96, 28, 0.06) 0%,
    rgba(255, 140, 66, 0.02) 40%,
    transparent 70%
  );
}

/* Ensure content is above pseudo-elements */
body > * {
  position: relative;
  z-index: 1;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/app/globals.css
git commit -m "feat: add supernova theme global styles with starfield"
```

---

### Task 18: Root layout

**Files:**
- Modify: `src/app/layout.tsx`

- [ ] **Step 1: Replace `src/app/layout.tsx`**

Replace the entire file contents with:

```tsx
// src/app/layout.tsx

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Battle of Nodes — Live Dashboard",
  description:
    "Real-time analytics for the MultiversX Battle of Nodes shadow fork. Track nodes, transactions, and network health.",
  icons: { icon: "/favicon.svg" },
  openGraph: {
    title: "Battle of Nodes — Live Dashboard",
    description:
      "Real-time analytics for the MultiversX Battle of Nodes shadow fork.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/app/layout.tsx
git commit -m "feat: configure root layout with Inter font and metadata"
```

---

### Task 19: Page component

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: Replace `src/app/page.tsx`**

Replace the entire file contents with:

```tsx
// src/app/page.tsx

import { Dashboard } from "@/components/Dashboard";

export default function Home() {
  return (
    <main className="min-h-screen">
      <Dashboard />
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: wire page.tsx to Dashboard component"
```

---

### Task 20: Clean up scaffold files

**Files:**
- Delete: `src/app/favicon.ico` (we'll use the default or add a custom one later)
- Delete: any default page styles or components from create-next-app

- [ ] **Step 1: Remove default scaffold files**

Remove any leftover default files that aren't needed:

```bash
rm -f public/file.svg public/globe.svg public/next.svg public/vercel.svg public/window.svg
```

- [ ] **Step 2: Create a simple SVG favicon**

Create `public/favicon.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <defs>
    <radialGradient id="g" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="30%" stop-color="#ff8c42"/>
      <stop offset="60%" stop-color="#e8601c"/>
      <stop offset="100%" stop-color="transparent"/>
    </radialGradient>
  </defs>
  <circle cx="16" cy="16" r="14" fill="#020b18"/>
  <circle cx="16" cy="16" r="8" fill="url(#g)"/>
</svg>
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: clean up scaffold files and add supernova favicon"
```

---

### Task 21: Build and visual verification

- [ ] **Step 1: Verify production build**

```bash
npm run build
```

Expected: Build succeeds with no errors. Output shows:
- Route `/` (static or dynamic)
- Route `/api/snapshot` (dynamic)

- [ ] **Step 2: Start dev server and verify in browser**

```bash
npm run dev
```

Open `http://localhost:3000`. Verify:
1. Deep space background with star field is visible
2. Header shows "Battle of Nodes" with supernova logo mark and pulsing live indicator
3. Hero stat shows a large number for Nodes Online
4. 2x2 stat grid shows: Fully Synced, Community Nodes, Backup Coverage, Active Operators
5. 3-column transaction row shows: TX Since Launch, Successful TX 24h, SC Calls 24h
6. Epoch progress bar is visible with gradient and time remaining
7. Blocks Since Launch appears below epoch bar
8. Footer shows "Powered by MultiversX", API link, and freshness counter

- [ ] **Step 3: Verify data accuracy**

Compare dashboard values against manual API calls:

```bash
curl -sS 'https://api.battleofnodes.com/nodes/count?online=true'
curl -sS 'https://api.battleofnodes.com/transactions/count?after=1773234000'
curl -sS "https://api.battleofnodes.com/transactions/count?status=success&after=$(($(date -u +%s)-86400))"
```

Dashboard values should match these responses (within the 15s cache window).

- [ ] **Step 4: Verify responsive layout**

Check at three breakpoints using browser dev tools:
- Desktop (1280px): 2x2 grid, 3-column TX row, large hero number
- Tablet (768px): 2x2 grid, TX row adjusts, medium hero
- Mobile (375px): Everything stacks to single column

- [ ] **Step 5: Verify animations**

Wait 15 seconds for a data refresh. Numbers should smoothly animate to their new values (no jumps). Epoch progress bar should advance smoothly.

- [ ] **Step 6: Verify staleness indicator**

Stop the BoN API proxy (or add artificial delay). After 60 seconds without fresh data, the live indicator should turn amber and show "STALE". Footer should show "Data may be stale".

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: complete Battle of Nodes live dashboard v1"
```

---

### Task 22: GitHub repo and Vercel deployment

- [ ] **Step 1: Create GitHub repository**

The user will create the repo on GitHub. Then:

```bash
git remote add origin git@github.com:USERNAME/bon-dashboard.git
git push -u origin main
```

- [ ] **Step 2: Connect to Vercel**

1. Go to vercel.com/new
2. Import the `bon-dashboard` repo
3. Framework preset: Next.js (auto-detected)
4. No environment variables needed
5. Deploy

- [ ] **Step 3: Verify production deployment**

Visit the Vercel URL. Verify:
- `/api/snapshot` returns JSON with live data
- Dashboard renders correctly with live data
- All 10 stats are visible and updating
