# Research index

Three parallel research passes run 2026-08-29 for the micro1 Frontier Engineering Challenge (Agentic Workflows Hackathon), Aug 28–31 2026. ~60 primary sources per pass, web-verified at that date.

| File | Covers |
|---|---|
| [01-micro1-intel.md](01-micro1-intel.md) | Who micro1 is, who judges, why they're running this, their published benchmark methodology, community chatter (there is none), HackerEarth submission mechanics |
| [02-winning-patterns.md](02-winning-patterns.md) | Judge psychology, what the modal submission out of 7,500 looks like, problem-selection filters, presentation craft, the video shot list, anti-slop tells, 72-hour allocation |
| [03-technical-playbook.md](03-technical-playbook.md) | Verification research, eval harness design, judge validation, small-N statistics, context engineering, single-vs-multi-agent evidence, reproducibility patterns, trajectory capture, prioritized shortlist with hour estimates |

Decision and plan: [`../STRATEGY.md`](../STRATEGY.md)
Deadlines, rubric, deliverables, submission traps: [`../CHALLENGE-FACTS.md`](../CHALLENGE-FACTS.md)

## The three findings that drove the decision

**1. micro1 sells exactly what this hackathon asks you to produce.** Their contractor listings pay $50–100/hour to "create reproducible RL environments that test a model's ability to solve these workflows along with a golden reference solution." The hackathon deliverable — solution, fair baseline, shared eval cases, clean-environment reproduction guide — *is* an RL environment with a verifier. They are acquiring at ~$1.30/registrant what they otherwise pay hourly for. Build accordingly.

**2. Sixty of the hundred points, and all three tie-breaks in order, are eval and engineering rigor.** Agent Engineering (30) + Measured Improvement (15) + Reproducibility (15). Only 20 points are "does it look good." And Reproducibility is both the #2 tie-break and a disqualification gate — the only category where you can lose everything.

**3. Intrinsic self-correction does not work, and saying so with your own numbers is the Hot Take.** Huang et al. (ICLR 2024): the same reflection loop gains +8.4 points with an external correctness signal and loses up to 37.7 without one. Most published positive results leaked oracle labels or benchmarked against a deliberately weak first attempt. The dominant hackathon reflex — "add a critic agent" — is measurably harmful. Running that ablation yourself yields a changelog entry, a removed experiment, and the insight, from one experiment.

## Caveats

- Reports were produced by web-research agents. Facts carry URLs; inferences are labelled as such in each file. Spot-check anything load-bearing before putting it in the README.
- Two independent passes corroborated the micro1 product/benchmark findings (Realm, RedlineBench, the container + golden-reference + weighted-rubric + judge-panel methodology). Treat those as solid.
- The prize breakdown ($5k/$3k/$2k vs "$10,000 across three awards") is unresolved. It lives in an image on the Prizes tab.
- One source in pass 2 (the "41 of 49 projects were LangChain RAG" claim) could not be fetched directly and came via a search index. Treat as illustrative, not citable.
