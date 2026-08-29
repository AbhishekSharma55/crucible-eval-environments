# Challenge facts — operational sheet

*Extracted from `context/overview.txt` and `context/micro1 - First Hackathon97ce7c5.pdf` (10 pages, titled "micro1 - Hackathon Uno"), plus verified research. Compiled 2026-08-29.*

## Deadline

| Event | UTC | IST |
|---|---|---|
| Kickoff | Aug 28, 15:00 | Aug 28, 20:30 |
| **Deadline** | **Aug 31, 18:00** | **Aug 31, 23:30** |

HackerEarth's page shows "3:00 PM – 6:00 PM UTC" — that is a rendering artifact of start and end times, not a daily window.

## The brief

Open-ended. **There is no starter repo, no prescribed runtime, no acceptance tests, and no assigned problem** — despite the overview page promising "starter materials, constraints and acceptance tests" at kickoff. You pick the problem.

> *"Pick a specific and meaningful problem you understand. Use agents to solve it and show through clear evidence that your solution improves the way the task is handled today."*

Four questions the PDF says to keep in mind: Who has this problem? What bottleneck makes it worth solving? Does the agent solve it well? Can another person reproduce the result?

Every entry must present **both a baseline solution and an advanced solution**, where the advanced one shows meaningful improvement in capability, reliability, efficiency, coverage or engineering quality — "not a cosmetic variation."

## Rubric — 100 points

| Criterion | Pts | Rubric text |
|---|---|---|
| Agent Solution & Engineering | **30** | "uses agents purposefully and is technically sound. Better context or tools may improve one project, while memory, verification, skills or orchestration may improve another." |
| End to End Quality | **20** | "a realistic and self contained execution... with the finish of something a person would sign their name to rather than an obvious AI generated draft." |
| Problem & User Value | **15** | "solves a meaningful problem for a clearly defined user" |
| Measured Improvement | **15** | "demonstrates gains over a fair baseline and uses the changelog to connect each iteration with evidence" |
| Reproducibility | **15** | "a clear path to run the solution and baseline and reach the main result" |
| Hot Take / Insights | **5** | "turns an observed failure mode into a practical lesson" |

**Tie-break order:** Agent Solution & Engineering → **Reproducibility** → Measured Improvement → End to End Quality → final panel review.

Note the asymmetry: **Problem & User Value and Hot Take are not tie-breakers at all**, while Reproducibility is #2 despite being only 15 points. With 7,500 registrants, ties at the top are near-certain, so Reproducibility is worth more than its face value.

**Qualification gate:** a submission is scored *only after* passing eligibility, completeness, integrity, **trace** and **reproducibility** checks. "A project that cannot be run or verified may be disqualified before rubric scoring." Traces are a hard gate, not a rubric line item.

## Evaluation guidance from the PDF

- Choose **one primary metric** that reflects what success means to the user.
- **Ten or more cases** is a good target. Same cases for baseline and final solution.
- Include **one challenging case** and explain what it revealed.
- Define what a good result looks like *before* running the evaluation.
- Metric table: primary outcome / human time per task / cost per task, each with baseline, agent solution, change.
- **"If the format above fits your task poorly, design your own clear scoring rubric and propose it, so the judges can use it to assess your workflow."**

## Four required deliverables

1. **Complete solution code + improvement changelog.** Everything required to run it, including the instructions that shape each agent. README introduces the intended user, their bottleneck, why solving it is valuable. Clearly labelled Improvement Changelog, one entry per meaningful iteration, connected to the evidence that guided the next decision — *including experiments later removed.* Close with the main failure mode and the hot take.
2. **Reproduction guide.** Written for a clean environment. Exact commands for solution, baseline, and evaluation. Which data is required, what output to expect, relevant versions, approximate runtime and cost.
3. **Solution video, ≤5 minutes.** Problem → simple baseline → one realistic execution start to finish → final comparison → changelog → the change that contributed most → one experiment removed.
4. **Agent trajectories** for **every agent used** — including the coding agent used to build the project. From agent instructions through to final result: what the agent did, how tools responded, the feedback that shaped the next step, retries, human checkpoints.

## Ground rules

1. Build with tools you already know.
2. **Make clear what existed before the competition and what you added.**
3. Use every tool per its licence and service terms.
4. **Keep consequential actions controlled through a sandbox or simulation. Add human approval before the action happens.**
5. **Make a qualified human reviewer part of any solution that could significantly affect someone.**
6. Legal and ethical use case, responsible with people and data.
7. Public or synthetic data preferred; approved anonymous data works.
8. **Keep credentials and private information outside the submission.**
9. **Connect every claim about your results to the evidence you submit.**
10. Give judges enough access to run the project and reproduce the main result.

## Rules and eligibility

- Individual only. One registration, one final entry. Revisions allowed until the deadline; **only the latest complete submission is evaluated.**
- 18+. Open globally except where prohibited.
- Coding-agent use is **required**; tools must be disclosed and trajectories submitted.
- No API keys or model credits provided — bring your own setup.
- Any language allowed; Python, TypeScript, Java, C++, Go, Rust recommended.
- **Submissions are governed by the Hackathon Participation Agreement, under which micro1 owns submissions and may use them for AI model training and evaluation.**

## Prizes

- $10,000 cash across three selective awards (an earlier announcement said $5,000 total; the current page says $10,000 — likely $5k/$3k/$2k after a post-launch increase, unconfirmed).
- Up to 50 paid opportunities at micro1.
- Digital participation certificate for every eligible valid submission.
- **Separate, non-guaranteed:** micro1 may offer to acquire qualifying agent-use traces at **$2–$15 per trace, capped $100–$200 per participant.** Not part of the prize pool, does not affect judging.

## Submission mechanics — HackerEarth

The "Start submission" form has up to 11 fields: project title, idea selection, description, "Built with" (**disclose coding agents here**), images (**JPG/PNG only, max 3MB**), video link, presentation upload, demo link, repository link, source code upload (**private by default — visible only to you and judges**), instructions.

**Traps:**
- **Video must be a YouTube / Vimeo / Youku link.** No MP4 upload. Unlisted is fine.
- **Publishing is one-way** — "after you publish your project, you cannot make any new changes to it." But multiple submissions are allowed and only the final one is judged. **Publish a complete working submission around T-8h as insurance, then supersede it.** Do not sit on a single unpublished draft at 17:59 UTC.
- All external links must be **publicly accessible**. Verify in an incognito window. A private repo or a restricted Drive link is the classic completeness-gate disqualifier.
- Trajectory logs won't fit the form — put them in the repo and link.

**Worth confirming with yeison@micro1.ai:** that "latest submission is judged" is actually configured on this event. micro1's rules say yes; HackerEarth's default publish behaviour is one-way.

## Contacts and channels

- Test administrator: **Yeison Cruz, yeison@micro1.ai** (no public technical footprint found — likely program ops, not the scorer)
- micro1 Discord: https://discord.com/invite/J3TuHtS9v9 (~5,784 members, not hackathon-specific, but the only real-time channel)
- Official subreddit: **r/micro1_ai**
- Challenge page: https://www.hackerearth.com/challenges/hackathon/micro1-frontier-engineering-challenge-2026/

## The PDF's three appendix examples — collision warning

The PDF's appendix walks through three worked examples. Expect a large fraction of 7,500 entrants to build these verbatim:

1. **Code analysis: is this repository actually good?** — buyer assessing a private repo before purchase. Validation method prescribed: have qualified reviewers rank ten codebases with a shared rubric, give the same to the agent and a baseline, compare orderings.
2. **Candidate evaluation: should we hire this person?** — reconciling JD, target profile, CV, interview records, assessments; surfacing contradictions and possible cheating. *(Note: this is micro1's own product, Zara. Your version gets compared to a production system.)*
3. **Podcast translation: can every version still feel like the same show?** — long-horizon consistency of speaker identity, pronunciation, recurring terms, tone across episodes and languages.

The underlying *shapes* are what the organizers find interesting: rank against a shared rubric with expert ground truth; reconcile contradictory evidence with uncertainty surfaced; maintain long-horizon consistency. **Keep the shape, change the substrate.**
