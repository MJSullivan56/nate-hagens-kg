#!/usr/bin/env python3
"""chunk_pipeline.py — show-notes-anchored transcript chunking + NER candidate
extraction, per `pilot/pilot-spec-transcript-chunking.md`.

    # chunking only (deterministic, no LLM, no cost)
    python pilot/chunk_pipeline.py --episode TGS-127-EdConway --out pilot/output

    # add the chunk-level NER pass (costs money — see --model)
    python pilot/chunk_pipeline.py --episode TGS-127-EdConway --out pilot/output \
        --ner chunk --model claude-opus-5

    # diff a produced record against a hand-built reference
    python pilot/chunk_pipeline.py --episode TGS-127-EdConway \
        --diff pilot/example/TGS-127_chunked_example.json

    # gap-size distribution, to tune FILLER_GAP_THRESHOLD (spec §1.3)
    python pilot/chunk_pipeline.py --all --gap-stats

Two stages, deliberately separable because their costs differ by orders of
magnitude: chunking is pure local text processing, NER is one API call per
chunk. Chunking runs and gets reviewed before any money is spent.

Design decisions that the spec left open, resolved here explicitly rather than
silently (each is called out in the emitted record's own `_decisions` block):

1. CHUNKS ARE A NON-OVERLAPPING PARTITION. The spec says a filler chunk covers
   a gap "between consecutive entries" exceeding the threshold, but the hand-
   built reference nests its filler chunk *inside* the enclosing topic chunk's
   span (chunk_07 = 422-608 and chunk_07b_filler = 528-569 both cover 528-569).
   Overlapping spans make "which chunk does this turn belong to" ambiguous, so
   here the topic chunk is CUT where the filler begins. See `build_chunks`.

2. A TURN BELONGS TO THE CHUNK CONTAINING ITS OWN START TIME, half-open
   [start, end). Straight from the reference's own stated rule. Long turns run
   past their chunk's `end_seconds` — expected, not a bug.

3. The reference flags a contradiction in itself at chunk_08 (a turn starting
   at 569s shown under a chunk beginning at 608s) and asks for a code-level
   rule. Decision 1 resolves it: that turn falls inside the filler span and is
   assigned there.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TRANSCRIPTS = HERE / "transcripts"
SHOWNOTES = HERE / "scraped-shownotes"

# Spec §1.3 proposes 90s; genuinely provisional — run --gap-stats before tuning.
FILLER_GAP_THRESHOLD = 90

# Fixed site boilerplate that precedes the real transcript body.
TRANSCRIPT_MARKER_RE = re.compile(r"(?im)^\#*\s*TRANSCRIPT\s*:?\s*$")
SEPARATOR_RE = re.compile(r"^[-=_]{10,}\s*$")

# `[HH:MM:SS] Speaker Name:` starts a turn. A bare `[HH:MM:SS]` with no speaker
# label after it is a paragraph break WITHIN the current turn (SKILL.md gotcha
# #3) — the dominant pattern in monologues, so getting this wrong fragments a
# 24-minute Frankly into dozens of spurious turns.
TURN_RE = re.compile(
    r"^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*"
    r"([A-Z][A-Za-z.'’\- ]{1,40}?)\s*:\s*(.*)$")
BARE_TS_RE = re.compile(r"^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)$")

# Outro/credits boilerplate that follows the last real turn.
OUTRO_MARKERS = (
    "if you enjoyed or learned from this episode",
    "please follow us on your favorite podcast",
    "visit thegreatsimplification",
    "this episode was recorded",
    "produced by", "edited by", "music by", "hosted by",
    "subscribe to our newsletter",
)

# SKILL.md gotcha #6(c): caption timestamp/duration fused into running prose
# with no separator, breaking words mid-sentence.
CORRUPTION_RE = re.compile(
    r"[a-z]{2}\d{1,2}:\d{2}(?::\d{2})?[a-z]{2}"          # ..you00:12know..
    r"|\d{1,2}:\d{2}:\d{2}\.\d{3}"                        # WebVTT fractional
    r"|align:start position:\d+%")                        # WebVTT cue settings

CHAPTER_RE = re.compile(r"(?im)^\#{2,}\s*Chapter\s+\d+\s*[:.]?")

# Pricing per 1M tokens, from the claude-api skill's model table (2026-06-24).
PRICING = {
    "claude-opus-5":    (5.00, 25.00),
    "claude-opus-4-8":  (5.00, 25.00),
    "claude-sonnet-5":  (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-fable-5":   (10.00, 50.00),
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def ts_to_seconds(ts: str) -> int | None:
    """`HH:MM:SS` or `MM:SS` -> seconds.

    Both forms occur, sometimes in the same corpus (SKILL.md gotcha #9 flags
    `1:38:32` vs `02:04`), so the number of parts decides — never the width.
    """
    parts = ts.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


def fmt_ts(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# --------------------------------------------------------------------------
# pairing (spec §"File-pairing convention")
# --------------------------------------------------------------------------

def episode_slugs() -> list[str]:
    """Every episode with a transcript, by slug (the `-TRANSCRIPT` stem)."""
    out = []
    for p in sorted(TRANSCRIPTS.glob("*-TRANSCRIPT.*")):
        out.append(re.sub(r"-TRANSCRIPT$", "", p.stem))
    return out


def find_pair(slug: str) -> tuple[Path, Path | None]:
    """Locate (transcript, metadata) for a slug.

    Metadata matching is extension-agnostic per the spec — `.yaml`, `.json`,
    and a website-export `.md` are all valid on that side.
    """
    tr = next((p for p in TRANSCRIPTS.glob(f"{slug}-TRANSCRIPT.*")), None)
    if tr is None:
        raise SystemExit(f"no transcript found for slug {slug!r}")
    meta = next((p for p in sorted(SHOWNOTES.glob(f"{slug}.*"))
                 if p.suffix.lower() in (".yaml", ".yml", ".json", ".md")), None)
    return tr, meta


def load_metadata(path: Path | None) -> tuple[dict, str]:
    """Load the scraped metadata. Returns (record, source_format)."""
    if path is None:
        return {}, "none"
    text = path.read_text(encoding="utf-8").replace("\x00", "")
    if path.suffix.lower() == ".json":
        return json.loads(text), "json"
    if path.suffix.lower() in (".yaml", ".yml"):
        return yaml.safe_load(text) or {}, "yaml"
    # Website-page markdown — a genuinely different third format (SKILL.md
    # gotcha #9). Not parsed here; Phase 0's three bootstrap episodes are all
    # yaml/json, and TGS_231 is deliberately a later step.
    return {"_raw_markdown": text}, "markdown"


# --------------------------------------------------------------------------
# transcript parsing
# --------------------------------------------------------------------------

@dataclass
class Turn:
    speaker: str
    start_seconds: int
    text: str

    def as_dict(self) -> dict:
        return {"speaker": self.speaker, "start_seconds": self.start_seconds,
                "text": self.text}


@dataclass
class ParsedTranscript:
    turns: list[Turn] = field(default_factory=list)
    has_inline_timestamps: bool = False
    bare_timestamp_count: int = 0
    teaser: Turn | None = None
    outro_text: str | None = None
    has_embedded_metadata_corruption: bool = False
    has_youtube_chapters: bool = False
    had_nul_bytes: bool = False
    speakers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def parse_transcript(path: Path, host: str | None) -> ParsedTranscript:
    """Parse a transcript into speaker turns, stripping boilerplate.

    Order matters: strip site boilerplate, then detect the teaser (which needs
    turns already parsed to know where the host first speaks), then the outro.
    """
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    out = ParsedTranscript(had_nul_bytes="\x00" in text)
    text = text.replace("\x00", "").replace("\r\n", "\n")

    out.has_embedded_metadata_corruption = bool(CORRUPTION_RE.search(text))
    out.has_youtube_chapters = bool(CHAPTER_RE.search(text))

    # 1. Drop everything up to and including the `# TRANSCRIPT` marker. Split
    #    on the LAST one: a stray premature marker exists in this corpus.
    marks = list(TRANSCRIPT_MARKER_RE.finditer(text))
    body = text[marks[-1].end():] if marks else text
    if len(marks) > 1:
        out.notes.append(f"{len(marks)} '# TRANSCRIPT' markers; split on the last")

    # 2. Classify every line first, THEN assemble turns.
    #
    #    Two passes rather than one because the outro can only be identified in
    #    hindsight: it is whatever follows the separator that follows the LAST
    #    speaker-labelled turn, and you don't know which turn is last until the
    #    end. RR-24's outro is four BARE-TIMESTAMP lines after a separator, so a
    #    single forward pass appends them to the final speaker's turn and ends
    #    the episode with "...this blue-green ball. If you'd like to learn more
    #    about this episode..." — the credits fused into real speech.
    lines: list[tuple[str, str, str, str]] = []   # (kind, ts, speaker, text)
    for line in body.split("\n"):
        s = line.strip()
        if not s:
            continue
        if SEPARATOR_RE.match(s):
            lines.append(("separator", "", "", ""))
            continue
        m = TURN_RE.match(s)
        if m:
            lines.append(("labelled", m.group(1),
                          re.sub(r"\s+", " ", m.group(2)).strip(), m.group(3).strip()))
            continue
        b = BARE_TS_RE.match(s)
        if b:
            lines.append(("bare", b.group(1), "", b.group(2).strip()))
            continue
        lines.append(("plain", "", "", s))

    out.has_inline_timestamps = any(k in ("labelled", "bare") for k, *_ in lines)
    out.bare_timestamp_count = sum(1 for k, *_ in lines if k == "bare")

    last_labelled = max((i for i, (k, *_) in enumerate(lines) if k == "labelled"),
                        default=None)

    # 3. Outro boundary: the first separator after the last labelled turn.
    #    Structural, so it works whether the credits carry bare timestamps
    #    (RR-24) or no timestamp at all (TGS_127), and finds nothing when there
    #    is no trailing separator at all (Frankly-145).
    outro_at = None
    if last_labelled is not None:
        outro_at = next((i for i in range(last_labelled + 1, len(lines))
                         if lines[i][0] == "separator"), None)
    if outro_at is not None:
        tail = [t for k, _, _, t in lines[outro_at + 1:] if k in ("bare", "plain") and t]
        if tail:
            out.outro_text = re.sub(r"\s+", " ", " ".join(tail)).strip()
        lines = lines[:outro_at]

    # 4. Assemble turns. A bare timestamp continues the current turn (SKILL.md
    #    gotcha #3) — the dominant case in monologues.
    cur: Turn | None = None
    for kind, ts, speaker, text in lines:
        if kind == "labelled":
            sec = ts_to_seconds(ts)
            cur = Turn(speaker=speaker, start_seconds=sec if sec is not None else 0,
                       text=text)
            out.turns.append(cur)
        elif kind in ("bare", "plain") and cur is not None and text:
            cur.text = (cur.text + " " + text).strip()
        # `plain` before the first labelled turn is site preamble; dropped.

    for t in out.turns:
        t.text = re.sub(r"\s+", " ", t.text).strip()

    # 5. Teaser. Spec/SKILL.md gotcha #1: the real content begins at the HOST's
    #    first turn; anything before it is a cold-open soundbite spliced in from
    #    later, regardless of the timestamp it carries.
    #    NOTE: for a solo monologue the host is the only speaker, so this rule
    #    is vacuous — it strips nothing and cannot distinguish a teaser from
    #    real content. That limitation is real and unresolved (see the
    #    reference's own _preprocessing_rules open question).
    if host and out.turns:
        first_host = next((i for i, t in enumerate(out.turns)
                           if _same_speaker(t.speaker, host)), None)
        if first_host is None:
            out.notes.append(
                f"host {host!r} never appears as a speaker label; no teaser strip applied")
        elif first_host > 0:
            if first_host > 1:
                out.notes.append(
                    f"{first_host} turns precede the host's first turn; all stripped as teaser")
            out.teaser = out.turns[0]
            out.turns = out.turns[first_host:]

    # 6. Outro fallback: only for transcripts with NO trailing separator, where
    #    the structural rule above found nothing. Keyword-based, so it is the
    #    weaker of the two — it can only cut at whichever marker happens to
    #    appear first, which on RR-24 would have left two of four credit
    #    sentences attached to real speech.
    if out.turns and out.outro_text is None:
        last = out.turns[-1]
        hits = [i for mk in OUTRO_MARKERS
                if (i := last.text.lower().find(mk)) > 0]
        if hits:
            cut = min(hits)
            out.outro_text = last.text[cut:].strip()
            last.text = last.text[:cut].strip()
            out.notes.append("outro found by keyword fallback (no trailing "
                             "separator); verify the cut point")

    seen: list[str] = []
    for t in out.turns:
        if t.speaker not in seen:
            seen.append(t.speaker)
    out.speakers = seen
    return out


def _same_speaker(a: str, b: str) -> bool:
    """Loose speaker-name match — the transcript may add an honorific or use a
    short form where the metadata uses the full name."""
    def toks(x):
        drop = {"dr", "prof", "professor", "mr", "mrs", "ms", "the"}
        return [t for t in re.findall(r"[a-z]+", (x or "").lower())
                if len(t) > 1 and t not in drop]
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return False
    return ta == tb or ta[-1] == tb[-1]


# --------------------------------------------------------------------------
# chunking
# --------------------------------------------------------------------------

def normalize_show_notes(raw: list | None) -> list[dict]:
    """Sort by seconds, drop unusable entries, collapse duplicate timestamps."""
    out = []
    for e in raw or []:
        sec = e.get("seconds")
        if sec is None and e.get("timestamp"):
            sec = ts_to_seconds(str(e["timestamp"]))
        if sec is None:
            continue
        out.append({"seconds": int(sec),
                    "timestamp": e.get("timestamp") or fmt_ts(int(sec)),
                    "topic": e.get("topic"),
                    "links": e.get("links") or []})
    out.sort(key=lambda e: e["seconds"])
    merged: list[dict] = []
    for e in out:
        if merged and merged[-1]["seconds"] == e["seconds"]:
            # Same anchor second listed twice — merge rather than emit a
            # zero-length chunk.
            prev = merged[-1]
            prev["topic"] = "; ".join(x for x in (prev["topic"], e["topic"]) if x)
            prev["links"] = prev["links"] + e["links"]
            continue
        merged.append(e)
    return merged


def build_chunks(show_notes: list[dict], turns: list[Turn], duration: int | None,
                 slug_tag: str, threshold: int = FILLER_GAP_THRESHOLD) -> list[dict]:
    """Build a non-overlapping chunk partition from show-notes anchors.

    For each consecutive anchor pair, one `topic_anchored` chunk. Where the gap
    exceeds `threshold` AND a turn actually starts late enough inside it to be
    genuinely unflagged content, the topic chunk is CUT at that turn and the
    remainder becomes a `filler` chunk.

    The cut is what keeps chunks non-overlapping (decision 1 in the module
    docstring). Without it, a filler nested inside its enclosing topic chunk
    leaves turn assignment ambiguous.
    """
    if not show_notes:
        return []
    end_of_episode = duration if duration else (
        max((t.start_seconds for t in turns), default=0) + 1)
    turn_starts = sorted({t.start_seconds for t in turns})

    chunks: list[dict] = []
    n = 0
    for i, e in enumerate(show_notes):
        start = e["seconds"]
        nxt = show_notes[i + 1]["seconds"] if i + 1 < len(show_notes) else end_of_episode
        if nxt <= start:
            nxt = start + 1

        cut = None
        if nxt - start > threshold:
            # First turn beginning more than `threshold` after the anchor: the
            # point where content stops plausibly belonging to the anchor topic.
            cut = next((s for s in turn_starts if start + threshold < s < nxt), None)

        n += 1
        chunks.append({
            "chunk_id": f"{slug_tag}_chunk_{n:02d}",
            "chunk_type": "topic_anchored",
            "start_seconds": start,
            "end_seconds": cut if cut is not None else nxt,
            "topic_label": e["topic"],
            "curated_links": e["links"],
            "turns": [],
            "ner_candidates": [],
        })
        if cut is not None:
            n += 1
            chunks.append({
                "chunk_id": f"{slug_tag}_chunk_{n:02d}_filler",
                "chunk_type": "filler",
                "start_seconds": cut,
                "end_seconds": nxt,
                "topic_label": None,
                "curated_links": [],
                "turns": [],
                "ner_candidates": [],
            })
    return chunks


def assign_turns(chunks: list[dict], turns: list[Turn]) -> list[Turn]:
    """Place each turn in the chunk containing its own start time.

    Half-open [start, end). Returns any turns that fell outside every chunk
    (e.g. speech before the first show-notes anchor) so the caller can report
    them rather than lose them.
    """
    orphans = []
    for t in turns:
        for c in chunks:
            if c["start_seconds"] <= t.start_seconds < c["end_seconds"]:
                c["turns"].append(t.as_dict())
                break
        else:
            orphans.append(t)
    return orphans


# --------------------------------------------------------------------------
# record assembly
# --------------------------------------------------------------------------

EPISODE_TYPE = {"interview": "Interview", "roundtable": "PanelDiscussion",
                "frankly": "Monologue", "podcast_interview": "Interview"}


def episode_iri(meta: dict) -> str | None:
    """Mint per CLAUDE.md decision 0d: tgs:<EpisodeType>.<ACRONYM>_<n>_<Frag>."""
    num, series = meta.get("episode_number"), meta.get("series")
    etype = EPISODE_TYPE.get(series or "")
    if num is None or not etype:
        return None
    guests = meta.get("guests") or []
    frag = re.sub(r"[^A-Za-z0-9]", "", guests[0]) if guests else ""
    if not frag:
        frag = re.sub(r"[^A-Za-z0-9]", "", (meta.get("title") or "").split(":")[0])[:32]
    return f"tgs:{etype}.TGS_{num}_{frag}" if frag else f"tgs:{etype}.TGS_{num}"


def build_record(slug: str, threshold: int = FILLER_GAP_THRESHOLD) -> dict:
    tr_path, meta_path = find_pair(slug)
    meta, meta_format = load_metadata(meta_path)
    host = meta.get("host")
    parsed = parse_transcript(tr_path, host)

    sn = normalize_show_notes(meta.get("show_notes"))
    anchor = ("show_notes" if sn
              else "youtube_chapters" if parsed.has_youtube_chapters else "none")

    slug_tag = re.sub(r"[^A-Za-z0-9]", "", slug.split("-")[0] + (
        slug.split("-")[1] if len(slug.split("-")) > 1 else ""))
    chunks = build_chunks(sn, parsed.turns, meta.get("duration_seconds"),
                          slug_tag, threshold)
    orphans = assign_turns(chunks, parsed.turns)

    gaps: list[str] = []
    if not parsed.has_inline_timestamps:
        gaps.append("no usable inline timestamps; proportional fallback would be "
                    "required (not implemented — no Phase 0 episode needs it)")
    if not sn:
        gaps.append("no show_notes in the scraped record; filler-only chunking "
                    "would be required (not implemented — no Phase 0 episode needs it)")
    if orphans:
        gaps.append(
            f"{len(orphans)} turn(s) start before the first show-notes anchor or "
            f"after the last chunk and are unassigned: "
            + ", ".join(f"{t.speaker}@{t.start_seconds}s" for t in orphans[:4]))
    if meta_format == "markdown":
        gaps.append("metadata is website-page markdown; structured show_notes "
                    "not parsed (spec §2.5 TGS_231 case)")

    # IRI minting: CLAUDE.md decision 0d states uniqueness comes from
    # SourceAcronym + Number ALONE, with the title fragment "PURE human
    # readability [that] can be shortened or dropped without breaking
    # anything". That invariant does not hold for non-interview series: the
    # three series number independently, so Reality Roundtable 24 and interview
    # episode 24 both mint TGS_24. The EpisodeType prefix keeps the full IRI
    # distinct, but dropping the fragment would collide. Flagged, not
    # unilaterally re-designed — renaming conventions needs an explicit
    # go-ahead per CLAUDE.md.
    if meta.get("series") in ("roundtable", "frankly") and meta.get("episode_number"):
        gaps.append(
            f"IRI MINTING RISK: series={meta['series']} #{meta['episode_number']} mints "
            f"'{episode_iri(meta)}' — the SourceAcronym+Number key 'TGS_"
            f"{meta['episode_number']}' is NOT unique across series (interview "
            f"#{meta['episode_number']} exists independently). CLAUDE.md 0d says that key "
            f"alone should be unique. Needs a convention decision (e.g. RR_/FR_ "
            f"acronyms); not resolved here.")

    # Monologue degeneracy: with one turn for the whole episode, every chunk but
    # the first is empty and chunk-level NER collapses into a single
    # whole-transcript call. Reported because it makes the spec's §2 chunk-vs-
    # transcript comparison vacuous for this episode type.
    withturns = sum(1 for c in chunks if c["turns"])
    if chunks and withturns == 1 and len(chunks) > 3:
        gaps.append(
            f"CHUNKING DEGENERATE: 1 turn spans the whole episode, so {withturns} of "
            f"{len(chunks)} chunks hold content and chunk-level NER becomes one "
            f"whole-transcript call. The {parsed.bare_timestamp_count} bare continuation "
            f"timestamps carry real sub-turn time offsets that are currently merged "
            f"into turn text and discarded — they are the only available signal for "
            f"segmenting a monologue against its show-notes anchors.")

    gaps.extend(parsed.notes)

    return {
        "episode_iri": episode_iri(meta),
        "source_transcript_file": tr_path.name,
        "source_yaml_file": meta_path.name if meta_path else None,
        "source_sha256": meta.get("source_sha256"),
        "transcript_source_type": "official",
        "chunking_anchor_available": anchor,
        "has_embedded_metadata_corruption": parsed.has_embedded_metadata_corruption,

        "title": meta.get("title"),
        "webpage_url": meta.get("webpage_url"),
        "youtube_url": meta.get("youtube_url"),
        "duration_seconds": meta.get("duration_seconds"),
        "published_date": str(meta.get("published_date")) if meta.get("published_date") else None,
        "recorded_date": str(meta.get("recorded_date")) if meta.get("recorded_date") else None,
        "keywords": meta.get("keywords") or [],
        "host": host,
        "guests": meta.get("guests") or [],
        "guest_bios": meta.get("guest_bios") or [],
        "description": meta.get("description"),
        "transcript_speakers": meta.get("transcript_speakers") or [],

        "chunking_method": "show_notes_anchored" if sn else "filler_only",
        "_provenance": {
            "alignment_confidence": "high" if parsed.has_inline_timestamps else "low",
            "chunking_method": "site:show_notes" if sn else "fallback:filler_only",
            "metadata_source_format": meta_format,
            "show_notes_entries": len(sn),
            "filler_gap_threshold_seconds": threshold,
            "turns_parsed": len(parsed.turns),
            "bare_continuation_timestamps": parsed.bare_timestamp_count,
            "speakers_observed_in_transcript": parsed.speakers,
            "teaser_stripped": parsed.teaser.as_dict() if parsed.teaser else None,
            "outro_stripped": parsed.outro_text,
            "had_nul_bytes": parsed.had_nul_bytes,
        },
        "_gaps": gaps,
        "chunks": chunks,
        "transcript_level_ner": None,
        "cost_tracking": {
            "chunk_level_input_tokens": None,
            "chunk_level_output_tokens": None,
            "transcript_level_input_tokens": None,
            "transcript_level_output_tokens": None,
            "estimated_cost_usd": None,
            "model_used": None,
            "extracted_at": None,
        },
        "_decisions": [
            "Chunks are a NON-OVERLAPPING partition. Where a >threshold gap "
            "contains a genuinely late turn, the topic_anchored chunk is cut at "
            "that turn and the remainder becomes a filler chunk. The hand-built "
            "reference instead nests the filler inside the enclosing topic "
            "chunk's span; that makes turn assignment ambiguous, so it was not "
            "reproduced. See _diff_vs_reference in the run report.",
            "A turn is assigned to the chunk containing its own start_seconds, "
            "half-open [start, end). Long turns run past end_seconds by design.",
            "Teaser detection = everything before the HOST's first turn. This "
            "rule is vacuous for solo monologues (the host is the only speaker) "
            "and is therefore unvalidated for that case.",
        ],
    }


# --------------------------------------------------------------------------
# NER (chunk-level)
# --------------------------------------------------------------------------

NER_SYSTEM = """\
You extract named-entity CANDIDATES from a podcast transcript chunk for a \
knowledge-graph reference pass. Nothing you output is minted directly; a human \
reviews it later.

Rules:
- SCHEMA-FREE. Do not force entities into a fixed type list. Use whatever \
`type_guess` actually fits (Person, Organization, Work_Publication, Material, \
Concept, Location, SchoolOfThought, Event, ...).
- Extract only entities actually named in the text. Do not infer or add \
outside knowledge.
- `confidence` 0.0-1.0 is your confidence that this is a real, correctly-read \
entity — not its importance.
- FLAG CORPUS PROBLEMS rather than silently cleaning them:
  * a name that looks like a speech-recognition error -> append \
"_LIKELY_ASR_ERROR" to type_guess, explain in context, low confidence.
  * a name rendered differently elsewhere in the same chunk or conflicting with \
the supplied episode metadata -> append "_NAME_VARIANT_CONFLICT", explain.
- `context` = the short surrounding phrase, plus your reasoning if you flagged it.

Return a `candidates` array. Return an empty array if the chunk names no
entities. Response shape is enforced by a schema — do not wrap it in prose or a
code fence."""


# Structured output rather than "return JSON and hope": guarantees a parseable
# shape, so a malformed reply can't silently become a dropped chunk. `type_guess`
# is deliberately a free-form string — the spec requires SCHEMA-FREE extraction
# (§2), so the schema constrains the envelope, never the type vocabulary.
NER_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "type_guess": {"type": "string"},
                    "confidence": {"type": "number"},
                    "context": {"type": "string"},
                },
                "required": ["text", "type_guess", "confidence", "context"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}


def ner_chunk(client, model: str, rec: dict, chunk: dict,
              max_tokens: int = 8192, effort: str = "high") -> tuple[list[dict], int, int]:
    """One NER call over a chunk's concatenated turns.

    Per spec §4, extraction runs over the concatenation of the chunk's turns at
    processing time rather than a separately stored `chunk_text` field, so there
    is no second copy that can drift out of sync.

    `effort` stays at `high`: the valuable part of this pass is judgment (is
    "Teal World" an ASR error for "Material World"?), not raw entity spotting,
    and that is exactly what lower effort degrades first.
    """
    body = "\n\n".join(f"{t['speaker']} [{fmt_ts(t['start_seconds'])}]: {t['text']}"
                       for t in chunk["turns"])
    if not body.strip():
        return [], 0, 0

    ctx = (f"Episode: {rec.get('title')}\n"
           f"Host: {rec.get('host')}   Guests: {', '.join(rec.get('guests') or [])}\n"
           f"Chunk topic (curator-supplied, higher confidence than anything you "
           f"infer): {chunk.get('topic_label') or '(unflagged filler segment)'}\n\n"
           f"TRANSCRIPT CHUNK:\n{body}")

    resp = client.messages.create(
        model=model, max_tokens=max_tokens, system=NER_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": NER_SCHEMA},
                       "effort": effort},
        messages=[{"role": "user", "content": ctx}])
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    try:
        cands = (json.loads(text) or {}).get("candidates") or []
    except json.JSONDecodeError:
        # Should be unreachable with a schema attached; kept so a surprise
        # surfaces in the output as a flagged row instead of an exception.
        cands = [{"text": None, "type_guess": "_PARSE_FAILURE", "confidence": 0.0,
                  "context": f"model returned non-JSON: {text[:200]}"}]
    return cands, resp.usage.input_tokens, resp.usage.output_tokens


def run_ner(rec: dict, model: str, limit: int | None = None) -> None:
    """Populate ner_candidates in place and fill cost_tracking."""
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(HERE.parent / ".env")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    tin = tout = done = 0
    targets = [c for c in rec["chunks"] if c["turns"]]
    if limit:
        targets = targets[:limit]
    for i, chunk in enumerate(targets, 1):
        cands, a, b = ner_chunk(client, model, rec, chunk)
        chunk["ner_candidates"] = cands
        tin += a
        tout += b
        done += 1
        print(f"  [{i}/{len(targets)}] {chunk['chunk_id']}: {len(cands)} candidates "
              f"({a} in / {b} out)", file=sys.stderr)

    pin, pout = PRICING.get(model, (0.0, 0.0))
    rec["cost_tracking"] = {
        "chunk_level_input_tokens": tin,
        "chunk_level_output_tokens": tout,
        "transcript_level_input_tokens": None,
        "transcript_level_output_tokens": None,
        "estimated_cost_usd": round(tin / 1e6 * pin + tout / 1e6 * pout, 4),
        "model_used": model,
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chunks_processed": done,
        "chunks_skipped_no_turns": len(rec["chunks"]) - len([c for c in rec["chunks"] if c["turns"]]),
    }


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def gap_stats(slugs: list[str]) -> None:
    print(f"\n{'='*72}\nSHOW-NOTES GAP DISTRIBUTION (tunes FILLER_GAP_THRESHOLD)\n{'='*72}")
    allgaps = []
    for slug in slugs:
        _, mp = find_pair(slug)
        meta, _ = load_metadata(mp)
        sn = normalize_show_notes(meta.get("show_notes"))
        if len(sn) < 2:
            print(f"  {slug[:44]:44} {len(sn)} entries — no gaps")
            continue
        g = [sn[i + 1]["seconds"] - sn[i]["seconds"] for i in range(len(sn) - 1)]
        allgaps += g
        g.sort()
        over = sum(1 for x in g if x > FILLER_GAP_THRESHOLD)
        print(f"  {slug[:44]:44} n={len(sn):3} min={g[0]:4} med={g[len(g)//2]:4} "
              f"p90={g[int(len(g)*0.9)]:4} max={g[-1]:5}  >{FILLER_GAP_THRESHOLD}s: {over}")
    if allgaps:
        allgaps.sort()
        over = sum(1 for x in allgaps if x > FILLER_GAP_THRESHOLD)
        print(f"\n  ALL: n={len(allgaps)} med={allgaps[len(allgaps)//2]} "
              f"p90={allgaps[int(len(allgaps)*0.9)]} max={allgaps[-1]}  "
              f">{FILLER_GAP_THRESHOLD}s: {over} ({over/len(allgaps)*100:.0f}%)")


def summarize(rec: dict) -> None:
    ch = rec["chunks"]
    topic = [c for c in ch if c["chunk_type"] == "topic_anchored"]
    filler = [c for c in ch if c["chunk_type"] == "filler"]
    withturns = [c for c in ch if c["turns"]]
    nturns = sum(len(c["turns"]) for c in ch)
    p = rec["_provenance"]
    print(f"\n{'='*72}\n{rec['episode_iri'] or rec['source_transcript_file']}\n{'='*72}")
    print(f"  title              {(rec['title'] or '')[:64]}")
    print(f"  duration           {rec['duration_seconds']}s ({fmt_ts(rec['duration_seconds'] or 0)})")
    print(f"  anchor             {rec['chunking_anchor_available']}  "
          f"({p['show_notes_entries']} show-notes entries)")
    print(f"  alignment          {p['alignment_confidence']}")
    print(f"  chunks             {len(ch)} total = {len(topic)} topic_anchored "
          f"+ {len(filler)} filler")
    print(f"  chunks with turns  {len(withturns)}/{len(ch)}  "
          f"({len(ch)-len(withturns)} empty — long turns spanning several anchors)")
    print(f"  turns              {nturns} assigned, {p['turns_parsed']} parsed, "
          f"{p['bare_continuation_timestamps']} bare continuation timestamps")
    print(f"  speakers           {p['speakers_observed_in_transcript']}")
    print(f"  teaser stripped    "
          f"{'YES — ' + p['teaser_stripped']['speaker'] + ' @' + str(p['teaser_stripped']['start_seconds']) + 's' if p['teaser_stripped'] else 'no'}")
    print(f"  outro stripped     "
          f"{'YES — ' + repr(p['outro_stripped'][:52]) if p['outro_stripped'] else 'no'}")
    print(f"  corruption flag    {rec['has_embedded_metadata_corruption']}")
    if rec["_gaps"]:
        print("  _gaps:")
        for g in rec["_gaps"]:
            print(f"    - {g[:100]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", help="episode slug (see --list)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", type=Path, help="directory for one JSON per episode")
    ap.add_argument("--ner", choices=["none", "chunk"], default="none")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--ner-limit", type=int,
                    help="only NER the first N chunks (cost probe)")
    ap.add_argument("--threshold", type=int, default=FILLER_GAP_THRESHOLD)
    ap.add_argument("--gap-stats", action="store_true")
    ap.add_argument("--diff", type=Path, help="reference JSON to diff against")
    args = ap.parse_args()

    if args.list:
        for s in episode_slugs():
            _, mp = find_pair(s)
            print(f"  {s:56} metadata={mp.name if mp else 'MISSING'}")
        return 0

    slugs = episode_slugs() if args.all else ([args.episode] if args.episode else [])
    if not slugs:
        ap.error("need --episode SLUG, --all, or --list")

    if args.gap_stats:
        gap_stats(slugs)
        return 0

    for slug in slugs:
        rec = build_record(slug, args.threshold)
        if args.ner == "chunk":
            print(f"NER over {slug} with {args.model}:", file=sys.stderr)
            run_ner(rec, args.model, args.ner_limit)
        summarize(rec)
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            dest = args.out / f"{slug}.json"
            dest.write_text(json.dumps(rec, indent=2, ensure_ascii=False),
                            encoding="utf-8")
            print(f"\n  -> {dest}")
        if args.diff:
            from diff_vs_reference import diff_report
            diff_report(rec, json.loads(args.diff.read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
