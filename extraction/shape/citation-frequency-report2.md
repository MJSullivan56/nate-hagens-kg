# Citation frequency audit — show-notes links across the corpus

Analyzed 57 scrape metadata files, 3919 total links, 1375 distinct domains. Pure local URL aggregation — no API calls, no cost.

## Self-referential domains (internal to this project's own ecosystem)

Not useful as a 'monitor for new content' list — these are the show's
own site, YouTube back-links, Wikipedia, podcast platforms.

| domain | count | episodes citing it |
|---|---|---|
| en.wikipedia.org | 570 | 49 |
| www.thegreatsimplification.com | 203 | 38 |
| www.youtube.com | 58 | 30 |
| youtu.be | 55 | 27 |
| youtube.com | 10 | 8 |
| podcasts.apple.com | 1 | 1 |
| thegreatsimplification.com | 1 | 1 |

## Top 30 third-party domains — the real bootstrap source list

| rank | domain | count | episodes citing it | sample link labels seen |
|---|---|---|---|---|
| 1 | www.britannica.com | 109 | 33 | Britannica; Britannica; Britannica |
| 2 | www.sciencedirect.com | 100 | 32 | ScienceDirect; ScienceDirect; Economic superorganism |
| 3 | read.realityblind.world | 87 | 33 | Reality Blind; Reality Blind; Reality Blind |
| 4 | pmc.ncbi.nlm.nih.gov | 73 | 19 | inattention; Emotional Reasoning and Psychopathology (Gangemi et al.); Nervous system overwhelm |
| 5 | www.nature.com | 42 | 24 | Ecological decay; Energy depletion; Nature |
| 6 | ourworldindata.org | 34 | 19 | Soils; Fisheries; 80% of the world still runs on fossil fuels |
| 7 | lectica.org | 29 | 1 | Dawson CV; Publications; Lectica |
| 8 | www.theguardian.com | 28 | 20 | Guardian; Guardian; Guardian |
| 9 | www.reuters.com | 26 | 12 | Reuters; Reuters graphic; Reuters |
| 10 | www.pnas.org | 26 | 15 | PNAS; N/P cycles; Economy |
| 11 | www.ncbi.nlm.nih.gov | 26 | 12 | NCBI; NCBI; PMC |
| 12 | www.psychologytoday.com | 24 | 10 | Psychology Today; Psychology Today; Agency |
| 13 | www.iea.org | 22 | 11 | IEA WEO 2025; AI hyperscaler and energy build-outs; IEA |
| 14 | www.eia.gov | 22 | 9 | EIA; EIA; EIA |
| 15 | link.springer.com | 21 | 17 | Springer; Springer; Springer |
| 16 | pubmed.ncbi.nlm.nih.gov | 21 | 15 | Stress-sensitive inference of task controllability (Ligneul et al.); Developmental shifts in computations used to detect environmental controllability (Raab et al.); Sugar |
| 17 | www.investopedia.com | 20 | 9 | Investopedia; Investopedia; Shortfall risk |
| 18 | www.science.org | 19 | 12 | Biodiversity loss; Biodiversity loss; Science.org |
| 19 | www.pewresearch.org | 16 | 11 | Pew; Pew survey; Pew |
| 20 | www.linkedin.com | 15 | 12 | LinkedIn; Sian Sutherland; LinkedIn |
| 21 | plato.stanford.edu | 15 | 14 | Stanford Encyclopedia; Stanford; Stanford Encyclopedia |
| 22 | www.warmdata.life | 14 | 3 | Site; Bio; Nora Bateson |
| 23 | www.npr.org | 14 | 12 | Strait of Hormuz practical closure; Fertilizer; NPR |
| 24 | www.resilience.org | 14 | 14 | Resilience; William Rees; Bio |
| 25 | dothemath.ucsd.edu | 14 | 3 | Peak Population; Murphy info; Do The Math |
| 26 | academic.oup.com | 14 | 11 | Adversarial geopolitics; Condor; Oxford Academic |
| 27 | www.brookings.edu | 13 | 12 | Increase in surveillence; Tunisia; Brookings |
| 28 | www.researchgate.net | 13 | 10 | Self-efficacy: Toward a unifying theory of behavioral change; Guide PDF; Cultivating |
| 29 | www.energy.gov | 13 | 8 | Energy.gov; WAP; DOE |
| 30 | batesoninstitute.org | 12 | 6 | Nora Bateson; Nora Bateson; Bateson Institute |

## What this tells you

- Domains near the top, cited across *many distinct episodes* (not just many times within one dense episode), are the strongest bootstrap candidates — real, repeated editorial trust signal from Nate's own team.
- A domain with a high count concentrated in very few episodes is a different signal (one episode citing one source heavily) — worth looking at separately, not folded into the same ranking.
- The 'episodes citing it' column matters more than raw count for this specific purpose — it answers 'how many independent editorial judgments trusted this source', not just 'how many links exist'.