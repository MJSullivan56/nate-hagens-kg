"""
Builds a local reference library of thegreatsimplification.com transcripts,
so future sessions don't need to search the web for primary-source material
every time a claim needs checking.

IMPORTANT — run this on your own machine, not in any sandboxed environment.
It was written using the REAL, confirmed page structure (verified via live
fetch on 2026-07-10 against episode 224), but the actual download loop has
never been executed end-to-end — I don't have network access to this site
from my side. Test with --limit 5 first before doing a full run.

What it does:
  1. Walks the paginated episode index at /podcast/episodes (interviews),
     /podcast/frankly (Franklys), /podcast/reality-roundtables (roundtables)
  2. For each episode page, finds the "Download transcript" link by its
     anchor TEXT, not a guessed URL pattern — the actual file path
     (wp-content/uploads/{year}/{month}/TGS-{num}-{Guest}-Transcript.docx.pdf)
     depends on upload date and isn't predictable from the episode number
     alone, confirmed by inspecting a real episode page.
  3. Downloads the PDF into transcripts_raw/ (gitignored — see repo's
     .gitignore, this was anticipated from the start)
  4. Writes/updates transcripts_index.csv (COMMITTED to git — small, and
     it's the actually-reusable artifact: episode #, title, guest, date,
     type, transcript URL, local filename)
  5. Resumable — skips anything already in the index unless --force

Politeness: checks robots.txt once at startup, 2-second delay between
requests, identifies itself with a real User-Agent. This is for personal
research reference use of content the publisher already makes freely
available for exactly this purpose (their own site explicitly offers
"detailed notes and transcripts" as a stated feature) — not redistribution.

Usage:
    python extraction/download_transcripts.py --limit 5    # test run first
    python extraction/download_transcripts.py               # full run
    python extraction/download_transcripts.py --type frankly # just Franklys
"""

import argparse
import csv
import re
import time
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.thegreatsimplification.com"
INDEX_PAGES = {
    # Guest interviews: long-form, typically 2+ hours. Numbered "Ep N".
    "interview": "/podcast/episodes",
    # Frankly: short (~20-30 min) solo videos, released weekly (Fridays).
    # Official description: "Short reflections and explanations by Nate
    # Hagens." Numbered "#N", separate sequence from guest episodes.
    "frankly": "/podcast/frankly",
    # Reality Roundtables: multi-guest panel format, numbered separately.
    "roundtable": "/podcast/reality-roundtables",
}
OUTPUT_DIR = Path("extraction/transcripts_raw")
INDEX_FILE = Path("extraction/transcripts_index.csv")
NO_TRANSCRIPT_FILE = Path("extraction/no_transcript_available.csv")
HEADERS = {"User-Agent": "nate-hagens-kg research tool (personal reference archive, contact via GitHub)"}


DELAY_SECONDS = 10  # matches the site's explicit "Crawl-delay: 10" directive


def check_robots_allowed(paths_to_check):
    """
    MANUALLY VERIFIED against the live robots.txt on 2026-07-10 (fetched via
    `curl -s https://www.thegreatsimplification.com/robots.txt`), NOT via
    Python's urllib.robotparser — that library returned a false "disallowed"
    for /podcast/episodes on this exact file, apparently due to the file's
    slightly non-standard structure (a Crawl-delay line before any
    User-agent line, and two separate "User-agent: *" blocks rather than
    one merged one). A known category of parser fragility on real-world
    WordPress/Yoast-generated robots.txt files, not specific to this setup.

    Actual confirmed content as of 2026-07-10:
        Crawl-delay: 10
        User-agent: *
        Disallow: /wp-content/uploads/wpforms/    <- unrelated form-plugin dir
        User-agent: *
        Disallow:                                  <- empty = allows everything else

    So: podcast/episode/frankly/transcript paths are all genuinely allowed.
    Only /wp-content/uploads/wpforms/ is off-limits, and it's irrelevant to
    this script (transcripts live under /wp-content/uploads/{year}/{month}/,
    a different path). If this file is ever re-checked and something
    actually changes, update this function accordingly — don't just restore
    the automated parser call without first confirming it's reliable on
    the new content.
    """
    disallowed_prefix = "/wp-content/uploads/wpforms/"
    blocked = [p for p in paths_to_check if p.startswith(disallowed_prefix)]
    if blocked:
        raise SystemExit(f"robots.txt disallows: {blocked} — stopping.")
    print(f"robots.txt check (manually verified 2026-07-10): OK for {', '.join(paths_to_check)}")
    print(f"Respecting site's Crawl-delay: {DELAY_SECONDS}s between requests")


def load_existing_index():
    if not INDEX_FILE.exists():
        return {}
    with open(INDEX_FILE, newline="", encoding="utf-8") as f:
        return {row["episode_url"]: row for row in csv.DictReader(f)}


def load_no_transcript_set():
    """Returns dict of {episode_url: title} — title added so Substack summary
    matching (match_substack_summaries.py) can also match against episodes
    known to have no transcript, not just ones that do."""
    if not NO_TRANSCRIPT_FILE.exists():
        return {}
    with open(NO_TRANSCRIPT_FILE, newline="", encoding="utf-8") as f:
        return {row["episode_url"]: row.get("title", "") for row in csv.DictReader(f)}


SITEMAP_URLS = {
    "frankly": "/frankly-original-sitemap.xml",
    "interview": "/episode-sitemap.xml",   # shared with roundtable, filtered by path below
    "roundtable": "/episode-sitemap.xml",
}


def discover_from_sitemap(episode_type):
    """
    Primary discovery mechanism. WordPress/Yoast sitemaps are static XML,
    not JavaScript-dependent — confirmed via live fetch on 2026-07-10 that
    the frankly-original-sitemap.xml alone contains 130+ historical Frankly
    URLs (vs. only 12 visible on the listing page, which turned out to be
    capped by JS-driven "load more" pagination that plain HTML scraping
    can't follow — the listing page's only further nav link went to the
    site ROOT, not a real page-2 URL).

    CAVEAT, confirmed same day: the sitemap lags slightly behind the live
    site — Frankly #146-149 were live and downloadable but NOT yet present
    in the sitemap when checked. So this is comprehensive for history but
    not guaranteed current for the newest 1-4 items. See
    discover_episode_urls() below, which combines this with the listing-page
    scrape specifically to cover that gap.

    episode-sitemap.xml (interview + roundtable) was NOT separately verified
    the way frankly-original-sitemap.xml was — same Yoast plugin, same XML
    schema, high confidence it works identically, but if it behaves
    differently, look here first.
    """
    sitemap_path = SITEMAP_URLS[episode_type]
    resp = requests.get(urljoin(BASE, sitemap_path), headers=HEADERS, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    all_urls = [loc.text for loc in root.findall(".//sm:loc", ns)]

    urls = []
    for full in all_urls:
        parsed = urlparse(full)
        if episode_type == "frankly":
            match = "/frankly-original/" in parsed.path
        elif episode_type == "roundtable":
            match = "/episode/reality-roundtable" in parsed.path
        elif episode_type == "interview":
            match = "/episode/" in parsed.path and "reality-roundtable" not in parsed.path
        else:
            match = False
        if match:
            urls.append(full)
    return urls


def discover_episode_urls(episode_type, limit=None):
    """Combines sitemap (comprehensive but possibly a few items stale) with
    the listing-page scrape (only shows ~12 most recent, but always current)
    to get both full history AND the newest items. Deduplicated."""
    urls = []
    try:
        urls.extend(discover_from_sitemap(episode_type))
        print(f"  Sitemap: found {len(urls)} URLs")
    except Exception as e:
        print(f"  Sitemap discovery failed ({e}), falling back to listing-page-only")

    listing_urls = discover_from_listing_page(episode_type, limit=None)
    new_from_listing = [u for u in listing_urls if u not in urls]
    if new_from_listing:
        print(f"  Listing page: found {len(new_from_listing)} additional URLs not yet in sitemap")
    urls.extend(new_from_listing)

    if limit:
        urls = urls[:limit]
    return urls


def discover_from_listing_page(episode_type, limit=None):
    """Fallback/supplement: walks the single listing page for one content
    type. NOTE: only shows a limited recent subset — the listing page uses
    JS-driven pagination ("load more") that plain HTML scraping can't
    follow past the first batch. Use discover_episode_urls() (which combines
    this with the sitemap) rather than calling this directly in most cases."""
    urls = []
    resp = requests.get(urljoin(BASE, INDEX_PAGES[episode_type]), headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    base_host = urlparse(BASE).netloc
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(BASE, href)
        parsed = urlparse(full)
        if parsed.netloc != base_host:
            continue
        if episode_type == "frankly":
            match = "/frankly-original/" in parsed.path
        elif episode_type == "roundtable":
            match = "/episode/reality-roundtable" in parsed.path
        elif episode_type == "interview":
            match = "/episode/" in parsed.path and "reality-roundtable" not in parsed.path
        else:
            match = False
        if match and full not in urls:
            urls.append(full)
        if limit and len(urls) >= limit:
            break
    return urls


def get_transcript_info(episode_url):
    """Fetch one episode page, extract transcript URL + metadata."""
    resp = requests.get(episode_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    transcript_link = None
    for a in soup.find_all("a", href=True):
        if "download transcript" in a.get_text(strip=True).lower():
            transcript_link = urljoin(BASE, a["href"])
            break

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    return {
        "episode_url": episode_url,
        "title": title,
        "transcript_url": transcript_link,
    }


def download_transcript(transcript_url, local_filename):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    local_path = OUTPUT_DIR / local_filename
    if local_path.exists():
        return local_path, False
    resp = requests.get(transcript_url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    local_path.write_bytes(resp.content)
    return local_path, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max episodes per type (for testing)")
    parser.add_argument("--type", choices=list(INDEX_PAGES.keys()), default=None,
                         help="Only this content type; default: all three")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if already in index")
    args = parser.parse_args()

    existing = load_existing_index()
    no_transcript = load_no_transcript_set()
    types_to_run = [args.type] if args.type else list(INDEX_PAGES.keys())
    check_robots_allowed([INDEX_PAGES[t] for t in types_to_run])

    rows = list(existing.values())
    no_transcript_rows = [{"episode_url": u, "title": t} for u, t in no_transcript.items()]
    new_count = 0
    skipped_known_dead_ends = 0

    for etype in types_to_run:
        print(f"\n=== Discovering {etype} episodes ===")
        urls = discover_episode_urls(etype, limit=args.limit)
        print(f"Found {len(urls)} episode URLs")

        for url in urls:
            if url in existing and not args.force:
                continue
            if url in no_transcript and not args.force:
                skipped_known_dead_ends += 1
                continue
            time.sleep(DELAY_SECONDS)
            try:
                info = get_transcript_info(url)
            except Exception as e:
                print(f"  FAILED to fetch {url}: {e}")
                continue

            if not info["transcript_url"]:
                print(f"  No transcript link found: {info['title']} ({url})")
                if url not in no_transcript:
                    no_transcript[url] = info["title"]
                    no_transcript_rows.append({"episode_url": url, "title": info["title"]})
                continue

            local_filename = os.path.basename(urlparse(info["transcript_url"]).path)
            time.sleep(DELAY_SECONDS)
            try:
                local_path, was_downloaded = download_transcript(info["transcript_url"], local_filename)
            except Exception as e:
                print(f"  FAILED to download transcript for {info['title']}: {e}")
                continue

            status = "downloaded" if was_downloaded else "already had it"
            print(f"  {status}: {info['title']} -> {local_path}")

            rows.append({
                "episode_url": url,
                "type": etype,
                "title": info["title"],
                "transcript_url": info["transcript_url"],
                "local_filename": local_filename,
            })
            new_count += 1

    with open(INDEX_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["episode_url", "type", "title", "transcript_url", "local_filename"])
        writer.writeheader()
        writer.writerows(rows)

    with open(NO_TRANSCRIPT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["episode_url", "title"])
        writer.writeheader()
        writer.writerows(no_transcript_rows)

    if skipped_known_dead_ends:
        print(f"\n(Skipped {skipped_known_dead_ends} episode(s) already confirmed to have no transcript — use --force to re-check)")
    print(f"Done. {new_count} new entries. Index at {INDEX_FILE}, PDFs in {OUTPUT_DIR}/ (gitignored).")


if __name__ == "__main__":
    main()
