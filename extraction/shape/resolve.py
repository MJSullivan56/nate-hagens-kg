"""resolve.py — map a transcript filename to its canonical episode page.

Needed because the .txt batch cannot be trusted to identify itself. Unlike the
hand-enriched .md files, a .txt carries NO metadata at all — no URL, no title,
no date — so the filename is the only handle, and the filename's episode number
is demonstrably wrong on a meaningful fraction of the corpus.

The evidence: nine number collisions exist among the 301 .txt files, and in
each pair one file's number is off by one.

    TGS-046-VandanaShivaTranscript      -> 46-vandana-shiva     number OK
    TGS-046-PatrickOphulsTranscript     -> 47-patrick-ophuls    number WRONG
    TGS118MichaelEveryTranscript        -> 118-michael-every    number OK
    TGS118LutherKruegerTranscript       -> 119-luther-krueger   number WRONG

But neither signal can simply outrank the other, and getting this backwards is
easy. Name-first is wrong: many guests appear on several episodes (Daniel
Schmachtenberger on eight, Art Berman on six, Chuck Watson on five), so the
plain name is often ambiguous and only the number separates them. Number-first
is also wrong, as the collisions above show.

    TGS-017-ChuckWatsonTranscript       -> 17-chuck-watson-nuclear-war (NOT 04)
    TGS148DickGephardtTranscript        -> 148-richard-gephardt        (NOT 01)
    TGS-003-ArtBerman (first interview) -> 03-arthurberman             (NOT 44)

So both signals are SCORED together: name similarity (fuzzy, since the corpus
writes "ArtBerman" for "arthurberman" and "DickGephardt" for "richard-gephardt")
plus a bonus when the number agrees. A clean name match can still beat a
disagreeing number, but a merely-similar name cannot. Every case where the
chosen episode's number differs from the filename's is reported rather than
silently resolved — "the filename says 46 but this is really 47" should not be
discovered later, downstream.
"""

from __future__ import annotations

import difflib
import os
import re
import unicodedata
from dataclasses import dataclass, field as dc_field

# Tokens that are packaging, not identity: file extensions, the word
# "Transcript", and the trailing copy-counter that duplicate downloads pick up
# ("...Transcript-1.txt", "...Transcript2.txt").
EXT_RE = re.compile(r"(?i)(\.txt|\.docx|\.pdf|\.doc)+$")
NOISE_RE = re.compile(r"(?i)(transcript|complete|final|draft|copy|v\d+)")
TRAILING_COUNT_RE = re.compile(r"[-_ ]*\d{1,2}$")

SERIES_PREFIX = [
    (re.compile(r"(?i)^RR[-_ ]*(\d+)"), "roundtable"),
    (re.compile(r"(?i)^reality[-_ ]*roundtable[-_ ]*(\d+)"), "roundtable"),
    (re.compile(r"(?i)^Frankly[-_ ]*(\d+)"), "frankly"),
    (re.compile(r"(?i)^TGS[-_ ]*(\d+)"), "interview"),
]


def norm(s: str) -> str:
    """Fold to comparable form: ASCII, lowercase, alphanumerics only."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


@dataclass
class Parsed:
    filename: str
    stem: str
    series: str | None = None
    number: int | None = None
    name_part: str = ""
    name_norm: str = ""


def parse_filename(filename: str) -> Parsed:
    stem = EXT_RE.sub("", os.path.basename(filename))
    p = Parsed(filename=os.path.basename(filename), stem=stem)

    rest = stem
    for pat, series in SERIES_PREFIX:
        m = pat.match(stem)
        if m:
            p.series = series
            p.number = int(m.group(1))
            rest = stem[m.end():]
            break

    rest = TRAILING_COUNT_RE.sub("", NOISE_RE.sub("", rest))
    p.name_part = rest.strip("-_ .")
    p.name_norm = norm(p.name_part)
    return p


def slug_identity(slug: str) -> tuple[int | None, str]:
    """Split a catalog slug into (episode number, normalized name).

    Two Frankly slug styles exist and both must be handled: the early ones are
    "frankly-03-energy-blindness", the later ones drop the word and read
    "20-keeping-warm-data". Missing the first style leaves those episodes with
    no number at all, so they can never earn the number bonus.
    """
    s = re.sub(r"^archive-", "", slug)
    s = re.sub(r"(?i)^frankly[-_]", "", s)
    m = re.match(r"^0*(\d+)[-_](.*)$", s)
    if m:
        return int(m.group(1)), norm(m.group(2))
    m = re.match(r"^(?:reality-)?roundtable-0*(\d+)$", s)
    if m:
        return int(m.group(1)), ""
    m = re.match(r"^rr-?0*(\d+)[-_]?(.*)$", s)
    if m:
        return int(m.group(1)), norm(m.group(2))
    return None, norm(s)


@dataclass
class Resolution:
    parsed: Parsed
    url: str | None = None
    slug: str | None = None
    catalog_number: int | None = None
    catalog_title: str | None = None
    method: str = "unresolved"
    confidence: str = "none"          # exact | strong | weak | none
    score: float = 0.0
    notes: list = dc_field(default_factory=list)


def build_index(catalog: dict) -> dict:
    """Index the catalog by normalized name and by series:number."""
    by_name: dict[str, list] = {}
    by_num: dict[str, list] = {}
    for e in catalog["entries"]:
        num, name = slug_identity(e["slug"])
        series = ("frankly" if e["post_type"] == "frankly-original"
                  else "roundtable" if re.match(r"^(reality-)?roundtable-|^rr-?\d", e["slug"])
                  else "interview")
        rec = {**e, "num": num, "name": name, "series": series,
               "title_norm": norm(e["title"])}
        if name:
            by_name.setdefault(name, []).append(rec)
        if num is not None:
            by_num.setdefault(f"{series}:{num}", []).append(rec)
    by_series: dict[str, list] = {}
    unique = {}
    for v in list(by_num.values()) + list(by_name.values()):
        for rec in v:
            unique[rec["link"]] = rec
    for rec in unique.values():
        by_series.setdefault(rec["series"], []).append(rec)
    return {"by_name": by_name, "by_num": by_num,
            "by_series": by_series, "unique": list(unique.values())}


NAME_WEIGHT = 2.0        # a perfect name match alone scores 2.0
NUMBER_BONUS = 1.5       # agreeing number adds 1.5
STRONG_NAME = 0.85       # name similarity at/above this counts as a real match
OVERRIDE_MARGIN = 0.3    # how much better a name must be to overrule the number


def name_similarity(a: str, b: str) -> float:
    """Fuzzy ratio between two normalized names, 0..1.

    Fuzzy rather than exact because the corpus consistently abbreviates:
    "ArtBerman" for "arthurberman", "DickGephardt" for "richard-gephardt",
    "DanielSchmactenberger" for "daniel-schmachtenberger" (a real misspelling
    that appears in both the filenames AND some catalog slugs). It also lets a
    filename name match a longer slug that carries a subtitle, as in
    "ChuckWatson" against "chuck-watson-nuclear-war".
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    base = difflib.SequenceMatcher(None, a, b).ratio()
    # Reward a clean prefix relationship — a slug with a trailing subtitle
    # should not be penalised purely for being longer than the filename.
    if a.startswith(b) or b.startswith(a):
        base = max(base, 0.80)
    return base


OVERRIDES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "manual_overrides.yaml")


def load_overrides(path: str = OVERRIDES_PATH) -> dict:
    """Human adjudications keyed by transcript filename (see that file)."""
    if not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as fh:
        return (yaml.safe_load(fh) or {}).get("overrides") or {}


def resolve(filename: str, catalog: dict, index: dict | None = None,
            overrides: dict | None = None,
            exclude: set | None = None) -> Resolution:
    index = index or build_index(catalog)
    p = parse_filename(filename)
    r = Resolution(parsed=p)

    # A human decision always wins, and is checked before any matching runs.
    ov = (overrides if overrides is not None else load_overrides()).get(p.filename)
    if ov:
        url = ov.get("url")
        if url:
            rec = next((c for c in index["unique"] if c["link"].rstrip("/") == url.rstrip("/")),
                       None)
            r.url = url
            r.slug = (rec or {}).get("slug") or url.rstrip("/").rsplit("/", 1)[-1]
            r.catalog_number = (rec or {}).get("num")
            r.catalog_title = (rec or {}).get("title")
            r.method, r.confidence, r.score = "manual-override", "exact", 99.0
            if ov.get("note"):
                r.notes.append(f"manual override: {ov['note']}")
            if rec is None:
                r.notes.append("override URL is not in the catalog — "
                               "will be fetched directly")
            return r
        if ov.get("skip"):
            r.method, r.confidence = "skipped", "none"
            r.notes.append(f"manually skipped: {ov.get('note') or 'no reason given'}")
            return r

    # Candidates: everything in the same series. The pool is small (a few
    # hundred), so scoring all of it is cheaper than staged fallbacks and avoids
    # the ordering bugs that staged matching invites.
    pool = [c for c in index["by_series"].get(p.series, [])] if p.series else index["unique"]
    if not pool:
        pool = index["unique"]
    # `exclude` holds pages already claimed by a more confident resolution, so a
    # second transcript cannot land on the same episode. See resolve_collisions.
    if exclude:
        pool = [c for c in pool if c["link"].rstrip("/") not in exclude]

    scored = []
    for c in pool:
        ratio = max(name_similarity(p.name_norm, c["name"]),
                    name_similarity(p.name_norm, c["title_norm"]) * 0.9)
        scored.append({"ratio": ratio, "rec": c,
                       "num_match": p.number is not None and c["num"] == p.number})
    if not scored:
        r.notes.append("no candidates in catalog for this series")
        return r

    num_cand = next((s for s in scored if s["num_match"]), None)
    by_ratio = sorted(scored, key=lambda s: -s["ratio"])
    best_name = by_ratio[0]

    # Alternatives whose name matches strongly, other than the numbered one.
    alts = [s for s in by_ratio
            if s["ratio"] >= STRONG_NAME and s is not num_cand and s["rec"]["name"]]

    chosen = reason = None
    if num_cand is not None:
        # The number points somewhere. Override it ONLY when the strong-name
        # alternatives all describe the SAME identity, which is the signature of
        # a genuine off-by-one (TGS-097-HelenThompson really is #98, and both
        # 98- and 152-helen-thompson are the same person, so either confirms the
        # name while the number does not).
        #
        # When the strong alternatives carry DIFFERENT names, they are false
        # friends from a shared title phrase — "How to Think About the Future
        # Part 5" resembles parts 1 through 4 without being any of them — and
        # the number is the better evidence.
        alt_names = {s["rec"]["name"] for s in alts}
        if (alts and len(alt_names) == 1
                and alts[0]["ratio"] - num_cand["ratio"] > OVERRIDE_MARGIN):
            same = [s for s in alts if s["rec"]["num"] is not None]
            chosen = (min(same, key=lambda s: abs(s["rec"]["num"] - p.number))
                      if same else alts[0])
            reason = "name-override"
        else:
            chosen = num_cand
            reason = "number" if num_cand["ratio"] < 0.6 else "name+number"
    elif best_name["ratio"] >= STRONG_NAME:
        chosen, reason = best_name, "name"
    # Deliberately no looser fallback below STRONG_NAME. Where neither the
    # number nor the name is good enough, guessing would produce a
    # confident-looking wrong answer; the file is reported unresolved instead and
    # a human adjudicates it via manual_overrides.yaml. This matches the repo's
    # standing rule that the methodology stays human-in-the-loop.

    if chosen is None:
        r.notes.append(
            f"no catalog match: no episode at {p.series} #{p.number} and best name "
            f"similarity only {best_name['ratio']:.2f} ({best_name['rec']['slug']})")
        return r

    best, ratio = chosen["rec"], chosen["ratio"]
    r.url, r.slug = best["link"], best["slug"]
    r.catalog_number, r.catalog_title = best["num"], best["title"]
    r.score = round(NAME_WEIGHT * ratio + (NUMBER_BONUS if chosen["num_match"] else 0), 2)
    r.method = reason
    r.confidence = ("exact" if ratio >= 0.95 and chosen["num_match"]
                    else "strong" if (chosen["num_match"] and ratio >= 0.6) or ratio >= 0.95
                    else "weak")

    if p.number is not None and best["num"] is not None and best["num"] != p.number:
        r.notes.append(
            f"filename says {p.series} #{p.number} but resolved to #{best['num']} "
            f"({best['slug']}, name similarity {ratio:.2f}) — filename number looks wrong")
    if reason == "number" and ratio < 0.4:
        r.notes.append(
            f"matched on number alone; the site titles this "
            f"{best['slug']!r}, which does not resemble the filename — VERIFY")
    return r


CONFIDENCE_RANK = {"exact": 3, "strong": 2, "weak": 1, "none": 0}


def resolve_collisions(results: list, catalog: dict, index: dict) -> list:
    """Ensure no two transcripts claim the same episode page.

    Each transcript is a distinct episode, so two of them resolving to one page
    means at least one is wrong. This happened for real: two Jean-Marc Jancovici
    transcripts both landed on 84-jean-marc-jancovici, because the site's OTHER
    Jancovici episode has an unnumbered slug
    ("jean-marc-jancovici-sobriete-vs-poverty-...") that scored lower on name
    similarity than the exact-match one.

    Resolution: the highest-confidence claimant keeps the page (a manual
    override always wins), and the others are re-resolved with the taken pages
    excluded, so they fall through to their next-best candidate.
    """
    by_url: dict[str, list] = {}
    for r in results:
        if r.url:
            by_url.setdefault(r.url.rstrip("/"), []).append(r)

    taken = set()
    losers = []
    for url, claims in by_url.items():
        if len(claims) == 1:
            taken.add(url)
            continue
        claims.sort(key=lambda r: (r.method == "manual-override",
                                   CONFIDENCE_RANK.get(r.confidence, 0),
                                   r.score), reverse=True)
        taken.add(url)
        winner = claims[0]
        for other in claims[1:]:
            other.notes.append(
                f"page {url.rsplit('/', 1)[-1]} was already claimed by "
                f"{winner.parsed.filename} ({winner.method}/{winner.confidence}); "
                f"re-resolved to the next-best candidate")
            losers.append(other)

    out = list(results)
    for loser in losers:
        prior_notes = list(loser.notes)
        fresh = resolve(loser.parsed.filename, catalog, index, exclude=taken)
        fresh.notes = prior_notes + fresh.notes
        if fresh.url:
            taken.add(fresh.url.rstrip("/"))
        out[out.index(loser)] = fresh
    return out
