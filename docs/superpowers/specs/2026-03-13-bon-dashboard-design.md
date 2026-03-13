# Battle of Nodes — Live Dashboard Design Spec

## Context

The Battle of Nodes (BoN) is a shadow-fork challenge on MultiversX where community validators run nodes on an isolated network (Chain ID `B`). There is currently no public-facing way for a general audience to follow what is happening on this network. This dashboard fills that gap: a single-page live analytics view showing network health, resilience, activity, and progress — without surfacing challenge-specific or shadow-fork-distorted metrics.

The data layer follows the guidance in `docs/dashboard-handoff.md`, which defines 10 recommended homepage stats, API endpoints, computation formulas, and editorial rules for what to highlight vs. avoid.

## Decisions

- **Single-page dashboard** — all 10 stats on one screen, no routing or navigation.
- **Next.js 15 App Router** with a Route Handler (`/api/snapshot`) as the server-side aggregator.
- **Vercel deployment** — new GitHub repo, auto-deploy on push to main.
- **Supernova theme** — deep space blue background, orange fire accents, cyan for MultiversX brand threading, explosive white for hero numbers.
- **Hybrid branding** — MultiversX logo/identity mark with a unique supernova visual identity.
- **No heavy animations** — CSS transitions and lightweight JS count-up effects only. No canvas, WebGL, or particle systems.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | Next.js 15, App Router |
| Language | TypeScript |
| UI | React 19 |
| Styling | Tailwind CSS v4 + CSS custom properties |
| Animation | Framer Motion (AnimatedNumber count-up) |
| Deployment | Vercel (auto-deploy from GitHub) |

No other runtime dependencies. The BoN API is public — no env vars or secrets needed.

## Data Layer

### Server-Side Aggregator (`/api/snapshot`)

A single Route Handler that produces a `DashboardSnapshot` by fetching all BoN API endpoints in parallel, computing derived metrics, and caching the result.

**Fetch targets** (all from `https://api.battleofnodes.com`):

| Endpoint | Purpose | Refresh |
|----------|---------|---------|
| `/nodes?size=500&from=N` (paginated) | Full node list for stats 1–5 | 30s |
| `/nodes/count?online=true` | Nodes online count | 15s |
| `/network/status/0`, `/1`, `/2`, `/4294967295` | Per-shard nonce for sync check | 15s |
| `/transactions/count?after=1773234000` | TX since launch | 30s |
| `/transactions/count?status=success&after=<24h>` | Successful TX last 24h | 30s |
| `/transactions/count?isScCall=true&status=success&after=<24h>` | SC calls last 24h | 30s |
| `/blocks/count?epoch=N` (per epoch since launch) | Blocks since launch | 60s |
| `/network/config` | Round duration for epoch time remaining | 300s |

**Caching strategy**: In-memory cache with 15-second TTL. Stale-while-revalidate: if a request arrives after TTL, return stale data immediately and trigger a background refresh. This avoids blocking the client on slow upstream fetches.

**Node pagination**: Loop `/nodes?size=500&from=0,500,1000...` until a page returns fewer than 500 results. The full node list powers stats 1–5.

**Blocks since launch**: Sum `/blocks/count?epoch=N` for epochs `BON_LAUNCH_EPOCH + 1` through `currentEpoch`, plus the fixed partial count for epoch 2033 (`BON_LAUNCH_PARTIAL_BLOCKS_E2033 = 9456`).

### Response Shape

```ts
type DashboardSnapshot = {
  generatedAt: string;              // ISO timestamp
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
```

### Client Polling

The client fetches `/api/snapshot` every 15 seconds via a custom `useSnapshot` hook. No direct BoN API calls from the browser.

### Constants

All constants from `dashboard-handoff.md` live in `src/lib/constants.ts`:

- `BON_API_BASE`
- `BON_LAUNCH_TS`
- `BON_LAUNCH_EPOCH`
- `BON_LAUNCH_PARTIAL_BLOCKS_E2033`
- `SYNC_TOLERANCE_BLOCKS`
- `BACKUP_NAME_REGEX`
- `OFFICIAL_INFRA_IDENTITIES`
- `OFFICIAL_INFRA_NAME_PATTERNS`
- `OFFICIAL_INFRA_OWNERS`
- `OFFICIAL_INFRA_PROVIDERS`

## Page Layout

Single page, top to bottom:

### 1. Header Bar
- Supernova logo mark (radial gradient circle — white core, orange fire, fade to transparent)
- "Battle of Nodes" title
- Live indicator (pulsing cyan dot)
- "SHADOW FORK ANALYTICS" subtitle right-aligned

### 2. Hero Stat — Nodes Online Now
- Largest number on the page (56px+, font-weight 900, white, subtle glow)
- "Nodes Online Now" label above in orange
- "across 4 shards" subtitle below in muted white

### 3. Primary Stat Grid (2x2)

| Position | Stat | Accent |
|----------|------|--------|
| Top-left | Nodes Fully Synced | Cyan (`#23f0c7`) |
| Top-right | Community Nodes Online | Blue (`#00b4d8`), with info tooltip explaining exclusion logic |
| Bottom-left | Backup Coverage % | Orange (`#e8601c`) |
| Bottom-right | Distinct Active Operators | Warm orange (`#ff8c42`) |

Each card shows: label (colored), big number (white), subtitle (muted).
Backup Coverage additionally shows the ratio (e.g., "92 / 246 providers").

### 4. Transaction Stats Row (3-column)

| Col 1 | Col 2 | Col 3 |
|-------|-------|-------|
| TX Since Launch | Successful TX Last 24h | SC Calls Last 24h |

Neutral-toned cards (white/gray borders), centered numbers, smaller than primary grid.

### 5. Epoch Progress

Full-width card:
- "Epoch 2039" label + "~2h 14m remaining" right-aligned
- Gradient progress bar: orange → white leading edge with a glowing dot
- Percentage (large) + round count (small) below

### 6. Blocks Since Launch

Compact inline stat beneath the epoch bar. Label + number on one line.

### 7. Footer

- "Powered by MultiversX" text
- Link to BoN API docs
- Data freshness: "Updated X seconds ago"

## Responsive Behavior

| Breakpoint | Primary grid | TX row | Hero |
|------------|-------------|--------|------|
| Desktop (≥1024px) | 2×2 | 3 columns | Large (56px) |
| Tablet (≥768px) | 2×2 | 2+1 stack | Medium (48px) |
| Mobile (<768px) | 1 column stack | 1 column stack | Medium (44px) |

The page uses a single max-width container (~1100px) centered with auto margins.

## Component Architecture

```
src/components/
├── Dashboard.tsx         # Client component. Owns useSnapshot, passes data to children.
├── Header.tsx            # Logo, title, live indicator
├── HeroStat.tsx          # Big centered number for Nodes Online
├── StatCard.tsx          # Reusable: label, AnimatedNumber, subtitle, accent color
├── EpochProgress.tsx     # Progress bar with gradient + time remaining
├── TransactionRow.tsx    # 3-column transaction stats
├── AnimatedNumber.tsx    # Framer Motion count-up animation
└── LiveIndicator.tsx     # Pulsing cyan dot (CSS animation)
```

`page.tsx` is a server component that renders the static shell (background, metadata). `Dashboard` is a `"use client"` component that handles polling and renders all stat components.

## Visual Design

### Color Palette

| Name | Hex | Role |
|------|-----|------|
| Deep Space | `#020b18` → `#0a1a35` | Background gradient |
| Supernova Orange | `#e8601c` | Primary accent, labels, progress bars |
| Flare Orange | `#ff8c42` | Secondary warm accent |
| Core White | `#ffffff` | Hero numbers, explosive accents |
| MVX Cyan | `#23f0c7` | Health indicators, brand threading |
| MVX Blue | `#00b4d8` | Secondary cool accent |
| Muted Text | `rgba(255,255,255,0.4)` | Subtitles, secondary info |
| Card BG | `rgba(color,0.04-0.08)` | Glass-morphism card fills |
| Card Border | `rgba(color,0.15-0.25)` | Subtle colored borders |

### Card Style

- `background`: Very low opacity fill of the card's accent color
- `border`: 1px solid with accent color at 15–25% opacity
- `border-radius`: 14–16px
- `backdrop-filter: blur(10px)` for glass depth
- Hover: border opacity increases slightly

### Background

- Linear gradient from deep space to slightly lighter navy
- CSS radial gradient star field (tiny dots at random positions)
- Faint supernova glow radial at top center (orange at very low opacity)

### Typography

- Font: Inter (or system font stack as fallback)
- Hero number: 56px, weight 900, tight letter-spacing, white with text-shadow glow
- Stat number: 30px, weight 800
- Labels: 10–11px, uppercase, letter-spacing 2px, accent colored
- Subtitles: 11–12px, muted white

## Interactivity

### AnimatedNumber
When data updates, numbers smoothly count from their current value to the new value using Framer Motion's `animate` on a motion value. Duration ~800ms, ease-out curve. On initial load, counts up from 0.

### Epoch Progress Bar
Bar width animates via CSS transition when `progressPct` changes. The leading-edge white dot has a subtle CSS pulse animation (box-shadow oscillation).

### Live Indicator
Small cyan dot with CSS `@keyframes` pulse — opacity and box-shadow scale cycling every 2 seconds.

### Data Freshness
"Updated X seconds ago" counter increments every second client-side, resets to "just now" when fresh data arrives from the poll.

### Loading State
On initial page load before data arrives: skeleton cards with pulsing placeholder backgrounds (Tailwind `animate-pulse`). Numbers show "—" until data lands.

### Stale Data Indicator
If the snapshot's `generatedAt` is older than 60 seconds, the live indicator dot turns amber and a subtle "Data may be stale" note appears next to the freshness timestamp. The dashboard continues showing last-known data rather than blanking out.

## Project Structure

```
bon-dashboard/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   └── api/
│   │       └── snapshot/
│   │           └── route.ts
│   ├── components/
│   │   ├── Dashboard.tsx
│   │   ├── Header.tsx
│   │   ├── HeroStat.tsx
│   │   ├── StatCard.tsx
│   │   ├── EpochProgress.tsx
│   │   ├── TransactionRow.tsx
│   │   ├── AnimatedNumber.tsx
│   │   └── LiveIndicator.tsx
│   ├── lib/
│   │   ├── constants.ts
│   │   ├── types.ts
│   │   ├── aggregator.ts
│   │   └── cache.ts
│   └── hooks/
│       └── useSnapshot.ts
├── public/
│   └── favicon.ico
├── tailwind.config.ts
├── next.config.ts
├── package.json
├── tsconfig.json
└── README.md
```

## Verification Plan

1. **Data accuracy**: Compare `/api/snapshot` values against manual `curl` calls to the BoN API endpoints listed in `dashboard-handoff.md`.
2. **Responsiveness**: Preview at desktop, tablet, and mobile breakpoints. All stats visible and readable at each size.
3. **Animation**: Verify AnimatedNumber transitions smoothly on data refresh (no jumps or flicker).
4. **Loading state**: Verify skeleton cards appear before data arrives, then animate to real numbers.
5. **Staleness**: Verify "Updated X seconds ago" counts up and resets on fresh data.
6. **Edge cases**: Verify graceful behavior when BoN API is slow or returns errors (show last known data, don't crash).
7. **Vercel deploy**: Push to GitHub, connect Vercel, verify production build and `/api/snapshot` route works.
