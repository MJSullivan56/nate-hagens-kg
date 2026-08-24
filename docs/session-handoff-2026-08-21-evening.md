# Handoff: transcript vectorization design + reasoner validation — 2026-08-21 (evening)

Session continuation while Claude Code credits are exhausted for the month.
Everything below is real, tested work done in a sandboxed chat environment —
no repo access, no Oxigraph access, no live corpus. Verify against real data
before treating any threshold here as final.

---

## 1. Transcript-to-vector chunking — designed and tested

**File**: `anchor_transcript_to_shownotes.py` (attached). Reads a show-notes
list plus a raw transcript, outputs `(show_note_timestamp, topic, chunk_text,
is_placeholder, embed_as_single_vector)` rows ready for embedding.

**The core idea**: use the show notes — already curated, already marking real
topic boundaries — to define chunk boundaries, rather than trying to
algorithmically guess at natural breakpoints in raw transcript text.

**Three real design decisions, each backed by testing against two real files
(RR-25, a TGS-provided Reality Roundtable transcript; Frankly-020, a YouTube
auto-generated Frankly transcript)** — see the script's own docstring for
the full reasoning behind each:

1. **Core window, not full-gap assignment.** A transcript turn only belongs
   to a show-note topic if it falls within `min(40s, 0.25 * gap-to-next-topic)`
   of that topic's own timestamp. Content beyond that window is tagged
   `(unlinked transition)`, not silently absorbed into the nearest topic.
   This was a real correction mid-session: the first version assigned
   everything up to the next topic's timestamp, which is technically
   lossless (verified: 0 orphaned turns, 0 empty segments) but produces
   diluted chunks — and since the actual purpose is embedding, dilution
   actively degrades retrieval quality, it doesn't just waste space.
2. **Duration-based branching, not series-label branching.** Episodes under
   35 minutes get embedded as one vector for the whole transcript, not
   chunked. Real evidence: 5 of 6 sampled Franklys ran 12-30 min;
   `Frankly_132` (the six-fronts framework episode, already flagged this
   session as substantial) ran 53.5 min — a clean, empty gap in the real
   data between 30.3 and 53.5 min. Threshold set at 2100s. Keyed on
   `duration_seconds` directly, not `series`, because duration varied
   nearly 2x within "interview" alone in the sample — series is not a
   reliable proxy for length.
3. **TGS-provided and YouTube-auto transcripts are BOTH auto-generated** —
   a real correction to an assumption made earlier in this same thread.
   RR-25's own header states "has not been fully proofed by ISEOF." Neither
   is human-verified; they differ in which tool produced them. TGS
   transcripts carry real `[HH:MM:SS] Speaker:` turns; YouTube transcripts
   are bare `M:SS` caption fragments with no speaker data at all — never
   inferred, left as `speaker: None`, matching the shape pipeline's own
   established precedent (`speaker: null` for the 20 solo Franklys with
   timestamps but no labels). Real ASR content errors in the YouTube
   version (Swedish "öre" → "era", "Force Majeure" → "Force Major") are
   left as-is — correcting them is a separate, human-reviewed task.

**Not yet done**: re-validate the `fraction=0.25, hard_cap=40` window and the
2100s duration threshold against real data at corpus scale — both are
grounded in real testing, but on a small sample (2 files for the window, 16
episodes total for the duration threshold). Revisit once loaded.

**Also not yet done**: deciding whether `(unlinked transition)` chunks get
embedded at all. Recommendation from this session: exclude them from the
primary retrieval index entirely, or keep them in a clearly separate,
secondary index — embedding pure transitional chitchat and leaving it
searchable alongside real content chunks would let a real query spuriously
match against noise.

---

## 2. A real, systematic bio-extraction bug — found and fixed

Every `guest_bios` entry sampled from the `.txt`-batch pipeline output
(`out_txt/` — 5 of 5 checked: Zak Stein, Malin Pinsky, Andrew Millison,
Thomas Crowther, Pedro Prieto) had site-chrome bled into the bio text —
the guest's name repeated on its own line, followed by
`Episode N [date] Recorded on: [date]`. Confirmed **isolated to the `.txt`
batch** (`site:about-sections` extraction) — the `.md`-batch samples checked
(Francis Weller, Fritjof Capra, both from `md_block:about`) were clean.

**The working fix**: don't try to regex-capture an unknown trailing name —
anchor on the guest's own `name` field, already sitting right next to `bio`
in the same record:

```python
pattern = re.compile(
    r'\n\s*' + re.escape(name) + r'\s*\nEpisode \d+.*Recorded on:.*$',
    re.DOTALL
)
cleaned = pattern.sub('', bio).rstrip()
```

Verified clean across all 5 affected records — first attempt (blind
`(.+?)` capture instead of anchoring on the known name) had a real bug,
over-matching on Malin Pinsky's bio because it has internal paragraph
breaks using a single `\n`, the same separator the trailing chrome uses,
and there's no earlier "Episode" occurrence to stop the non-greedy capture
early. Caught by checking `captured_name == name field` as a sanity check,
not by assuming a passing regex test proved correctness.

**Not yet done**: run this across the full 358-file corpus. Should be a
five-minute job once Code time or any terminal access returns — it's pure
Python/PyYAML, no repo dependency beyond the YAML files themselves.

---

## 3. ELT, not ETL — decided, with reasoning

Load raw YAML records into DuckDB completely as-is (bio-bleed junk, ASR
errors, `_site_divergence` conflicts, all of it) into `*_raw` tables. Build
cleaned views/tables on top via SQL, never overwriting raw. Reasoning:
every real bug found this session (bio-bleed, the truncated Wikipedia URL
in Capra's show notes, the `ReliabilityTier`/`ReliabilityType` reasoner
inconsistency) was found by inspecting *loaded* data — a pre-load transform
would very plausibly have silently swallowed some of these before anyone
saw them, the same way the first bio-fix attempt would have shipped wrong
if it hadn't been checked against real output.

Transcript full text stays in its own separate table
(`transcripts_raw(record_id, full_text)`), joined by `record_id`, not
embedded inline — keeps ordinary metadata queries fast, and makes the
copyright boundary `emit()` already enforces (no full text by default) a
physical one, not just a flag to remember.

---

## 4. Reasoner validation — real progress, genuinely unfinished

Ran HermiT (via `owlready2`, confirmed working in this sandbox — Java +
the reasoner jar both present) against the real merged graph.

**Confirmed and fixed**: `tgs:Source.CalDECCaliforniaDoughnutReport` in
`sources.ttl` carried a stale, pre-rename value —
`thinkr:ReliabilityTier.Authoritative` instead of
`thinkr:ReliabilityType.Authoritative` — the exact category of bug
`compute_confidence.py`'s own docstring documents fixing elsewhere. Real,
silent downstream effect: `compute_confidence.py`'s own logic takes
whatever `reliabilityTier` value is present and compares it against the
correctly-named constants, so this source's Evidence would never count as
"Reputable-or-better" despite clearly being meant as the top tier.

**NOT resolved**: the graph is still inconsistent after that fix. A first
bisection attempt to isolate the remaining cause had a real logic bug —
it narrowed based on one half's HermiT result without ever verifying the
*other* half still reproduced the inconsistency, so it converged on
`works.ttl` without real evidence that's actually where the problem is.
Every step in that flawed run reported "consistent," which itself is the
tell that something requires multiple files together to reproduce, not a
single-file bisection.

**Real, usable groundwork already in place** for whoever picks this back
up: HermiT runs cleanly in this environment once `xsd:date` and
`xsd:gYear` literals (and any `rdfs:range` declarations pointing at those
datatypes) are stripped from the graph first — neither is in HermiT's
supported OWL 2 datatype map, and this isn't optional, it crashes the
reasoner entirely otherwise. The stripping + owlready2 invocation code
both work; only the bisection needs a real fix (verify both halves at
each step, not just one, before deciding which half to keep narrowing
into).

---

## 5. Real cross-references confirmed independently this session

Worth having on record since they're real, if small, wins:

- `TGS_10` (Nora Bateson)'s own `scopeNote` flagged `warmdatalab.net` as
  "distinct from" the Bateson Institute's main site, based on inference —
  Frankly-020's real header confirms this directly: both `warmdata.life`
  and `warmdatalab.net` appear as separate, real, deliberately distinct
  links.
- `TGS_138` (Fritjof Capra)'s real YouTube URL (`sPVnR-FiQ4k`) surfaced in
  the `.md`-batch scrape but was never added to the graph's own
  `hasReplay` — small, real backfill item once loading happens.
- The Energy Blind animated-series `credits` field in the scraped YAML is
  a word-for-word match to what was hand-built into
  `Series.GreatSimplificationAnimatedSeries` earlier this session — good
  independent confirmation the manual build was accurate, though the
  scraped version's structured `role`/`name` pairs are cleaner than the
  graph's own flat `dct:contributor` literals; worth having the loader
  preserve that structure rather than flattening to match the less-good
  original.

---

## 6. Open items for next session (Code or otherwise)

1. Run the bio-name-anchor fix across the full corpus.
2. Re-validate the chunking window and duration threshold at corpus scale.
3. Decide whether `(unlinked transition)` chunks get embedded at all.
4. Fix the bisection script's real logic bug, find the second reasoner
   inconsistency.
5. Draft the concrete OWL axiom list (functional properties, real
   `owl:disjointWith`, inverses) in plain language for review before
   Protégé/HermiT work resumes at scale — flagged as needed back in the
   Phase 1.5 migration-prompt discussion, still not done.
6. Check whether the truncated-URL bug (missing closing paren on a
   Wikipedia link in Capra's show notes) is a one-off or systematic
   across the corpus.
