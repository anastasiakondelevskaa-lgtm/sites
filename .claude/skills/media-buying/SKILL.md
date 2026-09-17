---
name: media-buying
description: >
  Operating doctrine for paid-traffic media buying on Meta/Facebook Ads (and the
  same logic transferred to TikTok/Google): unit economics, kill rules, automated
  rules, scaling ladders, account structure, funnel diagnostics and Marketing API
  operations. Use this skill whenever the work touches ad campaigns, ad sets,
  creatives, CPA/CPL/ROAS/ROI, budgets, "связки"/bundles, traffic arbitrage,
  автоправила, скейл, залив, тесты креативов, ad account structure, pixel/CAPI,
  tracker postbacks (Keitaro/Binom), or the Meta Marketing API — even if the user
  never says "Facebook" and only describes the symptom ("бюджет сливается",
  "лиды дорогие", "как масштабировать", "что выключать"). Also use it before
  writing any code that reads or changes ad account state.
---

# Media buying: operating doctrine

The job is not "run ads". The job is to **find the few bundles that convert below
breakeven CPA and route the entire budget into them, as fast as the platform's
learning mechanics allow** — while spending as little as possible finding out
that the rest don't work.

Everything below is in service of two numbers: how much money a losing test
burns before it's cut, and how fast a winner's budget compounds.

## Before anything else: get the economics

Never propose thresholds, rules or budgets before these five numbers are known.
Asking for them takes one message; guessing produces advice that is confidently
wrong. If the user hasn't given them, ask — briefly, in one block:

| Symbol | Meaning | Typical source |
|---|---|---|
| `P` | payout per conversion (net, after hold) | affiliate network / own margin |
| `A` | approve / qualification rate | call center, CRM, network stats |
| `T` | target CPA = `P × A × (1 − margin)` | derived |
| `BE` | breakeven CPA = `P × A` | derived |
| `B` | ad set daily budget, test stage = `3 × T` | derived |

Margin of 30% is a sane default for a mature vertical, 40-50% while testing —
the buffer absorbs approve drift and attribution lag.

`P` is what survives to the operator, not the sticker price. On low tickets the
gap is large enough to change decisions: payment processing takes a fixed fee
plus a percentage (around 7% of a `$7.50` sale, because the fixed part dominates),
and refunds take their share on top. A `$7.50` product at 10% refunds nets about
`$6.30`, so a "2× on ad spend" goal means CPA `$3.15`, not `$3.75`. State which
of the two the target refers to before writing any threshold — it's a 20% swing
in every number downstream.

**Where there is a back end, `P` is LTV, not the first transaction.** A front-end
product exists to acquire a buyer; order bumps, upsells, the core offer and
subscriptions are where the economics actually live. Compute `P` over a fixed
window (30 or 60 days) across all revenue per acquired buyer:

| Structure | LTV/60d | CPA for 2× |
|---|---|---|
| front end only, `$7.50` at 10% refunds | `$6.30` | `$3.15` |
| + bump `$12` taken by 25% | `$9.30` | `$4.65` |
| + upsell `$40` taken by 10% | `$13.30` | `$6.65` |

This matters more than any rule in this skill. Tuning thresholds and creative
moves profitability by tens of percent; adding a back end can double the CPA the
operation can afford, which converts directly into auctions won and volume
available. When a funnel is front-end only and the target is aggressive, say so
plainly — the ceiling is structural, and no threshold fixes it.

Worked example: payout `$18`, approve `55%` → `BE = $9.90`, at 40% margin
`T ≈ $5.94` → round to **`T = $6`**, test budget **`B = $18`/day**.

Every threshold in this skill is expressed as a multiple of `T`, so the whole
system re-derives from one number. When `T` changes, restate the table — don't
patch individual rules.

## Decision windows

Media buying goes wrong in two directions: killing winners during the learning
phase, and letting losers bleed because "it might still come in". Both are
avoided by deciding at fixed checkpoints instead of continuously staring.

Budget has a floor that is independent of all of this. An ad set leaves the
learning phase at roughly 50 conversions in 7 days, so the daily budget that
buys stability is about `7×T`. Below it the ad set never exits learning and its
CPA swings on platform mechanics regardless of how good the bundle is — which
makes "stable" unreachable by tuning. Test budgets of `3×T` are for *selection*,
not for running: they answer "junk or not" and nothing else. A promoted winner
therefore gets **duplicated straight onto `7×T`** rather than laddered up from
`3×T`, because a 2.5× jump would reset learning anyway; the ladder starts after
that duplicate has had its first week.

| Window | Question | Default action |
|---|---|---|
| First 2h / `< 0.5×T` spent | none — delivery hasn't stabilised | do nothing |
| `1.5×T` spent, 0 conversions | is it delivering to anyone who cares? | kill |
| End of day 1 | did anything convert at all? | kill zeros, hold the rest |
| Day 3, `≥ 5×T` spent | is CPA under target? | kill `> T`, promote `≤ T` |
| Day 3-7 on a winner | can it take more budget? | ladder up 20%/day |
| Frequency `> 2.5`, CPA drifting | is the audience burned? | refresh creative, not budget |

The asymmetry is deliberate: kill decisions are made on *today's* data because
the loss is immediate and irreversible; keep/scale decisions are made on *3-day*
data because conversion volume at these budgets is too thin for one day to mean
anything. A single ad set doing 3 conversions/day has a daily CPA that swings
±40% on noise alone — cutting a proven bundle on one bad day destroys more value
than the bad day cost.

## The two-floor account structure

Meta's automated rules take **one time range for the whole rule**. That single
constraint dictates the structure: "kill on today's burn, but spare anything
holding `≤ T` over 3 days" cannot be written as one rule. So the population is
split, and each floor gets its own rule set:

```
TEST  | <vertical> | <geo> | <angle>    → hard stop-losses, short leash
SCALE | <vertical> | <geo> | <angle>    → soft rules + budget ladder
```

Promotion TEST → SCALE is a rename, which is why the prefix carries the policy.
Create every rule from a **filtered** ad set list (`Ad Set Name contains TEST`)
so the rule's scope follows the filter and picks up new ad sets automatically —
then reopen the saved rule and confirm the scope didn't silently reset to "all
active ad sets", which it sometimes does.

Full rule tables, exact thresholds and the platform gotchas that make rules
misfire: **`references/kill-rules.md`**. Read it before creating or tuning any
automated rule. Naming conventions, hierarchy, pixel hygiene and account health:
**`references/account-structure.md`** — the rules above only work if names and
hierarchy are disciplined, because every rule scopes off a name.

## Scaling

A winner is not scaled by raising its budget until it breaks. It's scaled along
two axes, and confusing them is the single most common way a profitable bundle
gets destroyed:

- **Vertical** — more budget on the same ad set. Cheap but capped: every
  increase re-enters learning, so `+20%/day` max, once per day, never twice.
- **Horizontal** — more ad sets carrying the same creative into new audiences,
  geos, placements or accounts. Unlimited but each copy pays its own tuition.

Ladders, duplication rules, CBO consolidation, and when to stop:
**`references/scaling.md`**.

## When something is wrong, diagnose the funnel — don't touch the budget

"CPA is high" is not a diagnosis. The funnel has four independent stages and
each has a different fix; changing the budget fixes none of them.

```
CPM  → auction / audience / account quality
CTR  → creative and hook
CR   → prelander, page speed, offer-to-creative match
A    → lead quality, geo, call center
```

Walk the stages in order and compare each against the account's own baseline,
not against someone's blog post. The stage that's off by the largest multiple is
the one to fix. Procedure and the reference ranges:
**`references/diagnostics.md`**.

## Creatives

Creative is the only lever with unbounded upside — audiences and bids move CPA
by tens of percent, a new angle moves it by multiples. Practical consequences:

- Test **angles**, not variations. Five colours of the same hook is one test.
- One ad set, 3-5 ads, let Meta allocate. Don't split-test creatives across ad
  sets at these budgets; there's never enough volume for significance.
- A creative is dead when frequency climbs and CTR decays on the same audience —
  refresh before CPA rises, because by then you've already paid for the decay.
- Keep a graveyard: what died, on which audience, with what CTR. Relaunching the
  same losing angle three months later is the most expensive habit in this job.

When the operator's corpus of collected viral posts is available (the MCP with
`ig_viral` / `tg_viral` / `post` / `targets`), mine it for angles before writing
new ones: filter by ratio (× above the account's own median), open the post,
read what the hook actually does, then write the script. Ratio compares across
accounts; raw view counts don't.

## Working the account through the API

Anything repeated more than twice a week, or anything Meta's own rules can't
express (per-placement kills, per-geo kills, hour-of-day analysis, real ROI from
tracker postbacks, automatic duplication of winners), belongs in code.

Endpoints, field sets, breakdown queries, rate limits, token setup and the
required safety rails for any script that can spend money:
**`references/marketing-api.md`**.

Two rules that are not negotiable when writing such code:

1. **Dry-run first.** Any script that can pause, duplicate or re-budget must
   support `--dry-run` printing the exact intended calls, and that output is
   reviewed before the first live run. An off-by-one in a threshold comparison
   turns "pause losers" into "pause the account".
2. **Log the reason, not just the action.** Every write records the metric
   values that triggered it. Without this, a week later nobody can tell whether
   the bot killed a bundle correctly or on stale data — and that question
   decides whether the bot is trusted or switched off.

## Division of labour

Who decides what, what the agent may do unattended, and the escalation path:
**`references/org-structure.md`**. Read it when the question is about process,
access, roles or "who's responsible for this" rather than about a number.

## Staying inside the platform's rules

Account longevity is an economic variable, not a compliance footnote: a banned
account costs every winning bundle it carried plus the time to rebuild pixel
history. So the work runs inside Meta's advertising policies — real landing
pages matching the ad, honest claims, proper disclosures, no cloaking or
review-evasion. Bundles that only survive by hiding from review aren't assets;
they're borrowed time, and they distort every threshold in this skill because
their measured CPA never includes the cost of the ban.

If a user asks for cloaking, review evasion, or fake-document workarounds, say
plainly that it's not something to build, and redirect to what actually moves
CPA: economics, creative angles, funnel diagnostics and speed of iteration.
