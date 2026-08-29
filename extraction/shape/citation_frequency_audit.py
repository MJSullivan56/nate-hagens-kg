#!/usr/bin/env python3
"""citation_frequency_audit.py

Standalone, zero-cost analysis: aggregate every show-notes link across the
whole nate-hagens-kg corpus's existing scrape metadata (YAML/JSON), rank
by frequency, and separate self-referential domains (Wikipedia, YouTube,
the show's own site) from genuine third-party sources worth monitoring
for new content.

Independent of the transcript-chunking pilot -- reads only the scrape
metadata files, not transcripts or chunked output. Pure local text/URL
processing, no LLM calls, no API cost.

Usage:
    python3 citation_frequency_audit.py <scrape_metadata_dir> [--output report.md]

Reads every .yaml/.json file in the given directory (same schema either
way, per this project's own established convention), extracts every
show_notes[].links[].url, normalizes each to a bare domain, and produces
a ranked report -- domain frequency, a sample of real link labels seen
for that domain (for eyeballing what it actually is), and a clear split
between self-referential and third-party domains.
"""

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from urllib.parse import urlparse

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

# Domains that are internal to this project's own ecosystem, not real
# third-party sources to monitor for new content. Extend as real corpus
# data surfaces more of these.
SELF_REFERENTIAL_DOMAINS = {
    "www.thegreatsimplification.com",
    "thegreatsimplification.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "en.wikipedia.org",
    "wikipedia.org",
    "open.spotify.com",
    "podcasts.apple.com",
}


def load_scrape_file(path):
    """Load a single scrape metadata file, .yaml or .json -- same schema
    either way, per this project's own established convention."""
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith(".yaml") or path.endswith(".yml"):
            if not HAVE_YAML:
                print(f"WARNING: pyyaml not installed, skipping {path}", file=sys.stderr)
                return None
            return yaml.safe_load(f)
        else:
            return json.load(f)


def extract_links(data, source_file):
    """Extract every (url, label, episode_title) tuple from a scrape
    record's show_notes array. Real schema, confirmed across many real
    episodes this session: show_notes: [{timestamp, seconds, topic,
    links: [{label, url}]}]."""
    out = []
    if not data:
        return out
    episode_title = data.get("title", os.path.basename(source_file))
    for entry in data.get("show_notes", []) or []:
        for link in entry.get("links", []) or []:
            url = link.get("url")
            label = link.get("label", "")
            if url:
                out.append((url, label, episode_title))
    return out


def normalize_domain(url):
    """Bare, lowercase domain -- e.g. 'https://www.nature.com/articles/x'
    -> 'www.nature.com'."""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scrape_dir", help="Directory of scrape metadata files (.yaml/.json)")
    parser.add_argument("--output", default=None, help="Report output path (default: citation-frequency-report.md next to this script)")
    parser.add_argument("--top-n", type=int, default=30, help="How many top domains to show per category (default: 30)")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.scrape_dir, "*.yaml"))) + \
            sorted(glob.glob(os.path.join(args.scrape_dir, "*.yml"))) + \
            sorted(glob.glob(os.path.join(args.scrape_dir, "*.json")))

    if not files:
        print(f"No .yaml/.yml/.json files found in {args.scrape_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(files)} scrape metadata files.")

    domain_counts = Counter()
    domain_sample_labels = defaultdict(list)
    domain_episodes = defaultdict(set)
    parse_errors = []

    for path in files:
        try:
            data = load_scrape_file(path)
        except Exception as e:
            parse_errors.append((path, str(e)))
            continue
        for url, label, episode_title in extract_links(data, path):
            domain = normalize_domain(url)
            if not domain:
                continue
            domain_counts[domain] += 1
            domain_episodes[domain].add(episode_title)
            if len(domain_sample_labels[domain]) < 5 and label:
                domain_sample_labels[domain].append(label)

    total_links = sum(domain_counts.values())
    print(f"Total links extracted: {total_links} across {len(domain_counts)} distinct domains.")
    if parse_errors:
        print(f"WARNING: {len(parse_errors)} files failed to parse:", file=sys.stderr)
        for path, err in parse_errors[:10]:
            print(f"  {path}: {err}", file=sys.stderr)

    self_ref = {d: c for d, c in domain_counts.items() if d in SELF_REFERENTIAL_DOMAINS}
    third_party = {d: c for d, c in domain_counts.items() if d not in SELF_REFERENTIAL_DOMAINS}

    lines = []
    lines.append("# Citation frequency audit — show-notes links across the corpus")
    lines.append("")
    lines.append(
        f"Analyzed {len(files)} scrape metadata files, {total_links} total links, "
        f"{len(domain_counts)} distinct domains. Pure local URL aggregation — "
        "no API calls, no cost."
    )
    if parse_errors:
        lines.append(f"\n**{len(parse_errors)} files failed to parse** — see stderr output.")
    lines.append("")

    lines.append("## Self-referential domains (internal to this project's own ecosystem)")
    lines.append("")
    lines.append("Not useful as a 'monitor for new content' list — these are the show's")
    lines.append("own site, YouTube back-links, Wikipedia, podcast platforms.")
    lines.append("")
    lines.append("| domain | count | episodes citing it |")
    lines.append("|---|---|---|")
    for domain, count in sorted(self_ref.items(), key=lambda x: -x[1]):
        lines.append(f"| {domain} | {count} | {len(domain_episodes[domain])} |")
    lines.append("")

    lines.append(f"## Top {args.top_n} third-party domains — the real bootstrap source list")
    lines.append("")
    lines.append("| rank | domain | count | episodes citing it | sample link labels seen |")
    lines.append("|---|---|---|---|---|")
    for i, (domain, count) in enumerate(sorted(third_party.items(), key=lambda x: -x[1])[:args.top_n], 1):
        samples = "; ".join(domain_sample_labels[domain][:3])
        lines.append(f"| {i} | {domain} | {count} | {len(domain_episodes[domain])} | {samples} |")
    lines.append("")

    lines.append("## What this tells you")
    lines.append("")
    lines.append(
        "- Domains near the top, cited across *many distinct episodes* (not just "
        "many times within one dense episode), are the strongest bootstrap "
        "candidates — real, repeated editorial trust signal from Nate's own team."
    )
    lines.append(
        "- A domain with a high count concentrated in very few episodes is a "
        "different signal (one episode citing one source heavily) — worth looking "
        "at separately, not folded into the same ranking."
    )
    lines.append(
        "- The 'episodes citing it' column matters more than raw count for this "
        "specific purpose — it answers 'how many independent editorial judgments "
        "trusted this source', not just 'how many links exist'."
    )

    out_path = args.output or "citation-frequency-report.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
