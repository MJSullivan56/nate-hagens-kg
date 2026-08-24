# extraction/shape/ — episode records from the hand-enriched Markdown transcripts

Turns the 57 hand-enriched `.md` files in `extraction/transcripts_text_cache/`
into shaped YAML/JSON episode records, reports what is missing, and fills the
gaps from the canonical source (the episode page on thegreatsimplification.com).

This is the staging layer for the eventual queryable DuckDB — one record per
episode, with people, dates, URLs, keywords, show-notes links, and (opt-in)
speaker-segmented transcripts as separate addressable fields.

The `.txt` files in the same folder are un-enriched raw dumps and are ignored
throughout.

## The shape is data, not code

`episode_shape.yaml` is the single source of truth for what an episode record
contains. Every field declares its type, whether it is required, its extraction
sources **in priority order**, and its normalization steps. `shape_lib.py`
reads that file and drives extraction from it, so adding a field is normally a
one-file edit.

Every emitted record carries a `_provenance` block naming which source won for
each field, and a `_gaps` list naming required fields still unfilled.

## Conflict policy

**The hand-curated `.md` is authoritative.** Site sources are listed last in
every field's `sources` and exist to fill blanks only. Where the site disagrees
with a value the `.md` already has, the `.md` wins and the disagreement is
recorded in the record's `_site_divergence` block rather than overwriting
anything. This matters because some `.md` show-notes tables are deliberately
*not* reproductions of the site's links — TGS-002's table, for instance, is
substitute reference material gathered because that episode published no real
per-topic links.

## Usage

```bash
# 1. one-time: pull the site's episode catalog from its WordPress REST API
python extraction/shape/fetch_episode_pages.py --catalog

# 2. fetch the episode pages (honors the site's Crawl-delay: 10 -> ~9 min)
python extraction/shape/fetch_episode_pages.py --fetch

# 3. fetch YouTube watch pages for publish dates and durations
python extraction/shape/fetch_episode_pages.py --youtube

# 4. parse the cached HTML into site_cache/site_values.json (free, rerunnable)
python extraction/shape/fetch_episode_pages.py --extract

# 5. see what is complete and what is still missing
python extraction/shape/build_episodes.py --report

# 6. emit the records
python extraction/shape/build_episodes.py --out extraction/shape/out --format yaml
python extraction/shape/build_episodes.py --out extraction/shape/out --format json
python extraction/shape/build_episodes.py --out ... --with-transcript   # adds full text
python extraction/shape/build_episodes.py --gap-csv extraction/shape/gaps.csv

# 7. optionally write the fetched data back into the .md files
python extraction/shape/patch_md.py --diff     # dry run, show diffs
python extraction/shape/patch_md.py --apply    # edit in place
```

Steps 1–4 hit the network; 5–7 are local and cheap. The HTML cache means
re-parsing never re-fetches.

## Result of the first full run (2026-08-21)

Before / after, across all 57 `.md` files:

| | before | after |
|---|---|---|
| `youtube_url` present | 10 | 56 (+1 confirmed absent) |
| `title` present | 52 | 57 |
| `webpage_url` present | 56 | 57 |
| `published_date` present | 52 | 57 |
| show-notes rows with no external link | 444 | 4 |
| files with stray NUL bytes | 24 | 0 |
| transcripts parsed into speaker turns | 17 | 49 |
| speaker turns extracted | 2,599 | 9,529 |

Totals now in the shaped records: 2,533 show-notes rows carrying 3,919 external
links, 6 normalized keywords, 71 distinct speaker labels, 37 transcript chapters.

Still open, and why:

- **TGS-024 has no YouTube video.** Recorded in `known_absent.yaml` — its page
  carries no video link and four search formulations found nothing, while
  neighbouring episodes surface readily. Reported as CONFIRMED ABSENT, not as a
  gap.
- **4 show-notes rows still have no link** — the site itself published none for
  those timestamps.
- **8 transcripts yield no speaker turns.** The 4 animated videos are narrated
  with no speaker labels at all; Frankly 47/80/151 and RR-13 are continuous
  prose broken only by `## Chapter N:` headings (captured as
  `transcript_chapters` instead). No speaker attribution exists in the source to
  extract.
- **Speaker labels are not yet reconciled.** "Art Berman" and "Arthur Berman"
  both appear, as do bare first names. Person-level dedup is a DuckDB-stage
  concern and matches the alias problem already logged in the repo's `CLAUDE.md`.

## The .txt batch (301 files, transcript only)

Second phase, started 2026-08-21. These files contain **nothing but transcript**
— no URL, title, date, keyword, show note, guest, or description. So the
conflict policy above has nothing to arbitrate here: the episode page is the
only source for everything except the transcript itself.

```bash
# resolve filenames to episode pages — offline, instant, no network
python extraction/shape/txt_pipeline.py --all --resolve-report
python extraction/shape/txt_pipeline.py --all --resolve-csv extraction/shape/txt_resolution.csv

# pilot a reproducible random sample end to end before committing to all 301
python extraction/shape/txt_pipeline.py --pilot 10 --seed 20260821 --run \
    --out extraction/shape/out_txt_pilot

# the full batch (~50 min at the 10s crawl delay)
python extraction/shape/txt_pipeline.py --all --run --out extraction/shape/out_txt
```

### The filename numbers cannot be trusted

This is the whole difficulty of the batch. Nine episode-number collisions exist
among the 301 files, and eleven filenames carry a number that points at the
wrong episode:

| filename says | actually is |
|---|---|
| `TGS-046-PatrickOphuls` | 47-patrick-ophuls |
| `TGS-060-JonathanHaidt` | 59-jonathan-haidt |
| `TGS-097-HelenThompson` | 98-helen-thompson |
| `TGS118LutherKrueger` | 119-luther-krueger |
| `TGS140StefanRahmstorf` | 141-stefan-rahmstorf |
| `TGS175Jean-MarcJancovici` | 84-jean-marc-jancovici |

But the number cannot simply be *ignored* either — many guests appear on several
episodes (Daniel Schmachtenberger on eight, Art Berman on six, Chuck Watson on
five), so the name alone is ambiguous and only the number separates them:

| filename | correct answer | the trap |
|---|---|---|
| `TGS-017-ChuckWatson` | 17-chuck-watson-nuclear-war | not 04-chuckwatson |
| `TGS148DickGephardt` | 148-richard-gephardt | not 01-dickgephardt |
| `TGS-003-ArtBerman (first interview)` | 03-arthurberman | not 44-art-berman |

`resolve.py` therefore scores both signals — fuzzy name similarity plus a bonus
when the number agrees — and overrides the number only when the strong-name
alternatives all describe the *same identity*. When they carry different names
they are false friends from a shared title phrase ("How to Think About the
Future Part 5" resembles parts 1–4 without being any of them) and the number
wins. Below its similarity floor it resolves nothing at all rather than emitting
a confident-looking guess; those go to `manual_overrides.yaml` for a human.

### Resolution verifies itself

The pilot's most useful outcome: resolution can be checked automatically and for
free, because two independent sources name the same person. The episode **page**
names the guest; the **transcript** names its own speakers. Neither depends on
the filename that drove the resolution, so agreement confirms the right page was
fetched.

That is what makes an off-by-one safe to accept without human review —
`TGS-060-JonathanHaidt` resolves to episode 59, and the transcript's speaker
really is Jonathan Haidt. The check runs on every `--run` and prints
`agree` / `DISAGREE` / `no-guest` counts; a DISAGREE means the wrong page was
fetched.

### Two transcripts must never claim the same page

Each transcript is a distinct episode, so a collision means at least one
resolution is wrong. This happened for real: both Jean-Marc Jancovici
transcripts landed on `84-jean-marc-jancovici`, because the site's *other*
Jancovici episode has an unnumbered slug
(`jean-marc-jancovici-sobriete-vs-poverty-...`) whose long trailing subtitle
held name similarity to 0.80 — just under the floor.

`resolve_collisions()` gives the page to the highest-confidence claimant and
re-resolves the rest with taken pages excluded. Where that leaves no candidate,
the file becomes unresolved and goes to `manual_overrides.yaml` — which is what
happened here, settled by reading the page's own label: `Ep 175 | Jean-Marc
Jancovici`.

> Possible future improvement: `#epi_label` carries the episode number even when
> the slug does not. It can't drive resolution (you'd have to fetch the page to
> read it) but it would make an excellent post-fetch assertion — if the label's
> number disagrees with the resolved number, something is wrong.

### Status — full batch complete (301/301)

| field | coverage |
|---|---|
| title, webpage_url, published_date, recorded_date, description, keywords, show_notes, transcript_pdf_url | **301/301** |
| youtube_url | 273/301 |
| duration_seconds | 272/301 |
| guests / guest_bios | 208/301 (Franklys are mostly solo) |
| spotify_url | 156/301 (older pages predate the platform buttons) |

**13,405 show-notes rows carrying 18,781 external links.** No duplicate episode
numbers, no duplicate slugs, nothing unresolved.

Verification (page's guest vs transcript's speakers, or page title vs transcript
for guest-less episodes): **197 agree, 102 title-agree, 0 disagreements**, 1
title-mismatch — `Frankly-005-FAQsfromEpisodes1-25...` → `frankly-05-faqs-on-episodes-1-25`,
which is plainly correct; the title check is simply weak on a Q&A episode whose
title words are never spoken.

Eight filenames had their episode number corrected from the resolution. The
record keeps the original under `_filename_episode_number`, and `_provenance`
records that the number came from the resolver — otherwise two records would sit
at "episode 46" and corrupt any number-keyed join.

### The output directories

| directory | what | count |
|---|---|---|
| `out/` | records from the 57 hand-enriched `.md` files, YAML | 57 |
| `out_json/` | the same 57 records, JSON | 57 |
| `out_txt/` | records from the 301 transcript-only `.txt` files | 301 |

Different **source batches**, not different stages — `out/` is phase 1, `out_txt/`
is phase 2. 13 episodes appear in both, because a `.md` and a `.txt` transcript
exist for the same episode; dedupe on `webpage_url` (the canonical page), not on
`record_id`, when loading into DuckDB.

**All three are gitignored and wiped on rebuild.** Nothing hand-entered should
live in them — put it in `manual_overrides.yaml`, which is tracked. That is why
`podcast_mp3_url` is an override field rather than an edit to the emitted YAML.

### Audio-only episodes: 28 have no YouTube video at all

Resolved 2026-08-21. The 28 interviews that produced no `youtube_url` are not
missing data — they were **never published to YouTube**. All fall in one era
(Jan 2022 – Feb 2023, episodes 5–56), their pages embed a Libsyn audio player
instead of a video, and a YouTube search returns only short CLIPS uploaded months
later, which the date-corroboration check correctly refuses.

MJSullivan collected the Libsyn MP3 URLs by hand. They live in
`manual_overrides.yaml` as `podcast_mp3_url`, alongside
`series: podcast_interview` to mark the format. With those in place **301/301
records carry a media link** (273 YouTube + 28 MP3).

So `youtube_url` being absent on a `podcast_interview` record is correct, not a
gap — query `youtube_url OR podcast_mp3_url` for "how do I watch/listen to this".

### Superseded: the YouTube worklist

`youtube_worklist.csv` was generated on the assumption those 28 episodes had
videos that simply hadn't been found. They don't — see above. The worklist is
obsolete; `manual_overrides.yaml` holds the MP3 URLs instead. `youtube_url:` is
still accepted as an override field if a video ever does turn up.

### Transcript conventions in the .txt batch

Four speaker-label styles occur and all four are parsed:

| style | files |
|---|---|
| `[00:00:00] Nate Hagens: text` | 158 |
| `Nate Hagens (00:00:02):` then text on the next line | 115 |
| `Nate Hagens: (00:02)` then text | few |
| `[00:00:00] text` — timestamps but no speaker (solo Franklys) | 24 |

The last group gets `speaker: null` rather than an assumed attribution — the
timestamped segmentation is worth keeping, the guess is not. 298 of 301 files
parse into turns (49,333 total); the 3 that do not have no timestamps at all.

## What the corpus actually looked like

Worth recording, because the variance is the reason this is shape-driven rather
than a single regex pass. Across 57 files:

| Field | Label spellings found in the wild |
|---|---|
| webpage | `WEBPAGE:`, `Webpage:`, `WEBSITE:` |
| youtube | `YOUTUBE:`, `Video:`, or absent (47 of 57) |
| keywords | `KEYWORDS:`, `Keywords:`, `KEYWOREDS:` (sic), or unlabeled |
| description | `## Description`, `Description`, `Show Summary`, or no heading |
| show notes | markdown table / plain lines + bare URLs / plain lines with no links |

Other things that had to be handled specifically:

- **Run-together keywords.** The episode page renders topic tags as adjacent
  `<span class="pill">` elements with no separator, so copy-pasting them yields
  `Economics And MonetarySystems ScienceGeopolitics`. Splitting that back into
  three tags is only possible against a known vocabulary, which is why the shape
  carries a `keyword_vocabulary` list.

- **Stray NUL bytes.** 24 files contain `0x00` bytes left over from copying out
  of the source PDFs. Python decodes them fine, but `grep` classifies such a
  file as binary and skips it *silently* — which is how 24 of these 57 files
  went missing from the first survey of this corpus. `patch_md.py` strips them.

- **Titles are absent from RR/TGS files.** Franklys fuse label and title on one
  line (`Frankly 151 | Protect the Irreversible: ...`), but Reality Roundtable
  and interview files carry only a bare label (`Reality Roundtable 19`,
  `Episode 220`). Their real titles exist only on the webpage.

- **Do NOT assume a Frankly has no guest.** Most are solo, but some feature
  one — Frankly 20 is "Staying Warm Data with Nora Bateson". For those, the
  title is the *only* place the guest is named: the page's byline heading reads
  just "Nate Hagens" regardless of series, and Franklys never carry an
  "About &lt;Name&gt;" bio block. So `guests` merges three signals (bio headings,
  page byline, and the channel's `with <Name>` title convention) and drops any
  name equal to the host rather than trusting any one source.

- **Slugs are not guessable.** Episode 1 is at `/episode/01-dickgephardt`
  (zero-padded), episode 220 at `/episode/220-art-berman` (not padded),
  roundtable 19 at `/episode/reality-roundtable-19`, and some older roundtables
  at `/episode/rr01-berman-michaux-prieto`. Franklys are a *separate WordPress
  post type* at `/frankly-original/<n>-<slug>`. Hence the catalog step — it
  enumerates all 416 entries from the REST API instead of guessing.

- **One misplaced marker.** Frankly-154 has a stray `# TRANSCRIPT` heading above
  its disclaimer and show-notes table, with the real one further down. The
  parser splits on the *last* marker, since show notes always precede the
  transcript.

- **The YouTube link needs an anchored selector.** Episode pages contain many
  `youtube.com` URLs inside their show notes (RR-19 has three). A bare regex
  picks the wrong one. The canonical link is the only one carrying
  `id="ep_lnk_yt"`.

## Files

| File | Role |
|---|---|
| `episode_shape.yaml` | the shape: fields, sources, normalizers, vocabulary |
| `shape_lib.py` | segmentation, extractors, normalizers, record assembly |
| `build_episodes.py` | CLI: build records, emit YAML/JSON, print the gap report |
| `fetch_episode_pages.py` | CLI: catalog, fetch pages/YouTube, extract site values |
| `patch_md.py` | CLI: write fetched data back into the `.md` files |
| `site_cache/` | fetched HTML + `catalog.json` + `site_values.json` (gitignored) |
| `out/` | emitted records (gitignored) |

`site_cache/` and `out/` are gitignored: they derive from the copyrighted
episode text, consistent with `transcripts_text_cache/` itself being ignored.
The scripts and the shape template are committed.

## Toward DuckDB

The emitted records are deliberately shaped for a straightforward relational
load — scalar fields become episode columns, and the list/table fields become
child tables keyed on `record_id`:

```
episodes(record_id, series, episode_number, title, webpage_url, youtube_url,
         youtube_video_id, spotify_url, apple_podcasts_url, podlink_url,
         transcript_pdf_url, published_date, recorded_date, duration_seconds,
         host, description, disclaimer, source_sha256, ...)
episode_keywords(record_id, keyword)
episode_guests(record_id, name, bio)
episode_credits(record_id, role, name)
show_notes(record_id, timestamp, seconds, topic)
show_note_links(record_id, seconds, label, url)      -- the queryable URL index
transcript_turns(record_id, seq, speaker, timestamp, seconds, text)
```

That covers the query targets named for this work: person, date, URL, keyword,
title. `show_note_links` is the one to watch — it is where "which episodes cite
this source" gets answered, and it is the field that was most incomplete in the
hand-enriched files.
