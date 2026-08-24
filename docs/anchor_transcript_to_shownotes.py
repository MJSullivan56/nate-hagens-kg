#!/usr/bin/env python3
"""
Assigns transcript content to show-note-defined segments for vectorization.

FINAL DESIGN as of 2026-08-21, after real testing against RR-25 (TGS-provided)
and Frankly-020 (YouTube auto-generated). Supersedes the first draft's naive
"active segment extends to the next topic" rule — that version was tested
first and confirmed technically correct (zero lost content, zero orphaned
turns), but was optimizing for the wrong thing. The actual goal is
downstream embedding quality, not coverage: a chunk diluted with unrelated
transitional content produces a worse vector than a shorter, clean one,
for the same reason recentering the ScenarioFacet grid earlier this
project made cosine distance meaningful — noise in a vector actively
degrades retrieval, it doesn't sit there harmlessly.

THREE real decisions baked into this version, each backed by testing
against real files, not picked by feel:

1. CORE WINDOW, not full-gap assignment. A turn only belongs to a topic
   if it falls within min(HARD_CAP, FRACTION * gap-to-next-topic) of that
   topic's own timestamp. Content beyond that window is explicitly tagged
   PLACEHOLDER_TOPIC, not silently absorbed into the nearest topic — this
   is a real, visible signal for downstream consumers, not a discard.
   Tested at fraction=0.25, hard_cap=40 as a defensible middle ground
   between diluted-but-complete and clean-but-fragmentary; RR-25 chunks
   averaged ~348 chars, Frankly-020 ~260 chars at this setting — both in
   a reasonable range for a real embedding (long enough to carry signal,
   short enough to stay on-topic). NOT re-validated against the full
   corpus yet — revisit once real data at scale is available.

2. DURATION-BASED BRANCHING, not series-label branching. Short episodes
   (most Franklys) should be embedded as ONE vector for the whole
   transcript, not chunked — anchored chunking only pays for itself once
   an episode has enough real topic-density to make per-topic vectors
   meaningfully distinct. Real evidence for the threshold: 5 of 6 sampled
   Franklys ran 12.1-30.3 min; the 6th (Frankly_132, the six-fronts
   framework episode — independently already flagged this session as
   substantial enough to deserve full taxonomy-building) ran 53.5 min,
   nearly Interview-length (Interviews sampled: 56.5-109.3 min). There's
   a clean, empty gap between 30.3 and 53.5 in the real data. Threshold
   set at 2100s (35 min): comfortably above every normal Frankly seen,
   comfortably below the one real exception and every Interview. This is
   keyed on duration_seconds directly, NOT on series/episode_type —
   duration varied nearly 2x within "interview" alone in the sample, so
   series label is not a reliable proxy for length.

3. TRANSCRIPT SOURCE MATTERS FOR PARSING, not just metadata. Both TGS-
   provided and YouTube-auto transcripts are auto-generated — RR-25's own
   header says "has not been fully proofed by ISEOF." Neither is a human-
   verified transcript; they differ in which TOOL produced them, not in
   proofed-vs-not. TGS transcripts carry real [HH:MM:SS] speaker turns;
   YouTube transcripts are bare M:SS caption fragments with NO speaker
   attribution — never inferred here, left as speaker=None, matching the
   project's own established precedent for genuinely unattributable
   content (the 20 solo Franklys with timestamps but no speaker labels).
   Real ASR content errors in YouTube transcripts (e.g. Swedish "öre"
   mistranscribed as "era", "Force Majeure" as "Force Major") are left
   AS-IS here — correcting them is a separate, human-reviewed task, not
   something to silently fix during chunking.

USAGE:
    python anchor_transcript_to_shownotes.py
Outputs a list of (show_note_timestamp, topic, chunk_text, is_placeholder,
embed_as_single_vector) rows per record.
"""
import re

FRACTION = 0.25
HARD_CAP_SECONDS = 40
DURATION_THRESHOLD_SECONDS = 2100  # 35 min — see design note #2 above
PLACEHOLDER_TOPIC = "(unlinked transition)"
INTRO_TOPIC = "Intro"


def parse_timestamp_to_seconds(ts):
    parts = [int(p) for p in ts.strip().split(':')]
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = 0, parts[0], parts[1]
    else:
        raise ValueError(f"Unparseable timestamp: {ts!r}")
    return h * 3600 + m * 60 + s


def parse_show_notes_tgs(text):
    notes = []
    for line in text.splitlines():
        m = re.match(r'\|\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*\|\s*([^|]+?)\s*\|', line)
        if m:
            notes.append((parse_timestamp_to_seconds(m.group(1)), m.group(2).strip()))
    return notes


def parse_show_notes_youtube(text):
    notes = []
    for line in text.splitlines():
        m = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s*[\u2013-]\s*(.+)$', line.strip())
        if m and not line.strip().startswith('-'):
            notes.append((parse_timestamp_to_seconds(m.group(1)), m.group(2).strip()))
    return notes


def parse_transcript_tgs(text):
    """[HH:MM:SS] Speaker: text turns. Real speaker attribution preserved."""
    turns = []
    pattern = re.compile(
        r'\[(\d{1,2}:\d{2}:\d{2})\]\s*(?:([A-Z][a-zA-Z.\' ]{1,40}):\s*)?(.*?)(?=\n\[\d{1,2}:\d{2}:\d{2}\]|\Z)',
        re.DOTALL
    )
    for m in pattern.finditer(text):
        body = m.group(3).strip()
        if body:
            turns.append((parse_timestamp_to_seconds(m.group(1)), m.group(2), body))
    return turns


def parse_transcript_youtube(text):
    """Bare M:SS caption lines. Speaker deliberately always None — see
    design note #3. Do not attempt to infer speaker from content."""
    lines = text.splitlines()
    turns = []
    current_ts, buf = None, []
    ts_line_re = re.compile(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s*$')
    for line in lines:
        m = ts_line_re.match(line.strip())
        if m:
            if current_ts is not None and buf:
                turns.append((current_ts, None, ' '.join(buf).strip()))
            current_ts = parse_timestamp_to_seconds(m.group(1))
            buf = []
        elif current_ts is not None and line.strip():
            buf.append(line.strip())
    if current_ts is not None and buf:
        turns.append((current_ts, None, ' '.join(buf).strip()))
    return turns


def assign_with_core_window(show_notes, transcript_turns,
                             fraction=FRACTION, hard_cap=HARD_CAP_SECONDS):
    """The final rule: a turn belongs to a topic only within a window that
    scales with how densely that episode's own show notes are spaced —
    not a fixed duration (which behaves very differently on sparse vs.
    dense episodes) and not "everything until the next topic" (which
    dilutes chunks with unrelated transitional content)."""
    sorted_notes = sorted(show_notes, key=lambda x: x[0])
    segments = {}
    for turn_ts, speaker, text in transcript_turns:
        active_idx = None
        for i, (note_ts, topic) in enumerate(sorted_notes):
            if note_ts <= turn_ts:
                active_idx = i
            else:
                break
        if active_idx is None:
            key = (0, INTRO_TOPIC)
        else:
            note_ts, topic = sorted_notes[active_idx]
            next_ts = sorted_notes[active_idx + 1][0] if active_idx + 1 < len(sorted_notes) else note_ts + hard_cap
            window = min(hard_cap, fraction * (next_ts - note_ts))
            key = (note_ts, topic) if turn_ts - note_ts <= window else (note_ts, PLACEHOLDER_TOPIC)
        segments.setdefault(key, []).append((speaker, text))
    return segments


def build_records(show_notes, transcript_turns, duration_seconds):
    """Final output shape: one row per real (non-placeholder, non-intro)
    segment PLUS the placeholder/intro segments tagged as such — never
    silently dropped, always distinguishable. embed_as_single_vector is
    the same value on every row for a given episode; the caller decides
    whether to actually embed per-chunk or embed the whole transcript
    once based on that flag."""
    single_vector = duration_seconds is not None and duration_seconds < DURATION_THRESHOLD_SECONDS
    segments = assign_with_core_window(show_notes, transcript_turns)
    rows = []
    for (ts, topic), turns in sorted(segments.items()):
        text = ' '.join(t for _, t in turns)
        rows.append({
            "show_note_timestamp": ts,
            "topic": topic,
            "chunk_text": text,
            "is_placeholder": topic in (PLACEHOLDER_TOPIC, INTRO_TOPIC),
            "embed_as_single_vector": single_vector,
        })
    return rows


if __name__ == "__main__":
    # Smoke test against the two real files used to design this.
    with open("/mnt/user-data/uploads/RR-25-Learning-in-a-Way-that-Actually-Matters.md") as f:
        rr25 = f.read()
    with open("/mnt/user-data/uploads/Frankly-020-KeepingWarmData.md") as f:
        f020 = f.read()

    rr25_rows = build_records(parse_show_notes_tgs(rr25), parse_transcript_tgs(rr25), duration_seconds=4230)
    f020_rows = build_records(parse_show_notes_youtube(f020), parse_transcript_youtube(f020), duration_seconds=1738)

    print(f"RR-25: {len(rr25_rows)} rows, embed_as_single_vector={rr25_rows[0]['embed_as_single_vector']}")
    print(f"Frankly-020: {len(f020_rows)} rows, embed_as_single_vector={f020_rows[0]['embed_as_single_vector']}")
