# Phase 0 review — three bootstrap episodes

**Built 2026-08-26 from the three files already in `pilot/output/`. Pure local
reading; no API calls, no new extraction.** Everything below is derived from
those files plus the token counts of two API calls made earlier that were never
written to disk (noted in §3).

Episodes: **TGS-127** (Ed Conway, Interview, 104.7 min) · **RR-24** (Space
Colonization, PanelDiscussion, 95.2 min) · **Frankly-145** (How to Think About
the Future Pt 3, Monologue, 24.3 min).

---

## 1. All 48 flagged corpus problems

These are the `_LIKELY_ASR_ERROR` / `_NAME_VARIANT_CONFLICT` candidates — the
concrete output of the reference-only NER pass. Nothing here is minted; this is
a review queue.

**Before the table: the 48 rows are not 48 findings.** Read the counts honestly:

| bucket | rows | what it actually is |
|---|---|---|
| **A — genuine transcription corruption** | **34** | Real ASR damage. The highest-value output; several are errors nobody had found by hand. |
| **B — one finding, repeated 7×** | **7** | All seven are `Don`. The speakers address DJ White as "Don" throughout; the metadata only knows "DJ White". One real identity finding, surfaced seven times because there is no cross-chunk dedup. |
| **C — legitimate variants, not errors** | **5** | `Ed Conway` (vs Edmund — a nickname), `CO2` (vs carbon dioxide — a synonym), `aluminium` (vs aluminum — a spelling), `U S` (a spacing artifact), `Udden Wentworth scale` (correct name, missing hyphen). Flagging these is over-triggering. |
| **D — chunk/topic misalignment** | **2** | A *different class of signal entirely* — see §2. |

So: **~35 distinct real findings from 48 rows**, of which ~34 are transcription
corruption. Precision on bucket A is high; the flag mechanism's weakness is that
it conflates "the transcript is damaged" with "this name has two legitimate
forms".

| # | ep | at | conf | flag type | candidate | what the model said, and my read |
|---|---|---|---|---|---|---|
| 1 | RR-24 | 00:00 | 0.40 | `Concept · ASR?` | **Pologic drift netting** | 'the world's largest and most destructive global fishery, Pologic drift netting' — 'Pologic' appears to be a transcription error for 'pelagic' |
| 2 | RR-24 | 03:48 | 0.25 | `Concept · ASR?` | **FBOs** | 'a mission concept study to put a spacecraft on FBOs, to test general relativity' — 'FBOs' is not a standard term; likely mis-transcription of 'NEOs' (near-Earth objects) or 'Phobo… |
| 3 | RR-24 | 03:48 | 0.80 | `Work_Publication · VARIANT?` | **The Hitchhiker's Guide to the Galaxy** | Transcript renders it 'Hitchhiker's Guided The Galaxy' — garbled ASR of the well-known title |
| 4 | RR-24 | 13:05 | 0.60 | `Person · VARIANT?` | **Don** | 'Don, I've known you for a long time.' Episode metadata lists guests as Tom Murphy and DJ White; 'Don' likely refers to DJ White (possibly 'Don' being his first name behind the ini… |
| 5 | RR-24 | 17:52 | 0.15 | `Concept · VARIANT?` | **Corn ethanol EROI** | Curator-supplied chunk topic, but nothing in this chunk mentions corn, ethanol, or EROI; the text is entirely about lifecycle environmental cost per human-hour in space. Possible c… |
| 6 | RR-24 | 18:00 | 0.40 | `SpaceMission · ASR?` | **serious wreck mission** | "I think the, was serious wreck mission and returned it to earth" — describes an asteroid sample-return mission; garbled phrase almost certainly a speech-recognition mangling of a … |
| 7 | RR-24 | 21:42 | 0.30 | `Concept · ASR?` | **Remote modus** | 'but it's energetic. Remote modus doesn't work' — almost certainly a mis-transcription of 'energetic remoteness' |
| 8 | RR-24 | 21:42 | 0.25 | `Work_Publication · ASR?` | **Reality 101** | 'which I think tall our aliens from reality 1 0 1 wanted to call' — passage is badly garbled; 'reality 1 0 1' may be 'Reality 101' (a course/series name) but the surrounding words … |
| 9 | RR-24 | 24:17 | 0.15 | `Acronym · ASR?` | **FWU** | 'but I like fu I'm guessing that's FWU' — garbled speech fragment; the acronym is not expanded anywhere and appears to be a transcription error for an unknown term. |
| 10 | RR-24 | 32:50 | 0.20 | `Unknown · ASR?` | **san's** | "you don't go full stop... that's what san's for" — garbled; unclear intended word or name, possibly not an entity at all |
| 11 | RR-24 | 35:00 | 0.30 | `Technology · ASR?` | **iron propulsion** | 'It's gonna have to have maybe iron propulsion' — likely mis-transcription of 'ion propulsion' in a discussion of exotic space travel tech. |
| 12 | RR-24 | 43:50 | 0.50 | `Person · VARIANT?` | **Don** | Nate Hagens says 'Don, I don't know what more you could add to that' immediately before DJ White speaks — likely an ASR mis-rendering or an alternate/nickname for the guest labeled… |
| 13 | RR-24 | 43:50 | 0.75 | `Unit_Concept · ASR?` | **sievert** | Rendered variously as 'milli verts', 'seavert', 'seabird', 'Seavers' — all appear to be ASR corruptions of the radiation dose unit sievert/millisievert within the same chunk |
| 14 | RR-24 | 50:06 | 0.50 | `Person · VARIANT?` | **Don** | 'Don do you have anything to add to that?' and 'Don in past years' — Nate addresses DJ White as 'Don', conflicting with the metadata name 'DJ White'. Possibly a nickname or ASR mis… |
| 15 | RR-24 | 1:00:25 | 0.90 | `Technology_Instrument · ASR?` | **James Webb Space Telescope** | "images we're getting back from the James we, space telescope" — rendered as 'James we, space telescope', almost certainly an ASR mangling of 'James Webb Space Telescope'. |
| 16 | RR-24 | 1:00:25 | 0.70 | `Material · ASR?` | **regolith** | "scrape off hundreds of square miles of the top regular" — 'regular' is very likely an ASR error for 'regolith' (lunar surface material). |
| 17 | RR-24 | 1:00:25 | 0.50 | `Concept · ASR?` | **bunkum** | "That's just bunkers." — 'bunkers' appears to be an ASR error for 'bunkum' (nonsense); flagged as corpus problem rather than treated as an entity. |
| 18 | RR-24 | 1:02:45 | 0.80 | `Person · VARIANT?` | **Arthur Clark** | 'had Arthur Clark writing about space elevators while funding my work' — likely Arthur C. Clarke; surname rendered without final 'e' and missing middle initial, possible transcript… |
| 19 | RR-24 | 1:07:02 | 0.55 | `Person · VARIANT?` | **Don** | Nate says 'Science tethered spiritual appeal there, Don' while addressing DJ White — likely DJ White's first name or an ASR variant; conflicts with the 'DJ White' rendering used in… |
| 20 | RR-24 | 1:07:02 | 0.30 | `Concept · ASR?` | **citation friends** | 'you've shared a lot of other stories with me over the years about your citation friends' — in a conversation about dolphins, 'citation' is likely a mis-transcription (possibly 'ce… |
| 21 | RR-24 | 1:10:47 | 0.70 | `Concept · ASR?` | **citations** | 'dozens of species of citations developed cerebral cortices' — almost certainly 'cetaceans' misheard as 'citations'. |
| 22 | RR-24 | 1:18:55 | 0.30 | `Concept · ASR?` | **great wall of fu** | 'There's this great wall of fu that, that is, coming' — appears truncated/garbled; possibly 'great wall of fuel' or an expletive rendering; likely transcription error |
| 23 | RR-24 | 1:19:50 | 0.45 | `Concept · ASR?` | **arc** | 'this idea of having this arc, you know, that can preserve humanity' — almost certainly 'ark' (as in Noah's ark / space ark) misrendered as 'arc' by transcription. |
| 24 | RR-24 | 1:23:25 | 0.45 | `Person · VARIANT?` | **Don** | 'who are maybe Don like you were when you were in your twenties' — the only other guest in metadata is 'DJ White', so 'Don' may be an ASR mishearing of 'DJ' or a different renderin… |
| 25 | RR-24 | 1:27:37 | 0.60 | `Person · VARIANT?` | **Don** | 'Don, I'm gonna give you the closing word. my old friend and co-writer of, three books' — appears to refer to the guest labeled DJ White; name rendered differently in same chunk |
| 26 | RR-24 | 1:32:10 | 0.40 | `Person · VARIANT?` | **Don** | 'Even before Don mentioned giving comfort and talking to this young whale who's dying' — no 'Don' appears in episode metadata; likely refers to co-guest DJ White (possible ASR mish… |
| 27 | TGS-127 | 00:00 | 0.95 | `Person · VARIANT?` | **Ed Conway** | "We did more of the same at a deeper level here with Ed Conway" — short form of 'Edmund Conway' used in same chunk and in episode title metadata |
| 28 | TGS-127 | 00:00 | 0.35 | `Work_Publication · ASR?` | **Teal World** | "author of three books, including most recently, Teal World" — almost certainly a mis-transcription of 'Material World', the book named later in the chunk and in episode metadata |
| 29 | TGS-127 | 00:00 | 0.55 | `Person · ASR?` | **Simon Michaud** | "Olivia Lazard and Simon Michaud on" — likely mis-rendering of 'Simon Michaux', a researcher on mineral requirements for the energy transition; spelling in transcript may be an ASR… |
| 30 | TGS-127 | 18:12 | 0.85 | `Concept_ClassificationScale · VARIANT?` | **Udden Wentworth scale** | "there's something called the Udden Wentworth scale, which says if you go beyond a certain size, then that is now a sand". Curator-supplied chunk topic renders it as 'Wentworth Sca… |
| 31 | TGS-127 | 27:28 | 0.35 | `Species · ASR?` | **Rhino** | "and Rhino, kind of great woolly mammoth, skeletons" — appears mid-sentence oddly; could be an ASR mishearing of 'Rhine' (the river mentioned earlier) rather than the animal |
| 32 | TGS-127 | 33:12 | 0.75 | `Person · ASR?` | **Mark Kalansky** | "The most famous is the one by a guy called Mark Kalansky" — referring to a famous book about salt; likely a transcription of 'Mark Kurlansky', author of 'Salt: A World History'. S… |
| 33 | TGS-127 | 45:02 | 0.70 | `Work_Publication · ASR?` | **iPencil essay** | "on your business card you should have a hyperlink to the iPencil essay" — almost certainly the essay "I, Pencil"; rendered as one word 'iPencil', likely a transcription artifact. |
| 34 | TGS-127 | 46:19 | 0.60 | `Material · VARIANT?` | **aluminium** | Speaker explicitly discusses the 'IUM thing at the end of aluminum' and that UK English says the longer form; transcript renders both pronunciations as 'aluminum', so the intended … |
| 35 | TGS-127 | 46:19 | 0.60 | `Work_Publication · ASR?` | **The Population Bomb** | Transcript reads "the population bond guy" in reference to Paul Ehrlich; 'bond' is almost certainly a mis-transcription of 'Bomb' (Ehrlich's book title) |
| 36 | TGS-127 | 50:28 | 0.60 | `Location_Mine · ASR?` | **Chukicamata** | "I went to this mine called Chukicamata, which is the biggest hole in the world" — likely transcription of the Chilean mine Chuquicamata; spelling appears garbled. |
| 37 | TGS-127 | 53:41 | 0.30 | `Mine · ASR?` | **kata** | 'The tailings dam for kata' — appears to be a truncated/garbled mine name (possibly a Chilean copper mine); transcript gives no full form |
| 38 | TGS-127 | 1:04:57 | 0.20 | `Person · VARIANT?` | **Richard Baldwin** | Curator-supplied chunk topic is 'Richard Baldwin', but this name does not appear anywhere in the transcript chunk text; flagged as metadata/text mismatch |
| 39 | TGS-127 | 1:07:11 | 0.30 | `Concept · ASR?` | **binoculars of the 2030s** | 'what a couple of the binoculars of the 2030s might be' — 'binoculars' makes little sense here; plausibly a mis-transcription of 'bottlenecks' (fits the supply-chain/chokepoint dis… |
| 40 | TGS-127 | 1:08:30 | 0.90 | `Material · VARIANT?` | **CO2** | 'CO2 in canisters'; same substance also named as 'carbon dioxide' in the same passage — variant of the same entity |
| 41 | TGS-127 | 1:11:54 | 0.85 | `Person · VARIANT?` | **Vasily Leontiev** | 'there's this guy Vasily Leontiev, who... actually won the Nobel Prize for it' — the economist is conventionally rendered 'Wassily Leontief'; transcript spelling may be an ASR/tran… |
| 42 | TGS-127 | 1:14:43 | 0.25 | `Concept · ASR?` | **the SKU** | 'I do worry that the SKU has gone far too much into naval gazing' — likely mistranscription (possibly 'the skew'); not a real named entity |
| 43 | TGS-127 | 1:14:43 | 0.30 | `Concept · ASR?` | **naval gazing** | 'gone far too much into naval gazing' — almost certainly 'navel gazing'; transcription error |
| 44 | TGS-127 | 1:17:37 | 0.40 | `Concept · ASR?` | **Ballywick** | 'brings us right to your Ballywick here' — almost certainly the word 'bailiwick' mis-transcribed as a proper-noun-like form; not a real entity |
| 45 | TGS-127 | 1:24:02 | 0.50 | `Concept · ASR?` | **Jevin's paradox** | "On Jevin's paradox and how technology making things better" — almost certainly 'Jevons paradox', which is rendered correctly later in the same chunk; flagged as ASR error and name… |
| 46 | TGS-127 | 1:24:28 | 0.80 | `Location · VARIANT?` | **U S** | "The amount of energy consumption in the U S is going to go up a lot" — transcript renders United States as spaced-out "U S"; likely intended "U.S." |
| 47 | TGS-127 | 1:24:28 | 0.25 | `Concept · ASR?` | **Swedish word** | "just subsisting on, like you say, that's Swedish word" — an actual Swedish term (likely 'lagom') appears to have been dropped or garbled in transcription; the entity itself is unr… |
| 48 | TGS-127 | 1:40:15 | 0.60 | `Work_Publication · VARIANT?` | **Bretton Woods** | 'a sequel to both of those books. So the material world and Bretton Woods' — here 'Bretton Woods' appears to name a book, whereas earlier in the same chunk it names the conference/… |

---

## 2. Honest quality notes, per episode

### TGS-127 (Interview) — the strongest result, with two caveats

Reproduced the hand-built reference closely: 14/15 metadata fields exact, chunks
1–6 structurally identical, all five verbatim turn texts byte-identical
including a 4,998-character turn. On chunk 1 (the reference's only real
extraction) it found 21/21 entities with confidences within 0.07, and
independently rediscovered both hand-found problems — `Teal World` (0.35 vs
reference 0.30) and `Simon Michaud` (0.55 vs 0.50).

Worth a second look:

- **11% of its 582 candidates (64) are just the two speaker names.** I feed
  `Speaker [ts]: text` into each prompt, so the model dutifully extracts
  "Nate Hagens" and "Ed Conway" in nearly every chunk (32× each). That is paid-for
  noise, not signal.
- **1.8× average duplication** — 582 candidates collapse to 319 distinct surface
  forms. Expected (the spec anticipates a later resolution stage) but it means
  the raw candidate count overstates the yield by ~45%.
- **A 1-second chunk exists.** `TGS127_chunk_46_filler` spans 3007–3008s. My
  filler-cut rule can emit a near-zero-length chunk when a turn starts just
  before the next anchor. Harmless — the turn is assigned correctly — but the
  "chunk" is meaningless as a unit.
- **Two flags are low-value formatting noise**, not corpus problems: `CO2` at
  0.90 and `U S` at 0.80. High confidence on a low-value flag is the worst
  combination for a review queue, because it sorts to the top.

### RR-24 (PanelDiscussion) — validated the thing it was chosen for, but noisiest

Delivered the structural test the spec wanted: **10 chunks carry `turns[]`
spanning 3 distinct speakers.** 200 bare continuation timestamps handled
correctly. All three speakers rediscovered by NER.

Worth a second look:

- **22% of its 376 candidates (82) are just the three speaker labels** — double
  TGS-127's rate, because there are three names to re-extract instead of two.
- **7 of its 26 flags are the same `Don` finding.** Genuinely useful once; as a
  review queue it is 27% redundant.
- **It found the outro bug.** Its credits are four *bare-timestamp* lines after a
  separator, which the original parser appended to Nate's final turn — the
  episode ended "…this blue-green ball. If you'd like to learn more about this
  episode…". Fixed structurally before the NER run, so the output is clean, but
  the episode is the reason the parser changed.
- **Lowest-confidence flags cluster here** (six at ≤0.30). Reading them, they
  are mostly *correct* — `citations` → cetaceans, `great wall of fu`, `san's`,
  `FWU` are all real garble. Low confidence is the model being appropriately
  uncertain about *what the right answer is*, not about whether something is
  wrong. That distinction matters if you ever filter this queue by confidence:
  **a confidence threshold would discard some of the best findings.**

### Frankly-145 (Monologue) — structurally correct, and that is the problem

Confirmed all three of the spec's predictions exactly: one continuous
24-minute turn, no cold-open teaser, no trailing outro.

Worth a second look — this is the most consequential note in the document:

- **Chunk-level NER collapsed into a single whole-transcript call.** One turn
  means one populated chunk: **1 of 23 chunks holds content; 22 are empty.**
  "One API call per chunk" became one call over the entire episode.
- **Its $0.0874 is therefore not a cost saving, and should not be used in any
  projection.** It is the cost of doing transcript-level extraction on a short
  episode, mislabelled as chunk-level. Per minute it is $0.0036 against
  $0.011–0.013 for the other two — a 3× gap that is an artifact, not an
  efficiency.
- **It makes the spec's §2 chunk-vs-transcript comparison vacuous for
  monologues.** The two granularities are the same operation at the same cost;
  the comparison can only ever report them identical.
- **31 candidates, zero flagged.** Plausible for a scripted monologue (Nate
  reading his own prose, few proper nouns garbled) but it also means this
  episode contributed no evidence at all about flag quality.
- **The unused signal**: its 44 bare continuation timestamps each carry a real
  time offset, currently merged into turn text and discarded. They are the only
  sub-turn temporal structure a monologue has, and they align naturally to the
  23 show-notes anchors.

### Cross-cutting: two flags are not about entities at all

Bucket D — `Corn ethanol EROI` (RR-24, 0.15) and `Richard Baldwin` (TGS-127,
0.20) — are the model reporting that **a curator's show-notes topic label does
not match the content of its chunk**. That is an alignment-quality signal, not a
named-entity finding, and it emerged unprompted.

It is the same phenomenon the hand-built reference documented by hand (its chunk
2's "Olivia Lazard / Michael Michaux" label refers to content in the *preceding*
turn), which suggests the effect is systematic rather than incidental. If so,
this side-channel is arguably more valuable than the ASR findings, because it
measures whether the chunking is anchoring correctly — and nothing else in the
pipeline measures that. Both instances arrived with low confidence and would be
lost to any threshold filter.

---

## 3. Spend to date, and what episode 4 onward would cost

### Real spend

| item | tokens | cost |
|---|---|---|
| Smoke test (1 call, validating structured output) | 382 in / 199 out | $0.0069 |
| 3-chunk cost probe on TGS-127 | 5,254 in / 3,591 out | $0.1160 |
| TGS-127 full run (48 calls) | 74,212 in / 38,686 out | $1.3382 |
| RR-24 full run (43 calls) | 64,223 in / 29,189 out | $1.0508 |
| Frankly-145 full run (1 call) | 6,395 in / 2,219 out | $0.0874 |
| | | **$2.5993** |

**The first two rows are not in any output file.** The `cost_tracking` blocks
sum to $2.4764; the true figure is **$2.5993**. The probe was a separate run
that wrote nothing, and the full TGS-127 run re-did all 48 chunks from scratch,
so its tokens are additional rather than included.

One-time setup remains **$0.00** in API spend — the pipeline, the diff tool, and
the parser rewrite cost nothing but time.

### What episode 4 onward looks like

Output tokens are 63–72% of cost, so cost tracks *how much the model finds*, not
just transcript length. Normalizing by duration:

| episode | $/min | $/call | note |
|---|---|---|---|
| TGS-127 | $0.01278 | $0.0279 | 2 speakers |
| RR-24 | $0.01103 | $0.0244 | 3 speakers, shorter |
| Frankly-145 | $0.00360 | $0.0874 | **degenerate — do not use** |

**Best honest estimate at this same depth (Opus 5, effort `high`, one call per
populated chunk):**

- **Full-length interview or panel (90–105 min): $1.05–1.35, call it ~$1.20.**
  Directly measured, n=2, and the two agree closely.
- **Frankly / monologue, as the pipeline behaves today: ~$0.09.** Real but
  misleading — you are buying one transcript-level pass, not chunk-level output.
- **Frankly, if the monologue degeneracy is fixed: ~$0.25–0.30.** Extrapolated
  at the interview per-minute rate over 24 minutes. This is the number to plan
  with if you want monologues chunked properly.

**Reductions available without changing model or depth:**

- Suppressing speaker-label re-extraction removes 11–22% of candidates. Since
  output is ~70% of cost, that is roughly **8–16% off** — and it removes noise
  rather than signal.
- Cross-chunk dedup does *not* reduce API cost (it is post-hoc), but it would cut
  the review queue by ~45%.

**Full-corpus projection, with its caveats stated:** at ~$1.20 for the ~248
non-monologue episodes and ~$0.29 for the ~100 Franklys, roughly **$325**, and I
would carry a **$250–450** range on that. Caveats that genuinely matter:

1. **n=2 for full-length episodes.** Duration and density both vary within type;
   two agreeing data points is not a curve.
2. **Valid for the official-transcript population only**, per spec §5. The
   audio-only and YouTube-caption episodes are a separate costing problem.
3. **Excludes the monologue fix**, which would raise the Frankly line ~3×.
4. **Excludes human review time**, which on this evidence is the real
   constraint: 989 candidates across three episodes, ~45% of them duplicates.

---

## 4. What I would want decided before episode 4

Not new work — just the three open items this run produced, in priority order.

1. **The monologue degeneracy** (§2). Affects ~100 episodes and currently makes
   one of the pilot's two headline questions unanswerable for a third of the
   corpus. Fix candidate: segment a single long turn at bare-timestamp
   boundaries when it spans multiple anchors. It changes `turns[]` semantics the
   spec deliberately settled, so it needs your call.
2. **Speaker-label suppression** (§2). Cheap, uncontroversial, ~8–16% cost
   saving and less noise.
3. **`TGS_<number>` is not unique across series.** RR-24 and interview 24 both
   mint `TGS_24`. Full IRIs stay distinct via the EpisodeType prefix, but
   CLAUDE.md 0d states the acronym+number key alone should be unique and that
   the title fragment is droppable — both false here. Flagged in each affected
   record's `_gaps`; not re-designed, since naming changes need an explicit
   go-ahead.
