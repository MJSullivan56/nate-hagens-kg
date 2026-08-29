# Citation frequency audit — show-notes links across the corpus

Analyzed 301 scrape metadata files, 18781 total links, 4824 distinct domains. Pure local URL aggregation — no API calls, no cost.

## Self-referential domains (internal to this project's own ecosystem)

Not useful as a 'monitor for new content' list — these are the show's
own site, YouTube back-links, Wikipedia, podcast platforms.

| domain | count | episodes citing it |
|---|---|---|
| en.wikipedia.org | 2191 | 267 |
| www.thegreatsimplification.com | 764 | 205 |
| www.youtube.com | 329 | 162 |
| youtu.be | 311 | 150 |
| youtube.com | 34 | 29 |
| podcasts.apple.com | 4 | 4 |
| thegreatsimplification.com | 3 | 3 |

## Top 30 third-party domains — the real bootstrap source list

| rank | domain | count | episodes citing it | sample link labels seen |
|---|---|---|---|---|
| 1 | www.britannica.com | 439 | 162 | What is shale oil?; Sensationalism; Walter Cronkite |
| 2 | read.realityblind.world | 423 | 160 | Everything requires an energy conversion; We use energy as principal, but treat it like interest; We use 100 billion barrel of oil equivalents of fossil hydrocarbons per year, globally |
| 3 | www.sciencedirect.com | 393 | 176 | A barrel of oil is worth ~5 years of human labor; One barrel of oil does 5 years of human labor; There’s nothing left after shale oil |
| 4 | www.nature.com | 222 | 114 | We don’t include resource creation or pollution streams in our prices; The Amazon is becoming a carbon source; The Amazon forest is a net source of carbon emissions |
| 5 | pmc.ncbi.nlm.nih.gov | 184 | 63 | Total species on Earth; Evolution’s impact on human brains; Social reciprocity in the animal kingdom |
| 6 | ourworldindata.org | 175 | 94 | 2 million known species, 10 million estimated total species; 80% of our economies energy inputs are fossil-fuel based; Our world is ~85% run on hydrocarbons |
| 7 | www.reuters.com | 165 | 81 | Putin’s speech 06/17/22; Germany upping coal imports and moving to wood; Insect populations declining 1-2% per year |
| 8 | www.theguardian.com | 165 | 113 | Germany’s energy transition plan and its reliance on natural gas; EU Vote to remove subsidies on pellets made of trees cut down specifically for that purpose; Humans are 36% of global biomass, and livestock is another 60% |
| 9 | www.ncbi.nlm.nih.gov | 163 | 85 | Klieber’s law; Major causes of insect decline; Issues with information availability |
| 10 | www.eia.gov | 149 | 56 | Half (65%*) of US crude oil production is light, tight shale oil; The U.S. produces 11-12 million barrels oil/day; uses 20 million barrels of oil/day |
| 11 | www.iea.org | 138 | 75 | Net Zero; Net Zero; reliance on cheap oil |
| 12 | link.springer.com | 107 | 78 | Global conventional oil extraction has plateaued the last 15 years; Poleward movement of fish; Multilevel selection |
| 13 | www.investopedia.com | 102 | 44 | consumption increases with income; Hunt brothers cornering the silver market; 1987 stock market crash |
| 14 | www.pnas.org | 100 | 62 | We are drawing down energy 10 million times faster than it was created; We are losing insect biomass at 1-2%/year, faster than other organisms; Sublinear scaling of energy for economies |
| 15 | www.bbc.com | 87 | 77 | UK power station owner cuts down primary forests in Canada; The benefits of a rituals and community; Circular economy in Edo Japan |
| 16 | www.science.org | 86 | 50 | Humans have long encroached on wild nature; We are on the verge of a 6th mass extinction; A 485-million-year history of Earth’s surface temperature |
| 17 | www.pewresearch.org | 79 | 54 | How much of a risk do people think climate is around the world?; Pessimistic views of the future; US beliefs on climate change |
| 18 | plato.stanford.edu | 77 | 42 | Game theory; Game Theory; Game Theory |
| 19 | www.npr.org | 75 | 60 | Foreign Students Studying in the U.S. Fear Deportation; July 4, 2025 Texas Flood; big oil’s role in blocking regulations |
| 20 | www.researchgate.net | 73 | 55 | Mental Health by Political Ideology and Sex; Charles Goodnight; 20th century copper ore concentration |
| 21 | www.energy.gov | 72 | 45 | 40% of a barrel of oil is gasoline, the other 60% creates thousands of other products; All the products that come from a barrel of oil; lifetime of solar panels |
| 22 | pubmed.ncbi.nlm.nih.gov | 68 | 43 | There are 1.5 million known species of insects; Risk homeostasis; Risk homeostasis |
| 23 | www.jstor.org | 67 | 46 | Herman Daly Steady State; Reconnecting water flows; Nurses Over-Prescribing Study |
| 24 | www.amazon.com | 66 | 44 | Collapse of Complex Societies; The Uninhabitable Earth; works |
| 25 | www.psychologytoday.com | 66 | 40 | instant gratification seeking psychology; Motivated Reasoning; Signaling |
| 26 | www.nytimes.com | 65 | 54 | Oil priced at negative dollars/barrel (2020); Doomerism; AI energy demands |
| 27 | www.frontiersin.org | 64 | 51 | We take 40% NPP for human systems; Human appropriation of NPP; Jeremy DeSilva, et al. – Human brains have shrunk: the questions are when and why |
| 28 | www.linkedin.com | 62 | 43 | Atossa Soltani; Sian Sutherland; Taylor Guthrie |
| 29 | www.epa.gov | 61 | 39 | Effects on Food Supply; US greenhouse gas emissions data; U.S. Environmental Protection Agency |
| 30 | www.weforum.org | 60 | 50 | World Economic Forum; regions will become inhabitable as warming increases; World Economic Forum |

## What this tells you

- Domains near the top, cited across *many distinct episodes* (not just many times within one dense episode), are the strongest bootstrap candidates — real, repeated editorial trust signal from Nate's own team.
- A domain with a high count concentrated in very few episodes is a different signal (one episode citing one source heavily) — worth looking at separately, not folded into the same ranking.
- The 'episodes citing it' column matters more than raw count for this specific purpose — it answers 'how many independent editorial judgments trusted this source', not just 'how many links exist'.