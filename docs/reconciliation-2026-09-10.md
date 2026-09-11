# Reconciliation: wwns-candidate-pipeline-01.md against wwns-topic-coverage-tracker.md

Checked all 10 candidates from the standalone pipeline (built in ignorance of
this tracker's existence) against the real 14 already tracked here — by
underlying source, not just topic similarity. Result: **1 fulfills an
explicitly flagged gap, 1 is redundant and should be folded in rather than
stand alone, 8 are genuinely new.** The standalone pipeline document should
be retired after this; nothing in it should keep living as a separate file.

---

## Fulfills an already-flagged gap — add directly

**Loneliness/social isolation (WHO Commission on Social Connection: ~871,000
deaths 2014–2019 associated with loneliness/isolation; newer 2026 survey
data shows it's now highest among 18–24 year-olds, not the elderly).**

The existing tracker's own "facets already well-evidenced" section
explicitly flagged this as an open need: *"real candidates exist but none
yet at the same source-quality tier as Carbon Majors/DGAP; recommend going
to a primary source, e.g. the 2023 US Surgeon General advisory or the WHO
Commission on Social Connection report, rather than a secondary summary."*
This candidate is exactly that primary source. Add as:

| # | Source | Real topics touched | Notes |
|---|---|---|---|
| 15 | WHO Commission on Social Connection report + 2026 age-skew survey data | #9 (strong, loneliness facet — now at primary-source tier), #4 (moderate) | Resolves the loneliness facet's own flagged source-quality gap directly. The age-skew finding (now highest among 18-24s, not the elderly) is itself a real, current, counter-intuitive hook distinct from the report's own headline mortality figure — worth leading with the surprise, not just the death toll |

---

## Redundant with an existing candidate — fold in, don't add separately

**AI data center electricity demand (Gartner: 565 TWh in 2026, AI-optimized
servers exceeding conventional draw by 2027; NERC reliability-risk paper).**

This shares its core source with the existing candidate #14 (NERC + DOE grid
reliability). Standing up a separate candidate here would cite NERC twice
under two different framings — exactly the kind of redundancy
`wwns-methodology.md` §6 is meant to catch. **Recommendation: fold the
Gartner 565 TWh figure into #14 directly as a supplementary AI-specific data
point**, rather than create #16. #14 already has the real reliability-risk
argument; this just sharpens *why* — the AI buildout specifically — with a
concrete number.

---

## Genuinely new — no real overlap with the existing 14

| # | Source | Real topics touched | Notes |
|---|---|---|---|
| 16 | IIF Global Debt Monitor (global debt ~$348T, ~308% of GDP, AI-linked corporate borrowing named as a driver) | #3 (strong) | Distinct from existing #8 (Brookings/Auerbach & Gale) — that candidate is US federal budget specifically; this is global aggregate debt with a real, current AI-financing angle #8 doesn't cover |
| 17 | *Science Advances* Feb 2026 — compounding ecological threats (3,129 wildlife populations, multi-threat decline compounds faster than any single threat) | #6 (strong), #5 (moderate — the compounding-threat mechanism itself is a genuinely reusable systems pattern) | Distinct mechanism from both existing #6 candidates (Carbon Majors/water, permafrost) — this is about threat-stacking as its own phenomenon, not a new instance of ecological damage |
| 18 | Oxfam Jan 2026, "Resisting the Rule of the Rich" (billionaire wealth $18.3T, ~1.9M tonnes CO2/billionaire/year) | #4 (strong), #1 (moderate) | No existing candidate pairs wealth concentration with a direct per-capita emissions figure this specifically |
| 19 | Bulletin of the Atomic Scientists, Jul 2026 — AI/SMR nuclear timeline gap vs. corporate announcements | #1 (strong), #8 (moderate) | Pairs naturally with #14/16(folded)'s own grid-demand argument as the supply-side skeptical counterweight — worth citing together if both get used in the same piece, per the omission-by-scope technique already established for this series |
| 20 | *Nature Communications* Feb 2026 — fourth global coral bleaching event (98 of 102 reef countries affected, most severe on record) | #6 (strong) | Distinct from Carbon Majors/water and permafrost — a third, genuinely different #6 angle, not a repeat |
| 21 | Monash University Jun 2026 — ultra-processed food directly linked to measurably worse attention, independent of overall diet quality | #4 (strong), #8 (moderate) | Genuinely rare case: validates `tgs:Concept.UltraProcessedInformation`'s own central analogy literally rather than just thematically — ultra-processed *food* damaging the same attentional capacity the concept argues ultra-processed *information* damages by a different mechanism |
| 22 | 2026 AI governance landscape (EU AI Act full enforcement, Council of Europe AI Treaty, Hiroshima AI Process — converging on "fragmented, no binding global ceiling") | #8 (strong), #7 (moderate) | Distinct from existing #4 (space resource extraction, touches #8 only moderately) — this is the first candidate centered on AI governance mechanism specifically |
| 23 | Real-time 2026 Strait of Hormuz crisis (US strikes on IRGC-linked tankers, Brent near $97-100/barrel, transits down from ~130/day to ~10/day) | #7 (strong), #1 (moderate) | Distinct from existing #2 (DGAP, Russia/Ukraine) — different conflict, different region. Live/acute rather than retrospective; would need the "update an acute situation" framing discussed separately, not a standard candidate treatment |

---

## Updated cumulative coverage (14 existing + 7 new = 21 real candidates; #16 folded, not counted separately)

| Topic | Prior count | New candidates touching it | New count |
|---|---|---|---|
| #1 Energy | 2 | #18 (mod), #19 (strong), #23 (mod) | 5 |
| #2 Overshoot/limits | 2 | — | 2 |
| #3 Monetary/growth | 2 | #16 (strong) | 3 |
| #4 Human behavior/psychopathy | 2 | #15 (mod), #18 (strong), #21 (strong) | 5 |
| #5 Systems/Superorganism | 2 | #17 (mod) | 3 |
| #6 Ecology | 2 | #17 (strong), #20 (strong) | 4 |
| #7 Geopolitics | 3 (4 counting secondary) | #23 (strong) | 4 (5 counting secondary) |
| #8 Technology/complexity | 2 | #19 (mod), #21 (mod), #22 (strong) | 5 |
| #9 Community/localization | 5 | #15 (strong — loneliness facet now primary-source tier) | 5 (upgraded, not expanded) |
| #10 Meaning/agency | 1 | — | 1 |

**#10 (meaning/agency) remains the thinnest topic** — still just the one
entry (the Pew "sour mood" / national-pessimism candidate). None of the
pipeline's 10 candidates touched this directly; worth flagging as the real
priority for the *next* search pass rather than something this
reconciliation happened to fix.

---

## Disposition of the standalone pipeline document

`wwns-candidate-pipeline-01.md` should be retired — its useful content
(candidates #16–23 above, the fold-in note for #14) is now absorbed
directly into the real tracker in this repo's own established format.
Nothing should keep living as a separate, parallel file once absorbed.
