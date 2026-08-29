# How to Win: Judge Psychology, the Modal Submission, and Presentation Craft

*Research completed 2026-08-29.*

## 0. The single highest-leverage insight

micro1 is not a generic sponsor. It is an AI data lab whose product *is* evaluations and RL environments. Its research page lists Realm (legal/pathology/financial/tax reasoning), Crosby-micro1 RedlineBench (contract redlining), and LongExtractionBench (225 long documents) ([micro1.ai/research](https://www.micro1.ai/research)). Its internal tool "Merit" tracks *"velocity, error rates, cost per task, and quality in real time"* ([micro1.ai/data-engine](https://www.micro1.ai/data-engine)) — **almost verbatim the metric table the PDF asks you to fill in** (primary outcome / human time per task / cost per task).

**Inference (high confidence):** You are being graded by eval engineers who buy trajectories and build benchmark environments for a living. The serial-winner framing — "If I reward this project, will my company look good?" ([sustained.substack.com](https://sustained.substack.com/p/lessons-from-winning-five-hackathons)) — translates here to: *does this submission look like a benchmark/RL environment micro1 would ship to a frontier lab?* A submission that ships a **reusable, verifiable eval environment plus clean labeled trajectories** is not just scoring points; it is producing the artifact they monetize.

**Corollary:** 30 (Agent Engineering) + 15 (Measured Improvement) + 15 (Reproducibility) = **60 points, and tie-breaks 1, 2, 3 in that exact order, are all eval and engineering rigor.** Only 20 points are "does it look good." Build for the eval-engineer reader, not the product-demo reader.

---

## 1. The qualification gate: where most of the 7,500 die

Large hackathons increasingly pre-screen with agents. Devfolio built an "evidence layer" that clones repos, walks code, and generates cited reports flagging claim–evidence mismatches — e.g. *"the submission claims 'multi-tenant isolation with row-level security,' but `db/policies.sql` only checks that a user is authenticated"* ([devfolio.co](https://devfolio.co/blog/the-discerning-machine/)). Humans then get the audit with citations.

**Inference (high confidence):** With ~7,500 registrations and a gate that explicitly checks "completeness, integrity, trace and reproducibility," micro1 will run automated repo/trace/README auditing first. **Assume a machine reads your README line-by-line and tries to find the file backing every claim.**

### Gate checklist — binary pass/fail, before any feature code
- Repo public, clone-to-run tested in a **fresh container** (`docker run --rm` from scratch), not your laptop.
- Video public and playable without login. Colosseum lists *"forgetting to grant judges access to google docs, pitch videos, github repos"* as a top mistake ([blog.colosseum.com](https://blog.colosseum.com/perfecting-your-hackathon-submission/)).
- Trajectories present **for every agent**, not just the main one. Most-skipped deliverable and a named gate item.
- No credentials in repo; `.env.example` only.
- Every number in the README traceable to a committed artifact (`results/*.json`, `logs/`, test output).
- A `PROVENANCE.md` stating exactly what pre-existed the competition (Ground Rule 02). Reusing your own prior library is fine; not disclosing it is an integrity flag.

**Judge time benchmark:** MLH's organizer guide budgets ~9 minutes per team in preliminary judging ([guide.mlh.io](https://guide.mlh.io/general-information/judging-and-submissions/judging-plan)); other virtual-hackathon guidance is ~2 minutes per project. **Your README's first screen and your video's first 90 seconds are the entire first round.**

---

## 2. What the modal submission will look like

### Evidence
- A judge reported **41 of 49** projects at one event were LangChain + Pinecone RAG systems (Gaurab Baral, Nov 2025 — [medium.com/@gauurab](https://medium.com/@gauurab/why-current-ai-models-fail-at-evaluating-hackathons-and-what-we-actually-need-de28cb87b6e5); page 403s to fetchers, quote via search index).
- Across 8,200 ETHGlobal projects, "AI agents" went from ~1% of submissions to **over a fifth of everything submitted** ([simbro.medium.com](https://simbro.medium.com/what-8-200-hackathon-projects-reveal-about-what-actually-wins-f105346ec97c)).
- 2026 lablab.ai winners: HealthVet ("6 AI agents"), AgentWard ("5 specialized AI agents"), a receivables project with "a 9-agent team" ([lablab.ai](https://lablab.ai/apps/recent-winners)). Google's ADK hackathon (477 projects) winners were SalesShortcut, Energy Agent AI, Edu.AI, GreenOps, Nexora-AI — every one "multi-agent system for [vertical]" ([cloud.google.com](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights)).

### The predicted modal micro1 submission

> A LangGraph or CrewAI **supervisor + 4–6 named subagents** (Researcher / Analyst / Critic / Writer), pointed at one of the PDF's three appendix examples — most likely **code-repo quality assessment**. A Streamlit or Next.js dashboard. A README with emoji section headers, a "✨ Features" bullet list, a Mermaid architecture diagram, and a claims table showing "Baseline 45% → Ours 92%" on **5 hand-picked cases graded by an LLM judge with no rubric and no human validation**. Baseline = one zero-shot prompt, deliberately crippled. Changelog = 4 rows, all "kept," no removals, written after the fact. Video = 4:45 of talking head + slides, with the system running for 40 seconds. Trajectories = one screenshot of a terminal, or a LangSmith link that requires login.

### Oversubscribed ideas judges will see hundreds of times
1. Repo quality / code-health assessor (Appendix example 1) — **largest cluster**
2. Resume ↔ JD candidate screener (Appendix example 2) — second largest; also what micro1 already sells (Zara), so your version gets compared to a production system
3. Podcast/video translation & dubbing consistency (Appendix example 3)
4. PR review agent / auto code reviewer
5. "Deep research" report writer with a critic agent
6. Meeting-notes → Jira/Linear ticket agent
7. Customer-support ticket triage/deflection
8. RAG over company docs / "chat with your PDFs"
9. Personal finance or invoice-processing agent
10. Travel planner / itinerary multi-agent
11. Medical symptom triage (also trips Ground Rule 05)
12. Legal contract redliner (micro1 literally has RedlineBench)
13. Test-generation agent for a repo
14. SQL/BI natural-language analyst
15. Supply-chain / logistics risk monitor
16. Devops/K8s cost or incident agent
17. Study-plan / tutor / quiz generator
18. Social-media or marketing content pipeline
19. Security vulnerability scanner agent
20. Email triage / inbox zero agent

### Is building an appendix example a trap?
**Inference (high confidence): yes as posed, but not as a domain.** The three examples are the highest-density collision zone. But they were written by the organizers, so the organizers find those *shapes* interesting. The shapes are:
- (a) rank/score artifacts against a shared rubric and beat human-reviewer ordering
- (b) reconcile contradictory evidence across sources with uncertainty surfaced
- (c) maintain long-horizon consistency across a series

**The winning move is to keep the shape, change the substrate.** Example: instead of "is this repo good," do "does this repo's dependency lockfile actually match what the build produces, and rank 12 real OSS repos by supply-chain drift risk against a rubric three human reviewers agreed on." Same evaluable structure, zero collisions, and it produces *verifiable* ground truth rather than a taste judgment.

### How to beat the modal submission

| Move | Why it beats the field |
|---|---|
| **Ground truth a machine can check, not an LLM's opinion** | "Verifiable beats judgeable" — deterministic state checks against ground truth are the standard in RL-environment design ([leehanchung.github.io](https://leehanchung.github.io/blogs/2026/03/21/rl-environments-for-llm-agents/), [unsloth.ai](https://unsloth.ai/blog/rl-environments)). Modal submissions use unvalidated LLM-as-judge. |
| **A baseline that is genuinely strong** | Give the baseline the *same* model, tools, and context budget. Report the number even if your lift shrinks to +18%. An honest +18% over a strong baseline outscores a fake +47% over a strawman, and it is the one thing an auditing agent can catch. |
| **A removed experiment with a real number** | The PDF explicitly asks for "one experiment you removed." The modal changelog has zero removals. |
| **Cost and latency per task, not just accuracy** | micro1's own Merit dashboard tracks cost per task. Trajectory/system metrics are where 2026 agent-eval practice lives ([deepeval.com](https://deepeval.com/blog/what-is-an-eval-harness)). |
| **Fewer agents, defended** | PDF: "Purposeful choices matter more than the number of components." Anthropic: *"find the simplest solution possible, and only increase complexity when needed."* A 2-agent system with an ablation proving agent #3 *hurt* beats a 6-agent swarm. |
| **Human-in-the-loop that actually gates** | Ground Rules 04/05 require it. Most entries will mention it; almost none will *show* the approval gate blocking an action in the trajectory. |

---

## 3. Problem selection: the five-filter test

1. **You can name the person.** Anthropic's winners quantify the bottleneck precisely: CrossBeam — *"California housing permits have a 90%+ rejection rate on first submission, six-month delays costing homeowners $30,000"*; TARA — *"Uganda road feasibility studies cost $1–4M and take 9–14 months"* ([claude.com](https://claude.com/blog/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon)). **Four of the five Opus 4.6 winners were not professional developers** — domain knowledge beat coding ability. If you cannot state the bottleneck as a number with a unit, pick something else.
2. **Ten-plus cases exist or can be built legally** from public/synthetic data, with **ground truth producible in under 4 hours.**
3. **A naive prompt gets it ~50–70% right.** Below that, too hard for 72 hours. Above that, no headroom to demonstrate improvement.
4. **The failure is specific and nameable** — "it silently drops the third constraint," not "it's inaccurate."
5. **You would use it Monday.** JetBrains' judges: build from *"a workflow you personally found annoying"*; one clear "oh, this is possible now" moment beats a feature tour ([blog.jetbrains.com](https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table/)).

Boring and narrow is a feature. Devpost judges list *"rehashed ideas, already-existing market solutions"* and *"recycled projects resubmitted to different hackathons"* as top point-losers ([info.devpost.com](https://info.devpost.com/blog/hackathon-judging-tips)).

---

## 4. Agent Solution & Engineering (30 pts, tie-break #1)

The rubric asks "Which design choices helped the agent solve the problem?" — it wants **attributable** design, not architecture diagrams.

- **One capability per changelog entry.** Context → tools → memory → verification → skills → orchestration. Add exactly one, re-run the full eval, record the delta. This turns your architecture into an **ablation table** — the single most persuasive artifact you can hand an eval engineer.
- **Verification as a first-class component.** Tool misuse is the most common agent-specific production failure — wrong arguments, wrong tool, or failing to handle a tool error and continuing as if it succeeded ([openlayer.com](https://www.openlayer.com/blog/ai-agent-failure-modes-tool-calling-loops-propagation)).
- **Cite MAST.** The Multi-Agent System Failure Taxonomy (14 modes; specification 41.8%, inter-agent misalignment 36.9%, task verification 21.3%; 1,600+ annotated traces, κ=0.88) is canonical ([arXiv:2503.13657](https://arxiv.org/abs/2503.13657)). Classifying *your* failures into a published taxonomy is an instant credibility signal.
- **Ship the agent instructions as files** — `agents/*.md`, prompts under version control, diffs visible in git history. The deliverable explicitly asks for "the instructions that shape each agent."
- **The Rippletide lesson:** the OpenAI Codex hackathon winner won on a "decision layer" — structured evaluation of outputs, not generation. *"Outputs are not outcomes... The hard part is not generating outputs. The hard part is turning them into outcomes"* ([rippletide.com](https://www.rippletide.com/resources/blog/winning-the-openai-codex-hackathon-moving-from-outputs-to-outcomes-the-decision-layer)).

---

## 5. Measured Improvement (15 pts)

- **≥10 cases** (PDF), include one adversarial case and *report that you failed it* if you did.
- **If you use LLM-as-judge, validate it.** Known biases: position, verbosity, self-preference ([openlayer.com](https://www.openlayer.com/blog/llm-as-judge-evaluation-guide), [deepeval.com](https://deepeval.com/blog/llm-as-a-judge)). Minimum viable defense: hand-label all cases yourself, report agreement (Cohen's κ or % agreement), randomize A/B order, decompose the rubric into discrete binary checks rather than a 1–10 vibe score. **A 100% pass rate is a bug, not a win.**
- **Report variance.** n=3 per case minimum, mean ± spread. Single-run numbers from a stochastic system are the tell of someone who has never shipped an eval.
- **Metric table exactly as the PDF specifies**, plus tokens and wall-clock. Match micro1's vocabulary: primary outcome, human time per task, cost per task.

---

## 6. Reproducibility (15 pts, tie-break #2) — the nondeterminism trap

Every competitor will claim reproducibility; almost none will handle that **LLM calls are nondeterministic**, so the judge's run won't match the reported numbers. Solving this visibly costs ~2 hours.

- **Record/replay the model calls.** VCR-style cassettes (`pytest-recording` / VCR.py) capture responses on a live run and replay after ([anaynayak.medium.com](https://anaynayak.medium.com/eliminating-flaky-tests-using-vcr-tests-for-llms-a3feabf90bc5)). Deterministic cache key: `SHA256(prompt || model || provider || temperature || max_tokens)` ([ai21.com](https://www.ai21.com/blog/caching-in-agentic-llm-pipelines/)).
- **Ship two paths:** `make repro-offline` (replays committed cassettes, no API key, exactly reproduces the reported table, minutes, $0) and `make repro-live`. **A judge with no API key can still reproduce your headline number — almost nobody will do this.**
- Pin exact **model IDs and dates**, not `latest`. Lockfile deps. `uv` or Docker with a digest-pinned base image.
- State **runtime and cost**: "full eval: ~14 min, ~$2.30, 412K tokens."
- Borrow the ACM artifact-badging frame ([acm.org](https://www.acm.org/publications/policies/artifact-review-and-badging-current)): Available / Functional / Reusable / Results Reproduced. A short "Artifact Appendix" addressed to a reviewer is a strong human-engineer signal.
- Verify by doing what the judge does: `git clone` into a clean container, run the README verbatim, and commit the terminal asciicast.

---

## 7. End to End Quality (20 pts) — the anti-slop criterion

The wording is unusual and deliberate: *"the finish of something a person would sign their name to rather than an obvious AI generated draft."* Treat it as a **negative** criterion — points are lost to tells, not gained by prose.

**Concrete tells** (from [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)): vocabulary clusters (*delve, robust, seamless, leverage, pivotal, crucial, underscore, showcase, testament, tapestry, meticulous, landscape, comprehensive*); avoidance of plain "is" (*serves as, stands as, represents*); negative parallelism (*not just X, but Y*); trailing present-participle clauses (*...further enhancing reliability*); the "Challenges and Future Prospects" closing formula; excessive boldface; emoji as section markers; title case in headings; inline-header vertical lists; leftover citation artifacts (`oai_citation`, `turn0search0`, `[cite: 1]`). Statistical tell: three or more consecutive sentences of 17–23 words, or >half of sentences opening with The/This/It/In ([theconversation.com](https://theconversation.com/can-you-teach-yourself-to-detect-ai-writing-maybe-289236)).

**Rules for your README/changelog:**
- Write the README's problem statement and the changelog's "decision/learning" cells **by hand**. Those are the two places a judge looks for a human.
- Include at least one thing an LLM would never write: a specific date, a dollar amount you paid, a named tool version that broke, an admission ("I spent 4 hours on a memory layer that made things worse; here's the number").
- Uneven sentence lengths. Concrete nouns. No "Features" list of adjectives. No emoji headers. No "🚀 Getting Started."
- Devpost judges penalize *"projects that lack detail and code"* behind *"polished appearances"* — polish without substance is worse than plain text with substance.
- Ship one artifact with visible craft: a real CLI with `--help`, a plain-HTML report the intended user would actually read, a well-designed results table. Commit history is part of the finish.

---

## 8. Agent trajectories — the most under-served deliverable

Requirement: *"representative trajectories for **every agent** you used, easy to follow from the agent instructions through to the final result... what the agent did and how its tools responded... the feedback that shaped its next step, plus any retries or human checkpoints."* **This includes the coding agent you used to build the project**, not only the agents inside it.

- `trajectories/` with one Markdown file per agent, each opening with the agent's system prompt, then numbered steps: input → tool call (args) → tool response (verbatim, truncated with an explicit marker) → agent's next decision → why.
- Include at least **one failing trajectory with a retry** and one **human checkpoint** where approval was requested and granted/denied. Cheapest way to score on Agent Engineering *and* Hot Take simultaneously.
- Emit structured JSONL alongside the Markdown, ideally under OpenTelemetry GenAI semantic conventions ([uptrace.dev](https://uptrace.dev/blog/opentelemetry-ai-systems)) — vendor-neutral, and directly useful to a company that buys traces.
- **Do not** link to a LangSmith/Langfuse dashboard as the only artifact; it may require login and can fail the trace check.

---

## 9. The 5-minute video: a shot list

Technical narration paces at ~100 words/minute; a 5-minute demo is ~500 words of script. Record screen first, then narrate against a locked edit; record in 30–90s chunks ([teleprompter.com](https://www.teleprompter.com/blog/how-to-time-your-script), [blog.kunchenguid.com](https://blog.kunchenguid.com/p/making-a-polished-tui-demo-video)).

Judges' rule of thumb: *"you have to be able to show something working within about 90 seconds"*; *"mock everything you can... remove every place the demo could stall"* ([blog.jetbrains.com](https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table/)).

| Time | Beat | Content |
|---|---|---|
| 0:00–0:35 | Problem + user | Name the person, the task, the number. Show the *actual current artifact* (the spreadsheet, the PDF, the manual checklist). No bullet slides. |
| 0:35–1:05 | Simple baseline, running | Show the one-prompt baseline execute on case #7 and produce a plausible-looking but wrong answer. Point at the specific wrong token. This is your "aha." |
| 1:05–2:35 | One realistic execution | Same case, your system. Uncut or lightly cut. Show a tool call, the verifier catching something, the human approval gate, the final artifact. |
| 2:35–3:20 | Final comparison | Metric table on screen. Say the baseline number out loud. Say yours. Say the sample size and the variance. |
| 3:20–4:10 | Changelog | Scroll the actual changelog file. 15 seconds per row max. |
| 4:10–4:40 | The change that mattered most | One ablation: "removing the verifier drops us from 84% to 61%." |
| 4:40–5:00 | The removed experiment + hot take | "I built a memory layer. It made case #3 worse because it carried a stale assumption forward. I deleted it. Lesson: ___." |

**Kill list:** talking head >20 seconds; a slide-based architecture diagram before anything runs; reading the README aloud; text too small at 720p; music; **any AI voiceover** (an obvious AI voice on a rubric that penalizes "obvious AI generated" work is an unforced error); anything requiring the judge to pause and read.

---

## 10. Repo layout that reads as "a human signed this"

```
README.md              # <=1 screen to first command. Problem, user, bottleneck, the number, the command.
CHANGELOG-IMPROVEMENT.md
REPRODUCE.md           # clean-environment guide, offline + live paths, runtime + cost
PROVENANCE.md          # what existed before Aug 28, what I wrote during
agents/                # system prompts as versioned files
src/
eval/
  cases/               # >=10, each with input + ground truth + why it's here
  rubric.md            # decomposed binary checks
  run_baseline.py
  run_solution.py
  judge_validation.md  # your labels vs judge labels, agreement stat
results/
  baseline.json  final.json  ablations.json  runs/   # raw, committed
trajectories/          # per-agent .md + .jsonl, incl. one failure + one human checkpoint
cassettes/             # recorded LLM responses for deterministic replay
Makefile               # setup | baseline | solution | eval | repro-offline | repro-live
```

**Changelog format** — extend the PDF's five columns with cost and n, which shows you thought past the template:

| Stage | What I tried & why | Evidence | Primary metric | Cost/task | Decision |
|---|---|---|---|---|---|
| Baseline | one prompt, same model | `results/baseline.json` | 0.46 ± 0.05 (n=10×3) | $0.01 | starting point |
| It1 | added file-read tool after seeing it invent function names | `results/runs/it1/` | 0.61 | $0.04 | kept |
| It2 | verifier re-checks each claim against source | `results/runs/it2/` | 0.79 | $0.09 | kept — largest single gain |
| It3 | added a memory layer across cases | `results/runs/it3/` | 0.74 | $0.11 | **removed** — carried stale assumptions between unrelated cases |
| Final | it1+it2, tightened rubric | `results/final.json` | 0.84 ± 0.03 | $0.09 | verification is the load-bearing component |

---

## 11. Hot Take (5 pts, disproportionate on perception)

Formula: **specific observed behavior → mechanism → generalizable rule → what I would build differently.** Anchor in your own trajectory logs, cite the MAST category, make it falsifiable.

Bad: "agents need better prompts."
Good: *"In 7 of 30 runs the agent received a tool error listing the valid arguments and re-issued the identical malformed call — it does not internalize schema feedback from error strings. Fix: make the tool return a repaired candidate call rather than an error message. That cut retry loops from 7/30 to 1/30."* (This exact pattern is documented in production logs — [openlayer.com](https://www.openlayer.com/blog/ai-agent-failure-modes-tool-calling-loops-propagation).)

---

## 12. 72-hour allocation

| Hours | Work |
|---|---|
| 0–4 | Pick problem. Write the eval spec and the 10+ cases **before** any system code. Hand-label ground truth. |
| 4–7 | Build and run the baseline. Commit the number. Do not tune the baseline down. |
| 7–10 | Repro skeleton: Makefile, Docker, cassette recording, results JSON schema. Doing this now means every later run is automatically evidence. |
| 10–34 | Iterations. One capability per iteration, full eval after each, changelog row written the same hour. Include one deliberate experiment you expect to fail. |
| 34–40 | Ablations for the final table. Adversarial case. Variance runs. |
| 40–48 | Trajectory export and cleanup: per-agent Markdown + JSONL, one failure, one human checkpoint. |
| 48–58 | README, changelog, REPRODUCE.md, PROVENANCE.md — hand-written. Clean-container repro test from the README verbatim. |
| 58–66 | Video: script (~520 words), record screen chunks, narrate, cut. |
| 66–72 | Buffer. Re-run gate checklist. Submit early; revisions allowed, but the gate punishes a broken last-minute push. |

---

## 13. Kill list

Do not: add a sixth agent to look sophisticated; build a web UI (a great CLI plus a clean HTML report beats a half-finished dashboard); use `latest` model aliases; report a single-run number; hand-pick eval cases after seeing results; use an LLM voice in the video; write the README with an agent and ship it unedited; claim anything the repo cannot prove; skip trajectories for the "minor" agents; leave the repo private until the last hour; or pick the repo-quality-assessor as posed in the appendix.

---

## Sources
[JetBrains judging notes](https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table/) · [Devpost judge advice](https://info.devpost.com/blog/hackathon-judging-tips) · [Devfolio, The Discerning Machine](https://devfolio.co/blog/the-discerning-machine/) · [MLH Judging Plan](https://guide.mlh.io/general-information/judging-and-submissions/judging-plan) · [Google ADK Hackathon results](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights) · [Opus 4.6 hackathon winners](https://claude.com/blog/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon) · [Opus 4.7 hackathon winners](https://claude.com/blog/meet-the-winners-of-built-with-opus-4-7-claude-code-hackathon) · [Rippletide, winning the Codex hackathon](https://www.rippletide.com/resources/blog/winning-the-openai-codex-hackathon-moving-from-outputs-to-outcomes-the-decision-layer) · [Eval-Driven Development](https://claudeskills.info/blog/everything-claude-code-hackathon-eval-driven/) · [Agno Global Agent Hackathon winners](https://www.agno.com/blog/global-agent-hackathon-winners) · [Solo.io MCP hackathon winners](https://www.solo.io/blog/celebrating-the-winners-of-the-2026-hackathon-for-mcp-ai-agents) · [lablab.ai recent winners](https://lablab.ai/apps/recent-winners) · [8,200 hackathon projects](https://simbro.medium.com/what-8-200-hackathon-projects-reveal-about-what-actually-wins-f105346ec97c) · [Why AI fails at evaluating hackathons](https://medium.com/@gauurab/why-current-ai-models-fail-at-evaluating-hackathons-and-what-we-actually-need-de28cb87b6e5) · [Colosseum submission guide](https://blog.colosseum.com/perfecting-your-hackathon-submission/) · [Devpost demo video tips](https://info.devpost.com/blog/6-tips-for-making-a-hackathon-demo-video) · [Lessons from winning five hackathons](https://sustained.substack.com/p/lessons-from-winning-five-hackathons) · [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) · [Detecting AI writing](https://theconversation.com/can-you-teach-yourself-to-detect-ai-writing-maybe-289236) · [MAST arXiv:2503.13657](https://arxiv.org/abs/2503.13657) · [Agent failure modes](https://www.openlayer.com/blog/ai-agent-failure-modes-tool-calling-loops-propagation) · [LLM-as-judge guide](https://www.openlayer.com/blog/llm-as-judge-evaluation-guide) · [DeepEval judge](https://deepeval.com/blog/llm-as-a-judge) · [DeepEval eval harness](https://deepeval.com/blog/what-is-an-eval-harness) · [VCR tests for LLMs](https://anaynayak.medium.com/eliminating-flaky-tests-using-vcr-tests-for-llms-a3feabf90bc5) · [Caching in agentic pipelines](https://www.ai21.com/blog/caching-in-agentic-llm-pipelines/) · [ACM Artifact Badging](https://www.acm.org/publications/policies/artifact-review-and-badging-current) · [Taxonomy of RL environments](https://leehanchung.github.io/blogs/2026/03/21/rl-environments-for-llm-agents/) · [Unsloth RL environments](https://unsloth.ai/blog/rl-environments) · [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) · [OpenTelemetry for AI](https://uptrace.dev/blog/opentelemetry-ai-systems) · [Script timing](https://www.teleprompter.com/blog/how-to-time-your-script) · [Polished TUI demo video](https://blog.kunchenguid.com/p/making-a-polished-tui-demo-video)
