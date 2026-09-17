# Division of labour

Three actors, one decision boundary each. The boundary matters more than the
roles: an agent that asks about everything is useless, and one that decides
everything is a liability.

## Actors

**Operator (human).** Owns the money and the offer relationships: payouts,
approve rates, which verticals and geos to enter, creative angles, account
access, and any decision that changes the economics. Sets `T`.

**Agent (this skill, in a session).** Analysis and judgement calls that need
context: reading breakdowns, diagnosing which funnel stage is leaking, tuning
thresholds when economics move, deciding what to promote and what to duplicate,
writing and changing the autopilot's code, weekly review.

**Autopilot (code on a schedule).** Mechanical execution between sessions: pull
insights, apply the rule set, pause losers, ladder winners, report. No judgement,
no exceptions, fully logged.

## Decision boundary

| Decision | Autopilot | Agent | Operator |
|---|---|---|---|
| Pause an ad set breaching a kill rule | ✅ | — | — |
| Ladder a winner `+20%` within cap | ✅ | — | — |
| Cut budget `−25%` on soft-cut rule | ✅ | — | — |
| Promote TEST → SCALE | propose | ✅ | — |
| Exclude a placement/geo found in breakdowns | propose | ✅ | — |
| Duplicate a winner into a new audience | — | ✅ | — |
| Change a threshold within the existing `T` | — | ✅ | — |
| Change `T`, margin, or the economics | — | propose | ✅ |
| Enter a new vertical or geo | — | propose | ✅ |
| Raise the budget cap | — | propose | ✅ |
| Grant or rotate access | — | — | ✅ |

Read it as: the autopilot may only do what's reversible and bounded. Pausing is
reversible; a `+20%` step inside a cap is bounded. Everything that changes the
shape of the operation needs a human.

## Rhythm

**Daily (agent, ~15 min).** Read the overnight log: what was paused and why, what
laddered, what R5 flagged for promotion. Verify a sample of kills against the
3-day numbers — the check is whether the autopilot is killing correctly, not
whether it ran. Promote flagged bundles. Surface anything that needs the
operator.

**Weekly (agent, ~1h).** Reconcile pixel conversions against tracker or network
numbers per campaign; a gap over ~15% means decisions are running on a drifted
proxy. Recompute `T` from current payout and approve. Review the creative
graveyard for angles worth reviving. Propose threshold changes with the evidence
that motivates them.

**On economics change (operator → agent).** New payout or approve → recompute
`T` → restate the whole threshold table → update `rules.yaml` and the Meta rules
together, so the two layers never disagree.

## Escalate immediately

- Spend anomaly: any ad set above ~2× its expected daily spend.
- Approve rate dropping while CPA looks stable — the dashboard stays green while
  margin goes negative.
- Account restriction or policy flag.
- Autopilot silent for more than two cycles (no log = assume broken, not idle).
- Tracker and Meta disagreeing by more than ~15%.

## Access

The agent and the autopilot share one System User token scoped to the specific
ad accounts, with campaign-management permission only (see
`marketing-api.md`). Secrets live in the CI/host secret store. Nothing sensitive
goes into the repo, a commit, or a chat message.

Per-environment tokens (test vs live) mean a compromised or misbehaving
environment can be cut off without stopping everything else.
