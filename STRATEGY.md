# Strategy — what we're building and why

*Written 2026-08-29, after three parallel research passes. Sources in `research/`.*

## The recommendation

**Build an agent that manufactures verifiable RL environments from real open-source bug-fix commits, and measure it on the one thing that matters: how many candidate commits it converts into environments that actually validate.**

Working name: **Crucible** (change it if you hate it).

---

## Why this one

### 1. It is literally the artifact micro1 pays $50–100/hour for

Their live Senior Software Engineer listing:

> *"Your task will be to create reproducible RL environments that test a model's ability to solve these workflows along with a golden reference solution."*

And the Open Source Contributor listing:

> *"you will be creating Reinforcement Learning Environments which test an AI model's ability to solve complex software engineering problems related to fixing code, creating features, refactoring code and optimizing performance."*

The hackathon links to those two roles as its "paid opportunities." The judges are the people who buy this. We are not guessing what they value — they published a price for it.

### 2. The ground truth is deterministic, free, and unfakeable

An environment is **valid** if and only if:

| Check | How it's verified |
|---|---|
| Fail-to-pass tests **fail** at the parent commit | Run them. Exit code. |
| Fail-to-pass tests **pass** at the fix commit | Run them. Exit code. |
| Pass-to-pass tests pass at **both** commits | Run them. Exit code. |
| The whole thing rebuilds hermetically in the container | `docker build` + `pytest`. |

No LLM judge in the primary metric. No rubric argument. No "our judge agrees 85% of the time." This is Jason Wei's asymmetry of verification taken to its limit — the task is hard to do and trivial to check. Every other entrant will be defending a subjective score; we hand the judge an exit code.

It also means **the eval costs compute, not tokens** — which matters given the $20 budget.

### 3. The reward-hacking story is built in, not bolted on

The agent has obvious cheats available: write a fail-to-pass test that trivially differs between the two commits without testing the actual behavior; leak the golden patch into the environment's visible files; pick tests that are flaky rather than genuinely fixed by the commit.

SpecBench found exactly this shape — a Codex-generated C compiler that hit 97% on visible tests and 0% held-out by hashing inputs to precomputed outputs. So we build a **held-out adversarial verifier** the agent's development loop never sees, and report the **reward-hacking gap** (visible validity rate minus held-out validity rate) as a headline number.

Almost nobody in a hackathon reports a number that makes them look worse. Doing it is the strongest possible signal to an evals company.

### 4. The human approval gate is the product, not a compliance checkbox

Ground Rules 04 and 05 require human approval before consequential actions. Most entries will bolt on a `input("approve? y/n")`.

Here, the expert reviewing a generated environment before it enters the dataset **is the actual workflow** — it's how micro1's own contractor pipeline works, and it's Ali Ansari's stated thesis:

> *"high-confidence evaluation still requires human judgment as the grounding layer."*

Their research paper *No Last Mile* argues structured human judgment is a permanent production input, not a transitional one. An agent that **amplifies** the expert rather than replacing them is their worldview, shipped.

Measurable consequence: **human review minutes per accepted environment** is our "human time per task" row, and it's the number the buyer actually cares about.

### 5. The user is specific and the bottleneck has a price tag

Not a persona. An eval/data engineer at an AI lab whose job is authoring verified RL environments, paid $50–100/hour, against a weekly quota, where a single environment takes hours of expert time — most of it spent on candidates that turn out to be unusable after you've already done the work.

That is the 15-point Problem & User Value row answered with a number and a unit, sourced to a public job posting.

### 6. Cost and trajectories both come nearly free

- **Agent under test:** Claude Code headless (`claude -p`) runs on the subscription, so eval rollouts cost ~$0 in marginal API spend.
- **Trajectories:** Claude Code writes full JSONL per session to `~/.claude/projects/`. `uvx claude-code-log` renders committable static HTML. The hardest-to-fake required deliverable is a byproduct.
- **The $20** stays reserved for a cross-model judge (different family than the actor, per the self-preference research) on the few genuinely qualitative criteria.

---

## The primary metric

**Validated environment yield per 100 candidate commits.**

This is good because it is a rate, it is deterministic, it has an honest strong baseline, and it maps directly onto the buyer's economics.

| Metric | What it measures |
|---|---|
| **Primary — validated yield** | % of candidate commits converted into environments passing all four validity checks |
| **Held-out yield** | Same, against the adversarial verifier the agent never saw |
| **Reward-hacking gap** | Primary minus held-out. Lower is better. Report it even though it hurts. |
| Human review min / accepted env | The "human time per task" row |
| Cost / accepted env | Tokens × price. Compare to $50–100/hr human authoring. |
| pass^k over k rollouts | Does it produce a *valid* environment every time, or one time in three? |

### The baseline must be strong, and here it is honest by construction

SWE-bench's own construction pipeline is heuristic: filter PRs that close an issue, that touch tests, then keep only the ones where the fail-to-pass transition validates automatically. **It discards the large majority of candidates.**

So the baseline is *that pipeline* — a real, respected, genuinely strong method, not a strawman we crippled. The claim becomes precise and falsifiable:

> On candidates the heuristic pipeline rejects, the agent recovers N% into valid environments, at $X each, versus $50–100/hour of expert time.

Per "AI Agents That Matter," we also run a **retry-with-warming** baseline, because retry alone matches many published agent architectures at 1/50th the cost, and a judge from an evals company will ask.

**Position against SWE-bench explicitly and generously in the README.** Claiming novelty we don't have reads as naive; crediting the prior art and stating precisely where we differ reads as senior.

---

## The changelog arc (planned, not yet run)

The rubric rewards *purposeful* choices and explicitly asks for an experiment you removed. Plan the removals in advance so we actually run them:

| # | Experiment | Expected outcome | Why we run it |
|---|---|---|---|
| Baseline | Heuristic pipeline only | Low yield, $0 | Establishes the floor honestly |
| Baseline+ | Retry-with-warming | Modest lift, cheap | Inoculates against "you beat a strawman" |
| It 1 | Give the agent the container + test-execution tool | Large lift | External signal — the thing that actually works |
| It 2 | **Bare self-critique loop, no external signal** | **Flat or negative** | The planned removal. Huang et al. predict this. Proves the Hot Take with our own numbers. |
| It 3 | Replace self-critique with execution-grounded verification | Large lift | The contrast that makes It 2 meaningful |
| It 4 | Windowed file reads + last-N observations vs full context | Small lift | Cites SWE-agent's ablation (full file −5.3, full history −3.0) next to our own |
| It 5 | Multi-agent split (harvester / author / verifier) | Likely negative at 15x tokens | Second planned removal. Measured, not asserted. |
| Final | Whatever survived | — | Ablation table, not an architecture diagram |

Two planned removals with real numbers, against a modal field whose changelogs contain zero.

---

## The Hot Take

> Self-correction is not a capability, it's a wiring diagram. The same reflection loop that gains +8 points with an external correctness signal *loses* up to 38 without one. The question is never "should the agent check its work" — it's "what non-model signal is the check made of?" If you can't name it, you've built a loop that will talk itself out of correct answers. And once you do name it, the agent starts optimizing against it, so you need a held-out copy too.

Grounded in Huang et al. (ICLR 2024), Kamoi et al. (TACL), the Self-Correction Illusion paper, and SpecBench — **and in our own It 2 vs It 3 numbers**, which is what makes it ours rather than a citation.

---

## Known risks, stated up front

**Dependency hell is the real threat.** Building arbitrary OSS repos at arbitrary historical commits is genuinely hard, and it's where this project dies if it dies.

Mitigation: restrict the corpus to a hand-checked set of pure-Python libraries — no compiled extensions, no exotic build systems — where `pip install -e . && pytest` works at HEAD. Pre-bake a Docker image with the deps. **Validate the corpus manually before writing any agent code.** If a repo fights us for more than 20 minutes, drop it and pick another. This is a first-hours task, not something to discover on day two.

**Scope.** Don't let the agent do the parts a script does better. Harvesting candidate commits from the GitHub API is deterministic — write it as a script. The agent's remit is the genuinely hard judgment: reconstructing the environment, selecting or authoring the fail-to-pass tests, writing the golden reference, and deciding whether a candidate is salvageable at all.

**SWE-bench adjacency.** Addressed above — credit it loudly, differentiate precisely.

**Fallback if the corpus proves unworkable:** keep the entire eval architecture (deterministic verifier, held-out split, reward-hacking gap, planned removals) and swap the substrate to CI-failure triage on a fixed set of pinned repos. The eval design is the valuable part and it transfers.

---

## What we are deliberately not doing

- No web dashboard. A real CLI with `--help` and a self-contained HTML report beats a half-finished Streamlit app.
- No multi-agent architecture by default. One measured experiment, then removal if it doesn't pay.
- No LLM judge in the primary metric.
- No LangSmith/Braintrust links — a judge who has to log in can't see our work.
- No `latest` model aliases, no single-run numbers, no emoji headers, no "✨ Features."

---

## Build order (when we start tomorrow)

Tier 0 first, because it can zero the submission:

1. **Hand-validate the repo corpus.** 6–10 pure-Python repos, confirmed buildable and testable at a historical commit. Nothing else starts until this works.
2. **The verifier.** Deterministic, containerized, four checks, exit codes. Build this before the agent — it's what everything is measured against.
3. **Offline replay layer.** `make eval` reproduces the published report with no API key, no network, under a minute. Tested on a clean clone with wifi off.
4. **Harvest script** → candidate commit corpus, split into dev / held-out. Never iterate against held-out.
5. **Baselines**, both of them, numbers committed to git before any agent work.
6. Then the agent, one capability per changelog row, full eval after each.

Detailed hour-by-hour allocation is in `research/02-winning-patterns.md` §12; the technique-by-technique priority list with hour estimates is `research/03-technical-playbook.md` §8.
