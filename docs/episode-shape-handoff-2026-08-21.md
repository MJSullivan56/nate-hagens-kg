# Handoff: episode-shape pipeline (`extraction/shape/`) — 2026-08-21

Session ran out of credits mid-stream. Everything below is the state as of that
moment, verified by running the code, not from memory.

**Goal of this work:** turn the transcripts in `extraction/transcripts_text_cache/`
into shaped, queryable episode records — the staging layer for a DuckDB anyone can
query by person, date, URL, keyword, or title.

**Where it got to:** both source batches are fully built. 348 distinct episodes,
15,938 show-notes rows carrying 22,700 external links, 58,862 speaker turns. No
unresolved records, no duplicate episode numbers, every record has a media link.

---

## 1. Read these first

| file | why |
|---|---|
| `extraction/shape/README.md` | full mechanics, usage, the corpus-variance catalogue, before/after numbers. **Start here.** |
| `extraction/shape/episode_shape.yaml` | the shape — single source of truth for what a record contains |
| `extraction/shape/manual_overrides.yaml` | every human decision made so far, with the reasoning |
| this doc | state, open items, and the traps |

---

## 2. What exists

All committed (the scripts and the two YAML config files):

```
extraction/shape/
  episode_shape.yaml      the shape: fields, sources, normalizers, vocabularies
  shape_lib.py            segmentation, extractors, normalizers, record assembly
  build_episodes.py       CLI for the .md batch  (57 files)
  txt_pipeline.py         CLI for the .txt batch (301 files)
  fetch_episode_pages.py  catalog + page/YouTube fetching + page parsing
  resolve.py              filename -> episode page matching (the hard part)
  patch_md.py             writes fetched data back into the .md files
  known_absent.yaml       fields confirmed absent at source (not merely unfilled)
  manual_overrides.yaml   human adjudications: resolution + podcast MP3 URLs
  README.md
```

Gitignored, all regenerable — **nothing hand-entered may live here** (see trap #1):

```
  site_cache/   686 files, 51 MB   fetched HTML + catalog.json + site_values.json
  out/           57 records        .md batch, YAML
  out_json/      57 records        .md batch, JSON
  out_txt/      301 records        .txt batch, YAML
extraction/md_backups/             2 tarballs (see §6)
```

---

## 3. Current coverage

### `.md` batch — 57 hand-enriched files → `out/`

| field | coverage |
|---|---|
| title, webpage_url, published_date, description | 57/57 |
| youtube_url | 56/57 (1 confirmed absent) |
| duration_seconds | 56/57 |
| recorded_date, keywords | 53/57 |
| show_notes | 52/57 |
| transcript_pdf_url | 49/57 |
| guests | 42/57 (Franklys/Videos mostly solo) |

2,533 show-notes rows, 3,919 external links. Series: 27 roundtable, 14 interview,
12 frankly, 4 video.

Improvements from the run: `youtube_url` 10→56, linkless show-notes rows 444→4,
files with stray NUL bytes 24→0, speaker turns 2,599→9,529.

### `.txt` batch — 301 transcript-only files → `out_txt/`

| field | coverage |
|---|---|
| title, webpage_url, published_date, recorded_date, description, keywords, show_notes, transcript_pdf_url | **301/301** |
| youtube_url | 273/301 |
| duration_seconds | 272/301 |
| guests | 208/301 |
| podcast_mp3_url | 28/301 |

13,405 show-notes rows, 18,781 external links. Series: 182 interview, 91 frankly,
28 podcast_interview.

**`youtube_url` + `podcast_mp3_url` = 301/301.** Every record has a media link.

### The two batches overlap by 3 episodes

`96-david-holmgren`, `123-the-consumption-pyramid`,
`132-what-to-do-as-the-world-falls-apart` have both a `.md` and a `.txt`
transcript. **Dedupe on `webpage_url`, not `record_id`** — the batches use
different filename conventions for the same episode. Union is 348 episodes.

---

## 4. Traps — read before touching anything

1. **`out*/` and `site_cache/` are wiped and rebuilt.** `txt_pipeline.build()`
   calls `shutil.rmtree(out)`. They are also gitignored. Anything hand-entered
   there is lost on the next run. This already nearly happened: 28 hand-collected
   MP3 URLs were sitting in `out_txt/`. They now live in
   `manual_overrides.yaml`, which is tracked. **Put human input in the override
   file, never in the emitted records.**

2. **`transcripts_text_cache/` is gitignored too** — the source `.md`/`.txt`
   files have no version-control safety net. `patch_md.py --apply` edits them in
   place. Snapshot to `extraction/md_backups/` before any in-place run.

3. **The `.txt` filenames lie about episode numbers.** Eleven point at the wrong
   episode. But the number can't be ignored either — Schmachtenberger appears on
   8 episodes, Berman 6, Chuck Watson 5, so the name alone is ambiguous. See
   `resolve.py`'s docstring; both orderings are wrong and it took three attempts
   to get right. **Do not "simplify" that scoring.**

4. **`emit()` drops the transcript unless `--with-transcript` is passed.** So
   `transcript: 0/301` in a report is not a gap. This is deliberate — it keeps
   copyrighted full text out of the emitted files by default.

5. **The page cache is keyed by transcript, not URL.** If a resolution changes,
   the stale page for the *old* episode would keep being served. `fetch_for()`
   now compares the cached canonical URL and re-fetches on mismatch. Keep that.

6. **A filtered run (`--only`, `--pilot`) must merge, not replace,
   `txt_site_values.json`.** An earlier version truncated the shared file to the
   2 records it was scoped to. Fixed; don't regress it.

7. **Site page structure varies by era** and cost several rounds of bugs:
   headings with and without trailing colons (`Show Summary:` vs `Description`),
   descriptions in `<h3>` instead of `<p>`, player chrome sitting in real `<p>`
   tags, timestamps separated from their dash by markup. All handled — but a new
   era of pages may bring more.

8. **`SequenceMatcher`'s `autojunk` distorts character-level ratios above 200
   chars.** It reported Nora Bateson's bios as 0.04 similar when they are near
   duplicates. Use word tokens and `autojunk=False` for prose comparison.

---

## 5. Open items

### A. Guest-bio reconciliation — designed, not built

The question: one person should have one bio, but bios differ across episodes.
Measured across 214 pages: 127 distinct guests, 24 appearing 2+ times, and **no
repeat guest has a verbatim-identical bio.** By word similarity: 9 near-dup
(≥0.85), 10 edited (0.5–0.85), 5 rewritten (<0.5).

**The delta is data, not error.** Shanna Swan's two bios are topic-tailored — one
leads with reproductive epidemiology, the other (a plastics roundtable) with her
Mt. Sinai post. Merging loses information about how TGS frames a person.

Proposed shape, not implemented:

- **Observation layer (DuckDB):** every bio kept, keyed to its episode, never
  deduped — `episode_guest_bio(record_id, person_key, name_as_published,
  bio_text, bio_sha256, published_date)`. "TGS published this text on this date"
  is settled by the source, so a flat property; no Evidence apparatus needed
  (per the contestable-vs-settled test in `CLAUDE.md`).
- **Canonical layer (graph):** one curated bio on `thinkr:Human`, human-approved,
  with a provenance pointer to the observation(s) it came from.
- **Bridge:** a review queue that classifies variants so only the 5 rewrites need
  a human, not the 9 near-dups. Default candidate = most recent, but *surface
  what the newest bio drops* — Swan's newer bio is 418 chars vs 1,139, so
  most-recent alone loses facts.

**Identity must come first.** You cannot reconcile bios before reconciling
people. Live alias pairs: `Art Berman`↔`Arthur Berman`,
`William E. Rees`↔`William Rees`, plus transcript misspellings like
`Reid Malloy` for Reid Meloy. Recommendation: reuse the existing
`thinkr:AlternateTerm` mechanism rather than inventing a parallel one.

Note this is structurally the **same problem** as the backlogged
Concept-evolution-over-time item ("a single `skos:definition` with no way to say
it changed"). Dated observations + one curated current value answers both —
an argument for designing it once.

### B. DuckDB loader — not started

`README.md` has the target schema. Key tables: `episodes`, `episode_keywords`,
`episode_guests`, `show_notes`, `show_note_links`, `transcript_turns`.
`show_note_links` (22,700 rows across both batches) is the one that answers
"which episodes cite this source".

Two things the loader must handle: dedupe the 3 overlapping episodes on
`webpage_url`, and treat a null `youtube_url` on a `podcast_interview` record as
correct — query `youtube_url OR podcast_mp3_url` for "how do I watch/listen".

### C. Smaller open items

- **11 files yield no speaker turns.** 4 animated videos are narrated with no
  labels; Frankly 47/80/151 and RR-13 are prose broken only by `## Chapter N:`
  headings (captured as `transcript_chapters`); TGS-051, TGS109, TGS171 have no
  timestamps at all. No attribution exists in the source — not a parser gap.
- **20 solo Franklys have timestamps but no speaker labels.** Turns carry
  `speaker: null` deliberately. The episode's `host` is recorded separately, so a
  query can attribute them without the pipeline guessing.
- **4 show-notes rows in the `.md` batch still have no link** — the site
  published none for those timestamps.
- **1 title-mismatch in verification:** `Frankly-005-FAQs...` →
  `frankly-05-faqs-on-episodes-1-25`, plainly correct. The title check is just
  weak on a Q&A episode whose title words are never spoken.
- **`#epi_label` carries the episode number even when the slug doesn't**
  (`Ep 175 | Jean-Marc Jancovici`). It can't drive resolution — you'd have to
  fetch the page to read it — but it would make a good post-fetch assertion: if
  the label's number disagrees with the resolved number, something is wrong.
  Cheap, and would have caught the Jancovici collision automatically.

---

## 6. Backups taken

`extraction/md_backups/` (gitignored — it *is* the episode text):

- `transcripts_md_pre_patch_2026-08-21.tar.gz` — all 57 `.md` files before
  `patch_md.py --apply` ran.
- `out_txt_manual_edits_2026-08-21.tar.gz` — 368 emitted records including the
  28 hand-edited podcast ones, taken before they were migrated into
  `manual_overrides.yaml`.

---

## 7. Resuming

Everything is cached; nothing below hits the network.

```bash
# rebuild both batches from cache and re-run all reports
python extraction/shape/build_episodes.py --report --out extraction/shape/out
python extraction/shape/txt_pipeline.py --all --rebuild --out extraction/shape/out_txt

# confirm the .md patcher is still idempotent (should say 0/57)
python extraction/shape/patch_md.py
```

Expected: 57 and 301 records; verification `197 agree / 102 title-agree /
0 DISAGREE / 1 TITLE-MISMATCH`; patcher `0/57`. **If any of those differ, a
regression crept in** — check §4 before anything else.

To refresh from the site (slow, honors `Crawl-delay: 10`):

```bash
python extraction/shape/fetch_episode_pages.py --catalog   # refresh episode list
python extraction/shape/txt_pipeline.py --all --run --out extraction/shape/out_txt
```

Suggested next step: **item B (the DuckDB loader)**. The records are stable, the
schema is sketched, and it is the first thing that makes any of this queryable —
which was the point. Item A is a bigger design commitment and blocks on the alias
table, so it is worth doing second.

---

## 8. Decisions made this session (don't re-litigate silently)

| decision | rationale |
|---|---|
| The hand-curated `.md` is authoritative; site fills gaps only | some `.md` show-notes tables are deliberately *not* the site's links (TGS-002's are substitute references) |
| Fetched data patched back into the `.md` files in place | MJSullivan's call; `patch_md.py` is idempotent and backed up |
| Site's keyword spelling is canonical (`Economics and Monetary`, lowercase "and") | the hand-typed files used "And"; folding to the site's form gives 6 clean values |
| Resolver refuses to guess below its similarity floor | a confident-looking wrong answer is worse than an admitted gap; humans adjudicate via the override file |
| Non-person speaker labels (`Voiceover`, `Outro`) excluded from `transcript_speakers` but their turns kept | that field is a person index; the spoken text is still real content |
| Franklys are **not** assumed solo | Frankly 20 is "Staying Warm Data with Nora Bateson"; the title's `with <Name>` is the only guest signal for those |
| Resolved episode number overrides the filename's | otherwise two records sit at "episode 46" and corrupt number-keyed joins |
| Bio reconciliation deferred entirely — every bio loads into `episode_guest_bio` untouched, no merge/canonical step yet | "most recent wins" is unsafe for genuine factual conflicts, not just tone/emphasis differences (see §A); reconciliation needs a real review pass, not an automatic default |
