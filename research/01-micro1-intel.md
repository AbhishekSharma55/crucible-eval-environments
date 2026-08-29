# micro1 Competitive Intelligence

*Research completed 2026-08-29. Sources verified at that date; re-check anything time-sensitive.*

**Bottom line:** micro1's paid contractor job specs describe, almost word for word, the artifact this hackathon asks you to produce: *"reproducible RL environments that test a model's ability to solve these workflows along with a golden reference solution."* The hackathon is a talent-and-data funnel for that exact deliverable. The winning move is to submit something that reads like a micro1 internal deliverable — a containerized, deterministic eval harness with a golden reference, a weighted rubric, an LLM-judge panel, ≥10 cases, and a failure taxonomy — not "a cool agent app."

---

## 1. The company

### Identity & scale
- Tagline: *"Data lab to train frontier models & evaluate agents."* Careers page: *"a research lab building the data infrastructure behind frontier AI."* (https://www.micro1.ai/, https://www.micro1.ai/careers)
- Founded 2022 by **Ali Ansari** (CEO), UC Berkeley CS then Stanford, focus on reinforcement learning. Now 25. (https://www.micro1.ai/ali-ansari)
- Funding: ~$6.6M seed (Aug 2023–Aug 2024) → **$35M Series A led by 01 Advisors** (Dick Costolo + Adam Bain, ex-Twitter) at **$500M valuation**, Sept 2025. Microsoft also an investor. Series B in preparation as of Feb 2026. (https://techcrunch.com/2025/09/12/micro1-a-competitor-to-scale-ai-raises-funds-at-500m-valuation/, https://sacra.com/c/micro1/)
- Revenue: $7M ARR start of 2025 → $50M mid-2025 → ~$190M (Feb 2026) → **$500M gross annualized run rate** (2026). Headcount varies wildly by source (326 core / 3,843 / 7,751) because most of the "workforce" is a contractor expert network — reportedly ~2M experts signed up. (https://www.forbes.com/sites/rayravaglia/2026/02/03/micro1-shows-why-ais-hardest-problem-is-evaluation-not-intelligence/)
- Competitors: Scale AI, Mercor, Surge AI.

### Products (three named lines)
1. **Realm** — *"RL environments that mirror real-world scenarios to generate world-class human data for agentic actions."* Also the brand for their public benchmarks.
2. **Cortex** — *"the visibility and improvement layer for agentic AI."* Four pillars: evaluation design, failure diagnosis, expert training data targeting the highest-priority failure modes, performance monitoring. (https://www.micro1.ai/data-engine/agentic-ai)
3. **Robotics** — egocentric human-demonstration / teleoperation data for humanoids (VP Robotics Data: Arian Sadeghi).

### Zara, the "AI recruiter"
LLM-based AI interviewer + candidate feedback system. GPT-4o + RAG; role-specific mock interview, then a 20–40 min AI-led interview with *"adaptive branching"* (follow-ups generated on the fly), then autonomous structured post-interview evaluation restricted to hard skills only. Published as *Zara: An LLM-based Candidate Interview Feedback System* (arXiv 2507.02869, April 2025). **Zara is how micro1 vets its expert network at scale — top-of-funnel for the whole business, not a side product.** (https://www.micro1.ai/research/zara-an-llm-based-candidate-interview-feedback-system)

---

## 2. Their benchmark house style — imitate this

Verbatim patterns from Realm Legal (https://www.micro1.ai/benchmark/realm-legal) and Crosby–micro1 RedlineBench (https://www.micro1.ai/benchmark/crosby-micro1-redlinebench):

- Model dropped into a **sandboxed container with a read-only file system** of source materials plus **a minimal set of tools** (shell, file-read, file-edit, image viewer, web search).
- An **expert authors a "golden response."** The rubric is *"designed to correspond to the attorney-authored golden response… translating that response into evaluation criteria for model outputs."*
- **35–60 weighted rubric criteria per task**, decomposed along a named framework (IRAC for legal: issue 4% / rule 33% / application 48% / conclusion 9% / other 6%; five weighted dimensions for RedlineBench).
- **LLM judge panels** (three judges, majority vote) check each criterion. Explicit scoring formula: `clamp((earned − penalty) / total_positive)`, reward in [0,1], averaged across rollouts and cells.
- Results reported with **confidence intervals and model-vs-model separation**, plus a **failure taxonomy with quantified penalties** — e.g. *"IRAC chain breaks after issue spotting"*; *"skipping images → hallucinated details, ≈−0.28 to −0.35"*; *"over-acceptance bias: models pass 80–99% of 'accept' rubrics but only 6–50% of 'reject' rubrics."*
- Behavioral metrics computed **without** LLM judges where possible (direct .docx diff analysis).

### Their research thesis (https://www.micro1.ai/research)
- *No Last Mile: A Theory of the Human Data Market* (arXiv 2603.00932) — structured human data (evaluation, rubric-based judgment, auditing, exception handling) is a **permanent** production input, not transitional.
- *The Benchmark Ceiling* (July 2026) — valid signal concentrates in **hard-tail items**; replacement cost rises convexly with frontier capability.
- Blog, *Most Agentic AI Never Makes It Past the Demo*: *"APIs time out. Schemas change without notice. Inputs arrive malformed, incomplete, or adversarially crafted… Responsible deployment of agentic AI is not primarily a model problem or even a data problem. It is an infrastructure and design problem."*
- Ansari in Forbes: *"It's not like typical software where you can kind of say yes or no to whether it works."* On why AI can't self-evaluate — if a model can reliably judge domain performance you've nearly solved the task, so *"high-confidence evaluation still requires human judgment as the grounding layer."*

---

## 3. Why they're running this — follow the money

### Verified facts
- Contractor listing **"Open Source Contributor"**: *"you will be creating Reinforcement Learning Environments which test an AI model's ability to solve complex software engineering problems related to fixing code, creating features, refactoring code and optimizing performance."* Pay **$50–$100/hour**, output-based per approved task, minimum weekly quota, roles filled in 48h. (https://www.remotech.ai/jobs/open-source-contributor)
- **"Senior Software Engineer"** listing: *"Your task will be to create reproducible RL environments that test a model's ability to solve these workflows along with a golden reference solution. These workflows are similar in scope to common DevOps | CI/CD | Debugging workflows using common CLI tools such as git, docker, gdb, asan, ffmpeg and many more."* (https://jobs.micro1.ai/post/90f5054a-e91e-403d-8733-c350ab619e44)
- The hackathon overview links to exactly these roles as the "paid opportunities."
- Participation Agreement: **micro1 owns submissions and may use them for AI model training and evaluation.**
- Separate offer: **$2–$15 per qualifying agent-use trace, capped $100–$200 per participant.**
- Qualification gate: scored *only after* passing *"eligibility, completeness, integrity, **trace** and **reproducibility** checks."* Traces are a hard gate, not a rubric line.
- 7,500 registrants; $10,000 total prize pool.

### Inference (high confidence)
At roughly **$1.30 per registrant in prize money**, micro1 is buying four things it otherwise pays $50–100/hr for:

1. **Reusable SWE RL environments + golden reference solutions.** Literally their #1 contractor deliverable. "Solution + baseline + same eval cases + clean-environment reproduction guide" *is* an RL environment with a verifier.
2. **Labeled agent trajectories with process supervision.** The spec asks for *"what the agent did and how its tools responded… the feedback that shaped its next step, plus any retries or human checkpoints."* That is the (state, action, observation, correction, outcome) tuple structure needed for process reward models — the scarcest and most expensive class of human data.
3. **The Improvement Changelog = an ablation dataset.** "What you tried and why / evidence / kept-revised-removed," *including experiments you removed*, is a set of (intervention → measured delta → human decision) triples. Negative results are near-impossible to buy at scale. **This is the most unusual ask in the whole rubric, and it is unusual precisely because it is what they want.**
4. **A pre-vetted hiring funnel** that skips Zara's top-of-funnel entirely — 7,500 self-selected engineers, ranked, with verified work product.

### What submission type is most valuable to them (→ what judges reward)
**An agent that performs evaluation/judgment on a domain, packaged as a reproducible environment with a golden reference and a rubric, validated against human expert ground truth.**

Evidence:
- Two of the three appendix examples are exactly this: *"Code analysis: is this repository actually good?"* and *"Candidate evaluation: should we hire this person?"* (the latter is micro1's own core business).
- Appendix example 1 prescribes their house validation method verbatim: *"have qualified reviewers rank ten approved codebases with a shared rubric, then give the same codebases and rubric to the agent and to a simple baseline. Does the agent come closer to the reviewers' order, and can it explain each position with evidence?"* → **rank correlation against expert ordering.** That is Realm/RedlineBench methodology compressed into one sentence.

**Lower-value / lower-scoring:** a slick SaaS demo, a chatbot wrapper, anything whose "evaluation" is a vibes-based screenshot, anything that can't be re-run.

---

## 4. The judges

### Verified
- Named contact: **Yeison Cruz, yeison@micro1.ai**, listed as *"test administrator."* **No LinkedIn, X, GitHub, or public technical footprint found.** Treat as program/talent-ops, not the technical scorer. *(Stated non-finding, not speculation.)*
- Overview states scoring is by **"micro1's engineering team,"** with a **"Final panel review of documented evidence"** as the last tie-break. No judge roster published.

### The engineering/research bench
- **Andrew Maas — VP of AI Engineering** (https://ai.stanford.edu/~amaas/, https://www.linkedin.com/in/andrewleemaas). **The most important person to write for.** CMU CS+CogSci → **Stanford CS PhD 2015 under Andrew Ng and Dan Jurafsky**. ~26,200 citations, h-index 22; author of the **Large Movie Review (IMDB) Dataset**, still a standard benchmark. Taught CS224S at Stanford. Apple Special Projects Group (data-centric deep learning for robotics, 2019–2023) → founded **Pointable** (enterprise retrieval, acquired by Apple) → Apple Director of Engineering → micro1. Self-describes his remit as *"data-centric ML systems that produce training data, evaluations, and expert feedback for frontier AI labs."* Was **Ali Ansari's master's advisor at Stanford**; joined as employee ~#80. **Resonates with: dataset construction rigor, benchmark validity, honest error analysis, measurement over demo.** He built his career on a dataset.
- **Imran Nasim, PhD — VP of Research** (appointed June 2026). PhD theoretical astrophysics, Surrey; postdoc Harvard/Dana-Farber + Broad Institute; formerly AI Engineer at IBM UK. Talks: *"What It Takes to Ship Agentic AI Into Production"*, *"Building Trustworthy AI Agents: The Role of Contextual Evaluations."* His line: contextual evaluations grounded in the customer's actual workflow beat generic benchmarks.
- **Ali Ansari — Founder/CEO.** RL background. Position: evaluation, not intelligence, is the hard problem; human judgment is the grounding layer.
- Others: **Liu Zhang** (MTS; spoke on red-teaming agentic systems), **Mark Esposito** (Chief Economist, Harvard Berkman Klein), **Arian Sadeghi** (VP Robotics Data), domain research directors (Ryan Charnov – finance, Isabel Yishu Yang – legal, Paola Rodríguez – medical).
- GitHub org `micro1-io` exists but has **no public repos or members**.

### Inference: the scoring loop
Triage pass by ops/junior engineers against the 100-point rubric, then a small senior panel (Maas / Nasim tier) reviewing only the shortlist for the three awards and the top-50 list. **Design for both:** survive automated/skim triage (clean README, one-command repro, results table above the fold, trajectories obviously present) *and* reward the senior read (rigorous eval design, honest negative results, quantified failure taxonomy).

---

## 5. Prior editions & community chatter

**This is the first edition.** LinkedIn: *"micro1 is hosting its first global hackathon with HackerEarth."* PDF titled "First Hackathon." No winner archive, no gallery, no precedent to reverse-engineer.

**Community chatter is essentially nonexistent — a real finding, not a search failure.** Searched Reddit, X, LinkedIn, Discord, YouTube, dev.to, Medium, hackathon aggregators.

| Source | Content |
|---|---|
| https://dev.to/marvinoka4/5900-engineers-just-registered-for-a-hackathon-where-using-ai-is-the-point-heres-how-it-will-1bdd | The **only** substantive third-party writeup, at the 5,900-registration mark. Generic strategy advice. Reads as AI-assisted commentary, **not** insider info. **No official clarifications.** Prize figures stale. |
| Reddit | Official subreddit is **r/micro1_ai** (not r/micro1). Zero indexed hackathon threads. |
| Discord | **https://discord.com/invite/J3TuHtS9v9** — "micro1 Community," ~5,784 members. Not hackathon-specific but the only real-time channel. **Worth joining for clarifications.** |
| X | @micro1_ai and @aliansarinik — nothing beyond the announcement. |
| Official | LinkedIn, Instagram, X, YouTube (@micro1_ai), r/micro1_ai. https://www.micro1.ai/community |

**Consequence: there is no crowd to benchmark against and no leaked interpretation of the rules.** Official clarifications go only to registered participants via HackerEarth Help.

### Data discrepancies
- **Prizes:** earlier LinkedIn said **$5,000 total / $3,000 to winner**; another source says **$5k / $3k / $2k**; current official page and hacklist.io say **"$10,000 cash across 3 selective awards."** Best read: pool **doubled after launch** to $5k/$3k/$2k. Not fully confirmed — breakdown lives in an image on the Prizes tab.
- **Registrations:** 5,900 (early) → **7.5K** (current).
- HackerEarth displays "3:00 PM – 6:00 PM UTC" — a rendering artifact of start (Aug 28 15:00 UTC) and end (**Aug 31 18:00 UTC**), not a daily window.

---

## 6. HackerEarth submission mechanics — there are traps here

From https://help.hackerearth.com/submitting-a-prototype. **"Start submission" opens a prototype form with up to 11 fields:**

1. Project title
2. Idea selection (dropdown, if the event has an idea round)
3. Project description
4. "Built with" (tech/tools list — **likely where you disclose coding agents**)
5. Images — **JPG/PNG only, max 3MB each**, recommended 630×320 or 16:9
6. Video link — **YouTube, Vimeo, or Youku only. No direct file upload.**
7. Presentation (file upload)
8. Demo link
9. Repository link
10. Source code (file upload; **default visibility is private — visible only to you and judges** — with a toggle to make it public)
11. Instructions (setup/usage)

### Critical mechanics
- **"Once you publish your submission, you cannot delete it"** and **"after you publish your project, you cannot make any new changes to it."**
- But **multiple submissions are allowed**: *"You may submit your project as many times as you like. Only the final submission will be judged."* Reconciles with micro1's *"Revisions are allowed until the deadline; only the latest complete submission is evaluated."*
- **Save as draft** before publishing; drafts are editable from the dashboard.
- All external links (repo, video, cloud storage) must be **publicly accessible** — a private GitHub repo or a "restricted" Drive link is the classic disqualifier at the completeness/integrity gate.

### Actionable
- Video **must be YouTube/Vimeo** (unlisted fine). Do not plan on uploading an MP4.
- Trajectory logs won't fit the form. Put them in the repo (`trajectories/`) and link. **Verify anonymous access in an incognito window.**
- **Publish a complete working submission early (~T-8h) as insurance**, then publish an improved one. You cannot edit, but you can supersede. Do not leave a single unpublished draft at 17:59 UTC.
- **Highest-value clarification question to ask yeison@micro1.ai:** confirm "latest submission is judged" is configured on this event — micro1's rules say yes, HackerEarth's default publish behavior is one-way.

---

## 7. Playbook

**Scoring:** Agent Solution & Engineering **30** · End-to-End Quality **20** · Problem & User Value **15** · Measured Improvement **15** · Reproducibility **15** · Hot Take **5**.

**Tie-break order:** Agent Solution & Engineering → **Reproducibility** → Measured Improvement → End-to-End Quality. **Problem & User Value and Hot Take are not tie-breakers at all**, while Reproducibility is the #2 tie-break despite being only 15 points. With 7,500 registrants, ties at the top are certain. **Reproducibility is worth far more than its 15 points.**

1. **Pick an evaluation/judgment problem, not a build problem.** Bonus if in a domain they sell into: code review, hiring, finance, legal, medical, DevOps/CI-CD debugging.
2. **Structure the deliverable as a micro1 benchmark.** Containerized (Docker, pinned digests, seeded, offline-capable) + minimal explicit tool surface + **expert-authored golden reference** + weighted rubric with published percentages + LLM-judge panel with majority voting + reward in [0,1] + non-LLM behavioral metrics where computable. Use their vocabulary: *golden reference, rubric weight, judge panel, reward, rollout, failure mode.*
3. **≥10 cases, identical for baseline and agent, plus one explicitly hard-tail case** — and report what the hard case revealed. *The Benchmark Ceiling* says all discriminating signal lives there; the judges wrote that paper.
4. **Report like a paper, not a pitch.** Full results table, multiple rollouts, variance/CIs, per-criterion breakdown, **quantified failure taxonomy** ("skipping X costs −0.28"). Include human time and cost per task rows.
5. **Make the Improvement Changelog the centerpiece.** Include ≥2 experiments you *removed*, with the evidence that killed them.
6. **Trajectories are a hard gate, not a bonus.** Agent instructions → tool call → tool response → error → retry → human checkpoint → outcome, per agent, checked into the repo. Also eligible for $2–15/trace. Format them cleanly and you get paid twice.
7. **Address reward hacking explicitly.** A short "how this environment resists gaming" section (isolated verifier, no network at eval time, tests outside the agent-writable tree) will read as senior to Maas/Nasim and to no one else in the field.
8. **Anti-slop.** Hand-write the README and video script. Cut em-dashes, "delve," bullet-soup, triumphant summaries.
9. **Hot Take:** one observed failure mode → a falsifiable claim about building reliable agents, grounded in your own logged data.
10. **Sandbox + human approval** for consequential actions — Ground Rules 04/05 and part of the integrity gate.

---

## Sources
[micro1](https://www.micro1.ai/) · [research](https://www.micro1.ai/research) · [Realm Legal](https://www.micro1.ai/benchmark/realm-legal) · [RedlineBench](https://www.micro1.ai/benchmark/crosby-micro1-redlinebench) · [Cortex/agentic-ai](https://www.micro1.ai/data-engine/agentic-ai) · [expert library](https://library.micro1.ai/llms.txt) · [Open Source Contributor role](https://www.remotech.ai/jobs/open-source-contributor) · [Senior SWE role](https://jobs.micro1.ai/post/90f5054a-e91e-403d-8733-c350ab619e44) · [Ali Ansari](https://www.micro1.ai/ali-ansari) · [Andrew Maas](https://ai.stanford.edu/~amaas/) · [Imran Nasim appointment](https://blogs.surrey.ac.uk/mathsresearch/2026/06/09/imran-nasim-appoint-vice-president-for-research-at-micro1/) · [Forbes](https://www.forbes.com/sites/rayravaglia/2026/02/03/micro1-shows-why-ais-hardest-problem-is-evaluation-not-intelligence/) · [TechCrunch Series A](https://techcrunch.com/2025/09/12/micro1-a-competitor-to-scale-ai-raises-funds-at-500m-valuation/) · [No Last Mile](https://arxiv.org/abs/2603.00932) · [challenge page](https://www.hackerearth.com/challenges/hackathon/micro1-frontier-engineering-challenge-2026/) · [HackerEarth submission help](https://help.hackerearth.com/submitting-a-prototype) · [dev.to writeup](https://dev.to/marvinoka4/5900-engineers-just-registered-for-a-hackathon-where-using-ai-is-the-point-heres-how-it-will-1bdd) · [micro1 Discord](https://discord.com/invite/J3TuHtS9v9)
