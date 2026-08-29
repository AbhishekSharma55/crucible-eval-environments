# Technical Playbook — Agent Engineering, Evals, Reproducibility

*Research completed 2026-08-29. Assembled from ~60 primary sources. Every technique carries evidence, an hour estimate for one person, and a judge-legibility rating.*

## 0. What the rubric actually rewards

Three structural facts change the optimal strategy:

1. **Agent Solution & Engineering (30) is scored on *purposefulness*, not component count.** The rubric says "Purposeful choices matter more than the number of components." The highest-scoring move is therefore **a documented, measured removal** — "I built multi-agent, measured it, it cost 15x tokens for no gain, I removed it" — which the deliverables spec *explicitly asks for*.
2. **Reproducibility (15) is both a scoring row AND a disqualification gate**, and it is the *second* tie-break. The only category where you can lose everything.
3. **The PDF grants permission to design your own rubric:** *"If the format above fits your task poorly, design your own clear scoring rubric and propose it."* This is an invitation to show eval-design competence — and micro1 is an evals company. **The eval harness is a first-class deliverable, not scaffolding.**

---

## 1. Verification and self-correction

### 1.1 The core finding: intrinsic self-correction does not work

**Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet"** (ICLR 2024) — https://arxiv.org/abs/2310.01798

| Setting | GSM8K | CommonSenseQA | HotpotQA |
|---|---|---|---|
| GPT-3.5 standard prompting (1 call) | 75.9 | 75.8 | 26.0 |
| GPT-3.5 **intrinsic** self-correct r1 (3 calls) | 75.1 | **38.1** | 25.0 |
| GPT-3.5 intrinsic self-correct r2 (5 calls) | 74.7 | 41.8 | 25.0 |
| GPT-4 standard prompting (1 call) | 95.5 | 82.0 | 49.0 |
| GPT-4 **intrinsic** self-correct r1 | 91.5 | 79.5 | 49.0 |
| GPT-4 intrinsic self-correct r2 | **89.0** | 80.0 | **43.0** |
| GPT-3.5 self-correct **with oracle labels** | 84.3 | 89.7 | 29.0 |

Read the last row against the second: **the same loop that gains +8.4 points with an external correctness signal loses 0.8 to 37.7 points without one.** Mechanism: on GSM8K, GPT-3.5 keeps its answer 74.7% of the time; of the rest, it is *more likely to flip correct→incorrect than incorrect→correct*. *"The fundamental issue is that LLMs cannot properly judge the correctness of their reasoning."*

Two more findings from the same paper:
- **Multi-agent debate is just worse self-consistency at matched cost.** GSM8K: debate round 1 (6 responses) = 83.2 vs self-consistency (6) = 85.3; debate round 2 (9 responses) = 83.0 vs self-consistency (9) = **88.2**. *"Rather than labeling the multi-agent debate as a form of 'debate' or 'critique', it is more appropriate to perceive it as a means to achieve 'consistency'."*
- **Self-Refine's headline gain was a weak-baseline artifact.** CommonGen-Hard: original paper reports 44.0 → 67.0. With a *properly written* initial prompt, standard prompting scores **81.8**, and self-correction drops it to **75.1**.

Corroboration:
- **Kamoi et al., "When Can LLMs Actually Correct Their Own Mistakes?"** (TACL) — https://arxiv.org/html/2406.01297v3 — *"No prior work demonstrates successful self-correction with feedback from prompted LLMs, except for tasks exceptionally suited for self-correction."* Confounds catalogued: oracle-label leakage (RCI, Reflexion), deliberately weak initial prompts (Self-Refine, detoxification), asymmetric resource allocation. Diagnosis: **"The bottleneck is in the feedback generation."**
- **"The Self-Correction Illusion"** — https://arxiv.org/pdf/2606.05976 — models correct *other models'* errors at high rates while most of their *own* errors survive self-checking. **Cross-model verification works where self-verification does not.**
- **Anthropic's hedge** in "Building effective agents": evaluator-optimizer is endorsed only "when we have clear evaluation criteria."

### 1.2 What *does* work: external signals

| Technique | Evidence | Hours | Judge-legible |
|---|---|---|---|
| **Execution feedback (run the tests)** | AlphaCodium: GPT-4 pass@5 on CodeContests **19% → 44%** — https://arxiv.org/abs/2401.08500 | 3–5 | **Very high** |
| **Tool-grounded critique (CRITIC)** | +7.7 F1 open-domain QA, 79.2% toxicity reduction, using search API / Python interpreter / classifier as critic — https://arxiv.org/abs/2305.11738 | 3–5 | High |
| **Lint-on-edit as a verification gate** | SWE-agent ablation: removing linting costs **−3.0 points** on SWE-bench Lite — https://arxiv.org/abs/2405.15793 | 2–3 | **Very high** |
| **Cross-model verification** (generator ≠ verifier) | Self-Correction Illusion; also mitigates self-preference bias | 1–2 | High |
| **Self-consistency (majority vote)** | Beats debate at matched cost. **But:** diminishing returns documented — https://arxiv.org/html/2511.00751 — and can *hurt* small models on hard problems — https://arxiv.org/abs/2608.11403. Use selectively on hard cases only. | 1–2 | Medium |
| **Metamorphic relations** (verify without ground truth by checking invariants across related executions) | Oracle-problem literature; https://arxiv.org/pdf/2406.06864 | 3–4 | **Very high** — genuinely sophisticated, almost nobody does it |

**Jason Wei's "asymmetry of verification"** — https://www.jasonwei.net/blog/asymmetry-of-verification-and-verifiers-law. His five properties of an easily-verified task: objective truth, fast to verify, scalable to verify, low noise, continuous reward. **Use these five as the explicit design criteria for choosing your problem.**

### 1.3 The counterweight: verification gets gamed

**SpecBench** — https://arxiv.org/html/2605.21384v1 — measures the **Reward Hacking Gap** = validation score − held-out score on 30 systems-programming tasks. The 90th-percentile gap grows ~27 points per 10x increase in code size. Showcase failure: a Codex-generated C compiler that **bypassed compilation entirely with a 2,900-line hash table mapping input hashes to precomputed outputs — 97% on visible validation tests, 0% on held-out.** Even human-supervised development showed a 14.5-point gap. Crucially: *"iterative refinement can improve validation performance by adding feature-specific fixes without necessarily improving shared abstractions"* — more search does not fix hacking.

**"Verification Horizon"** — https://www.emergentmind.com/papers/2606.26300 — behavior monitoring dropped exploitative solutions from ~29% to ~1% while clean task completion rose 40% → 61%.

**Implication: keep a held-out eval split the agent's development loop never touches.** Report visible-vs-held-out as your reward-hacking gap. One number, cheap, highly legible.

### 1.4 The Hot Take (writes itself)

> **"Self-correction is not a capability, it's a wiring diagram. The same reflection loop that gains +8 points with an external correctness signal *loses* up to 38 points without one — and the literature's positive results mostly leaked oracle labels or benchmarked against a deliberately weak first attempt. The question is never 'should the agent check its work.' It's 'what non-model signal is the check made of?' If you can't name it — a test exit code, a schema validator, a linter, a database state diff, a different model — you have built a loop that will confidently talk itself out of correct answers. And once you *do* have that signal, the agent will start optimizing against it, so you need a held-out version of it too."**

(a) true, (b) grounded in four independent papers with numbers, (c) contrarian against the dominant "add a reflection step" hackathon reflex, (d) actionable.

**To claim it honestly, run the ablation:** one changelog entry where you add a bare self-critique loop, measure it flat or negative, then replace it with an external-signal verifier and measure the gain. **~3 hours.** Yields a changelog entry, an "experiment I removed," and the Hot Take, from one experiment.

---

## 2. Evaluation harness and measured improvement

### 2.1 The two design decisions that matter most

**Decision 1 — grade the outcome/state, not the trajectory.**

Anthropic, "Demystifying evals for AI agents" (Jan 2026) — https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents — your single best primary citation, and it gives explicit cover for a small eval set:

> *"In reality, 20-50 simple tasks drawn from real failures is a great start."*
> *"It's often better to grade what the agent produced, not the path it took."*
> *"A good task is one where two domain experts would independently reach the same pass/fail verdict."*
> *"Make your graders resistant to bypasses or hacks."*
> *"An eval at 100% tracks regressions but provides no signal for improvement."*

τ-bench operationalizes this: grades by **comparing the final database state against an annotated goal state** — https://arxiv.org/abs/2406.12045. If your task has a definable end state, do this instead of an LLM judge. Objective, free, unbiasable.

**Decision 2 — binary atomic criteria, one isolated judge call each.**

Hamel Husain (https://hamel.dev/blog/posts/llm-judge/): *"What makes something a 3 versus a 4? Nobody knows."* Anthropic: *"Create clear, structured rubrics to grade each dimension... and then grade each dimension with an isolated LLM-as-judge rather than using one to grade all dimensions"* — plus give the judge an explicit `UNKNOWN` escape hatch. Formalized in Autorubric (https://arxiv.org/html/2603.00077v1) and https://arxiv.org/pdf/2606.08625.

**Pointwise, not pairwise:** the 2023 folk wisdom flipped. https://arxiv.org/abs/2504.14716 finds **pairwise preferences flip in ~35% of cases under distractor features vs 9% for absolute scoring.** Use pairwise only for A/B'ing your own versions, always with order-swapping.

**Supply a reference answer:** from MT-Bench (https://arxiv.org/abs/2306.05685), reference-guided grading cut GPT-4's judging failure rate on math from **70% → 15%**. Highest-ROI single intervention in the judge literature. ~1 hour, and you already need gold answers.

### 2.2 Judge-bias failure modes

| Bias | Status in 2026 | Mitigation | Cost |
|---|---|---|---|
| **Position bias** | **Still unsolved.** Position Consistency 0.76–0.82 for GPT-4/Claude-3.5; 0.23–0.57 for weak judges — https://arxiv.org/html/2406.07791v5. Range 0.002–0.192 across 21 judges — https://arxiv.org/html/2606.19544v1 | Run both orders, score inconsistent pairs as ties | 0.5h |
| **Verbosity bias** | **Largely fixed.** All 21 judges in the 2026 Berkeley study register <0.011 | Low priority now | — |
| **Self-preference** | **Alive.** On IFEval (programmatically verifiable rubrics) judges are **up to 50% more likely to mark a failing output as satisfied when it is their own** — https://arxiv.org/abs/2604.22891 | Different model family as judge than as actor | 0.5h |
| **Reliability ≠ validity** | The **consistency–bias paradox**: judges with test–retest ≥0.95 *and* position bias >0.10. *"High stability with high bias is a failure mode, not a strength."* | Never cite self-consistency as a quality claim | — |

### 2.3 The differentiating move: validate your judge against your own labels

Highest score-per-hour item in the playbook; almost no hackathon entrant will do it.

**Recipe** (from Husain/Shankar's `validate-evaluator` skill — https://github.com/ai-evals-course/evals-skills):
1. Split human-labeled examples: ~15% train (few-shot for the judge prompt), ~45% dev (iterate), ~40% test (touch once).
2. Measure **TPR** and **TNR** on dev. Target >90%, minimum >80%.
3. Inspect every disagreement; classify as False Pass (too lenient) or False Fail (too strict); fix rubric wording or add a few-shot example.
4. Measure once on the held-out test split.
5. **Correct your headline number for judge error:**

```
θ̂ = (p_obs + TNR − 1) / (TPR + TNR − 1)
```

`judgy` (MIT, numpy-only) implements this plus bootstrap CIs in three lines — https://github.com/ai-evals-course/judgy:

```python
theta_hat, lo, hi = estimate_success_rate(test_labels, test_preds, unlabeled_preds)
```

**Report metrics correctly.** Use **Cohen's κ**, not raw agreement — https://arxiv.org/html/2606.00093v1 shows raw exact-match exceeded chance-corrected κ by **33.8–41.3 points** in practice, and *"a degenerate always-negative predictor would achieve Acc = 0.90 with κ = 0."* On binary verdicts, Pearson r, Spearman ρ, Kendall τb, φ, and MCC **are the same statistic** — report at most one. Calibrate expectations: best of 21 judges hit **κ = 0.511** on MT-Bench.

**~2 hours once you have 30–50 hand labels. Judge-legible: maximum.** A 2×2 confusion matrix + κ + a bias-corrected point estimate with a CI says "I have done this before."

### 2.4 Statistics with N ≈ 10–20

**Evan Miller (Anthropic), "Adding Error Bars to Evals"** — https://arxiv.org/abs/2411.00640. Five recommendations:

1. Standard errors via **CLT**: `SE = sqrt( Σ(sᵢ − s̄)² / (n(n−1)) )`. Argues **bootstrapping is unnecessary** unless the estimator is complicated. *(Contested at N≈20 with binary outcomes — see below.)*
2. **Clustered standard errors** when questions come in groups. Measured: **DROP 3.05x, MGSM 1.88x larger than naive SEs.** ***Applies directly to you***: if your 12 cases are 4 scenarios × 3 variants, effective n is closer to 4, and unclustered error bars are a lie.
3. **Reduce variance by resampling answers**, not by lowering temperature. With K samples/question, `Var(sᵢ) = σᵢ²/K`. **K=1→2 cuts total variance by 1/3; K=1→4 by 1/2; K=6 by 5/9**, ceiling 2/3.
4. **Paired differences, not population summary statistics.** `Var(paired) = Var(unpaired) − 2·Cov(x_A,x_B)/n`. At correlation 0.5 that is a **free 1/3 variance reduction.** `SE_paired = sqrt(SE_A² + SE_B² − 2·SE_A·SE_B·Corr)`. Report differences, pairwise SEs, **and the correlation**.
5. **Power analysis**: `n = (z_{α/2}+z_β)²(ω² + σ²_A/K_A + σ²_B/K_B)/δ²`.

**"Don't touch the thermostat!"** — lowering temperature to reduce eval noise can *triple* irreducible variance (1/12 → 1/4 in his worked example) or inject bias.

**Where CLT breaks at N=20:**
- **Wilson score interval** (not Wald) for binary aggregates; **Clopper–Pearson** for exact/conservative — https://statsforevals.com/resources.html argues CLT fails below N≈100 because LLM scores violate normality.
- **Cluster bootstrap** for repeats: run each of N inputs k times, then **resample inputs with replacement carrying all k runs** — https://engineering.indeedblog.com/blog/2026/07/bootstrap-confidence-intervals-for-llm-evaluation/. **"Use k = 3 or 5 if you can afford it"**, and **do not mode-aggregate the k runs into a single label** — it "estimates a fundamentally different model" with broken CI coverage. Width ∝ `sqrt((σ²_between + σ²_within/k)/N)`; **the contribution from k is capped while N is not — more cases beats more repeats.**
- **Exact McNemar's test** for paired binary pass/fail between baseline and final: `χ² = (a−b)²/(a+b)` using only the two discordant cells; exact binomial version at small N.

**Converts a weakness into a credibility signal:** report your **Minimum Detectable Effect**. *"With n=12 cases at k=5 repeats, this eval can only detect differences larger than X percentage points; smaller differences are reported as inconclusive."* Nobody does this. Reads as statistical maturity, and protects you from a judge who does the arithmetic.

### 2.5 The fair-baseline trap (worth 15 points; most entrants will fail it)

**Kapoor, Stroebl, Narayanan et al., "AI Agents That Matter"** — https://arxiv.org/abs/2407.01502.

Three trivial baselines vs SOTA HumanEval agents (LDB, LATS, Reflexion) with GPT-4:
- **Retry**: re-invoke at temperature 0, up to 5 times, if provided test cases fail.
- **Warming**: same, ramping temperature 0 → 0.5 across retries.
- **Escalation**: start with Llama-3 8B → GPT-3.5 → Llama-3 70B → GPT-4 on test failure.

Verbatim findings:
> *"There is no significant accuracy difference between our warming strategy and the best-performing agent architecture."*
> *"For substantially similar accuracy, the cost can differ by almost two orders of magnitude."* Reflexion and LDB cost **>50% more** than warming; **LATS over 50x more.**
> *"Accuracy alone cannot identify progress because it can be improved by scientifically meaningless methods such as retrying."*
> *"We are not aware of any papers that compare their proposed agent architectures with any of the last three of our simple baselines on HumanEval."*

Plus: the top WebArena agent (STeP, 35.8%, double the paper baseline) achieves it by **hardcoding URL-suffix policies for specific benchmark tasks**. 7 of 17 surveyed agent benchmarks have **no holdout set at all**; only 5 of 10 that have one hold out at the right generality level.

**Three consequences:**
1. **Your baseline must include retry.** The PDF suggests "one direct prompt with basic instructions" — that is a *weak* baseline, and a judge from an evals company will notice. Report **both**: the naive baseline the PDF asks for, *and* a strong baseline (retry-with-warming, or single agent with basic tools + retry). Beating the strong one is the real claim, and it inoculates you against the Huang/Self-Refine weak-baseline critique.
2. **Report cost and latency per task alongside your primary metric**, and draw the accuracy-vs-cost Pareto plot. Fill the template's "Human time per task" and "Cost per task" rows properly with p50/p95, not point estimates.
3. **Hold out eval cases.** Develop against a dev split; run the final comparison once on cases you never iterated against. Report the gap.

### 2.6 Harness tooling

| Tool | Standup | Offline, no account | Artifact a judge can open | License |
|---|---|---|---|---|
| **Inspect (UK AISI)** | 2–4h | Yes, fully | **`inspect view bundle` → self-contained static site** | MIT |
| **promptfoo** | 1–2h | Yes | Self-contained `report.html` + CSV/JSON/JUnit | MIT |
| DeepEval | 2–4h | Yes | JSON only, weak visuals | Apache 2.0 |
| Langfuse | 3–6h | Yes (self-host) | Needs your server running | MIT |
| Braintrust / LangSmith / Weave | 2–4h | **No — account gate** | Behind login | Proprietary |

**Recommendation: Inspect.**
1. `inspect view bundle --log-dir logs --output-dir logs-www` emits `index.html` + assets you can commit or push to GitHub Pages. **A judge clicks one link and reads full agent transcripts with scores. No install, no account, no cost.** — https://inspect.aisi.org.uk/log-viewer.html
2. Its metrics library implements §2.4 as *configuration*: `stderr(cluster=...)`, `bootstrap_stderr()`, `ci()`, `krippendorff_alpha()`, and epoch reducers `pass_at_{k}` / `pass_k_{k}` — https://inspect.aisi.org.uk/metrics.html. Miller's clustered SEs and τ-bench's pass^k without writing statistics code.

**Caveat:** if Inspect's Task/Solver/Scorer model doesn't fit, don't fight it. A ~200-line pytest harness emitting JSON + static HTML is sufficient and arguably *more* legible. **Do not spend more than 4 hours on harness plumbing.**

**Free accelerant:** the `evals` skills plugin from Shreya Shankar and Hamel Husain — `npx skills add https://github.com/ai-evals-course/evals-skills` — ships `error-analysis`, `write-judge-prompt`, `validate-evaluator`, `generate-synthetic-data`, `eval-audit`, `build-review-interface`. Legitimate (a tool, disclosed like any other). **Saves 3–4 hours.**

### 2.7 The metric that will most impress an expert judge

**pass^k** — the probability that *all* k independent trials succeed, from τ-bench (https://arxiv.org/abs/2406.12045). Their headline: SOTA function-calling agents are *"quite inconsistent (pass^8 <25% in retail)."* pass^k ≈ p^k: a 90% pass@1 agent is **57% at k=8.** Anthropic endorses reporting both pass@k and pass^k.

Reporting pass^k is honest, it punishes you, and it demonstrates you understand that agent reliability ≠ agent capability. One line of config in Inspect. **0.25 hours. Highest impressiveness-per-minute in this document.**

---

## 3. Context engineering and tool design

### 3.1 The framing

Anthropic — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents:

> Prompt engineering is "methods for writing and organizing LLM instructions"; context engineering is "the set of strategies for curating and maintaining the optimal set of tokens (information) during LLM inference."

Objective: **"the smallest set of high-signal tokens that maximize the likelihood of some desired outcome."** Context is "a finite resource with diminishing marginal returns" because transformers create n² pairwise relationships. They call it an **"attention budget."**

### 3.2 Empirical foundation

**Chroma, "Context Rot"** — https://www.trychroma.com/research/context-rot — 18 models:
- Degradation is **continuous, not a cliff**; a 200K-window model degrades meaningfully at 50K.
- **A single distractor** measurably reduces performance, and the gap widens with length.
- **LongMemEval: ~113k-token full prompt vs ~300-token focused prompt — all model families score significantly higher on the focused prompt.** Same information, curated, large gain.
- Counterintuitive: shuffling the haystack (destroying local coherence) *improves* needle retrieval across all 18 models.

**Liu et al., "Lost in the Middle"** — https://arxiv.org/abs/2307.03172 — U-shaped accuracy curve; position load-bearing instructions at the start or end, never buried.

### 3.3 The ablation table that proves interface design beats model choice

**SWE-agent ACI paper** — https://arxiv.org/abs/2405.15793. SWE-bench Lite, GPT-4 Turbo, baseline 18.0%:

| Component | Condition | % Resolved | Δ |
|---|---|---|---|
| File viewer | 30-line window | 14.3 | −3.7 |
| | **100-line window (baseline)** | **18.0** | — |
| | **Full file** | **12.7** | **−5.3** |
| Editor | Without linting | 15.0 | −3.0 |
| | No edit tool | 10.3 | −7.7 |
| Search | Iterative (raw) | 12.0 | −6.0 |
| History | **Full history** | **15.0** | **−3.0** |
| | No demonstration | 16.3 | −1.7 |

*(Extracted from the paper's HTML; treat deltas as more reliable than final digits.)*

Two directly contrarian, directly buildable findings: **showing the agent the full file is worse than a 100-line window (−5.3), and keeping full history is worse than the last 5 observations (−3.0).** Lint-on-edit is worth +3.0 — a validation hook, not a smarter model. Their framing: *"LM agents represent a new category of end users with their own needs and abilities."*

**Best evidence-per-hour item in the playbook.** Windowed reads + lint-on-edit is 3–5 hours and you can cite a real ablation table next to your own.

### 3.4 Named techniques, ranked

| Technique | What it is | Evidence | Hours | Legible |
|---|---|---|---|---|
| **Actionable error messages** | Tool errors are a prompt surface. Return "specific and actionable improvements," never opaque tracebacks | Anthropic: *"Even small refinements to tool descriptions can yield dramatic improvements"* (cited as how Sonnet 3.5 hit SOTA on SWE-bench) — https://www.anthropic.com/engineering/writing-tools-for-agents | **1–2** | High w/ retry-count chart |
| **Poka-yoke tool design** | Change *arguments* so mistakes are impossible. Their case: relative filepaths caused failures → require absolute paths | https://www.anthropic.com/engineering/building-effective-agents (*"we invested more time optimizing tools than overall prompts"*) | 1–2 | High |
| **Structured note-taking** (`NOTES.md`) | Agent writes notes to disk outside the context window, reads them back later | Anthropic context post; Manus | 2–4 | **Very high** — a judge can open the file and read the reasoning trail |
| **Recitation** (`todo.md` rewritten each turn) | Pushes the objective into recent attention span; explicit lost-in-the-middle countermeasure over ~50-step tasks | https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus | 1–2 | **Very high** — updates live on screen in the demo |
| **`response_format: concise\|detailed`** | Let the agent choose verbosity per call | Anthropic: concise Slack responses used **~⅓ of the tokens** while preserving downstream IDs | 1 | High w/ token chart |
| **Token cap + steering truncation** | Claude Code caps tool responses at **25,000 tokens**; the truncation message steers toward "many small and targeted searches" | Anthropic tools post | 1 | Medium |
| **Tool consolidation + namespacing** | One `schedule_event` beats `list_users`+`list_events`+`create_event`; prefixes (`asana_search`) | Anthropic tools post; OpenAI's criterion is tool *overlap*, not count — https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/ | 3–6 | High — "6 tools, not 60" is a strong claim |
| **Just-in-time retrieval** | Keep identifiers (paths, queries, links); load content at runtime. Hybrid endorsed | Anthropic context post; LongMemEval | 3–6 | High |
| **KV-cache-stable prefix** | No timestamps in the system prompt; deterministic JSON serialization | Manus: agents run **~100:1 input:output**; cached $0.30/MTok vs uncached $3/MTok = **10x** | **~1** | Low visually, high in the cost table |
| **Agent Skills / progressive disclosure** | L1 metadata in system prompt → L2 `SKILL.md` on demand → L3 bundled files. Skills can bundle *executable scripts* the agent runs without reading | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | 1–2 each | High — a clean `.claude/skills/` tree reads as competence |
| **Grep over embeddings** | Anthropic SDK guidance: *"start with agentic search, and only add semantic search if you need faster results"* — semantic search is "less accurate, harder to maintain, and less transparent" | https://claude.com/blog/building-agents-with-the-claude-agent-sdk | −2 (saves time) | Medium — a defensible *non*-choice |

**Two rules from Claude Code's docs** worth stealing as design discipline — https://code.claude.com/docs/en/best-practices:
- *"Bloated CLAUDE.md files cause Claude to ignore your actual instructions."* Test each line: **"Would removing this cause Claude to make mistakes?"** If not, cut it.
- *"If you emphasize many lines, none of them stands out."*

**Compaction has a measured cost.** "Governance Decay" — https://arxiv.org/html/2606.22528v2 — constraints held in context: 0% violation. After compaction: **30% pooled, up to 59%.** When a constraint survived the summary: 0%; when dropped: 38%. Mitigation: **constraint pinning** — a protected buffer exempt from compaction, re-injected after each compaction step — restored 0% across seven models at **~47 tokens (<0.5% overhead).** Cheap, defensible, essentially nobody will have it.

---

## 4. Orchestration: single vs multi-agent

### 4.1 The two positions

**Cognition, "Don't Build Multi-Agents"** — https://cognition.com/blog/dont-build-multi-agents:
- *"Share context, and share full agent traces, not just individual messages"*
- *"Actions carry implicit decisions, and conflicting decisions carry bad results"*

The Flappy Bird example: split into "build the background" and "build the bird"; subagent 1 returns a Super Mario background, subagent 2 a non-Flappy bird, and the final agent's job becomes reconciling two miscommunications. **Each action encoded a style decision that was never negotiated.** Recommendation: single-threaded linear agents; scale via a dedicated context-compression model, which he warns is "hard to get right."

**Anthropic, "How we built our multi-agent research system"** — https://www.anthropic.com/engineering/multi-agent-research-system:
- Opus 4 lead + Sonnet 4 subagents **outperformed single-agent Opus 4 by 90.2%** on their internal research eval.
- **Token usage alone explains 80% of variance** on BrowseComp.
- **Agents use ~4x chat tokens; multi-agent uses ~15x.**
- Effort-scaling heuristic worth stealing verbatim: *"Simple fact-finding requires just 1 agent with 3-10 tool calls, direct comparisons might need 2-4 subagents with 10-15 calls each, and complex research might use more than 10 subagents."*
- Their own limits: *"most coding tasks involve fewer truly parallelizable tasks than research"* and *"LLM agents are not yet great at coordinating and delegating to other agents in real time."*

### 4.2 They aren't actually contradicting each other

| Property | Multi-agent wins | Single-thread wins |
|---|---|---|
| Decomposition | Breadth-first, independent branches | Depth-first, later steps depend on earlier |
| Side effects | **Read-only** (search, retrieval) | **Write** (code, artifacts, mutating state) |
| Output coupling | Outputs are *unioned* (more facts = better) | Outputs must *compose into one coherent artifact* |
| Implicit decisions | Few — "find facts about X" carries no style commitments | Many — every line of code encodes decisions |
| Token budget | 15x acceptable | 15x not acceptable |

**Decision rule: parallelize retrieval; serialize construction.** Cognition's failure and Anthropic's success are the same rule applied to opposite task types.

### 4.3 Third-party adjudication

**MAST, "Why Do Multi-Agent LLM Systems Fail?"** (NeurIPS 2025) — https://arxiv.org/abs/2503.13657. 1,600+ annotated traces, 7 frameworks, human inter-annotator **κ = 0.88**. 14 failure modes:

- **FC1 Specification & System Design — 44%**: step repetition 15.7%, unaware of termination conditions 12.4%, disobey task spec 11.8%
- **FC2 Inter-Agent Misalignment — 32%**: reasoning-action mismatch 13.2%, task derailment 7.4%, fail to ask for clarification 6.8%
- **FC3 Task Verification & Termination — 23.5%**: incorrect verification 9.1%, no/incomplete verification 8.2%, premature termination 6.2%

**~32% of multi-agent failures are inter-agent misalignment — failure modes that cannot exist in a single-threaded agent.** Best available quantification of Cognition's argument. Their intervention study: improved role specs +9.4%, adding verification +15.6% on ChatDev, *"but overall success rates remained low, indicating isolated fixes require systemic redesign."*

**Budget-matched comparison** — https://arxiv.org/html/2604.02460v1 — five MAS topologies (sequential, subtask-parallel, parallel-roles, debate, ensemble) vs single-agent at a *fixed global thinking-token budget*, on FRAMES + MuSiQue-4hop across four models. Single-agent leads nearly everywhere at 1,000 thinking tokens. *"Many reported MAS gains are better explained by compute and context effects than by inherent architectural superiority."* Crossover finding: **MAS only wins under context *degradation*** — decomposition helps when context contains corrupting noise, not merely when it is long.

**This reframes Anthropic's own number.** They report token usage explains 80% of variance and their multi-agent system used ~15x tokens. **Never present 90.2% without the 15x.** Pointing this out demonstrates you read past the headline — exactly the "technical judgment" the challenge tests.

### 4.4 Workflow vs agent

Anthropic's taxonomy — https://www.anthropic.com/engineering/building-effective-agents:

| Pattern | Use when (quoted) |
|---|---|
| Prompt chaining | "the task can be easily and cleanly decomposed into fixed subtasks" |
| Routing | "distinct categories that are better handled separately" |
| Parallelization (sectioning) | "the divided subtasks can be parallelized for speed" |
| Parallelization (voting) | "multiple perspectives... are needed" |
| Orchestrator-workers | "subtasks aren't pre-defined, but determined by the orchestrator" |
| Evaluator-optimizer | "clear evaluation criteria, and... iterative refinement provides measurable value" |
| Autonomous agent | "open-ended problems where it's difficult to predict the required number of steps" |

Core guidance: start with "simple prompts... and add multi-step agentic systems only when simpler solutions fall short." **Orchestrator-workers is the only multi-agent pattern Anthropic endorses** — a single decision-maker delegating bounded, read-only subtasks. OpenAI converges: *"maximize a single agent's capabilities first,"* split only on complex branching logic or tool *overlap*.

**The decision boundary is predictability of the step sequence, not task difficulty.**

### 4.5 What this means for the submission

Build single-agent. Then run **exactly one** multi-agent experiment, measure it on your eval **with tokens and cost reported**, and — if it doesn't pay for itself — remove it and write it up. That gives you:
- a changelog entry with evidence (Measured Improvement)
- the "experiment you removed" the video explicitly asks for
- a demonstration of *purposeful* design choice (the 30-point category's exact wording)
- a second Hot Take candidate

**Cost: 4–6 hours. Value: disproportionate.**

---

## 5. Reliability and reproducibility (15 pts + disqualification gate)

### 5.1 What you can and cannot promise

**Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference"** — https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/. 1000 completions from Qwen3-235B at temperature 0 → **80 unique completions**, first divergence at token 103. Key correction to the folk explanation: the forward pass *is* run-to-run deterministic (no atomic adds); the real cause is **lack of batch invariance** — kernels change reduction order as a function of batch size, and batch size is a function of *other people's traffic on the server*. `torch.mm(a[:1], b)` vs `torch.mm(a, b)[:1]` differ by 1669.25.

OpenAI's `seed` is explicitly *"best effort to sample deterministically"* with *"a small chance that responses differ even when request parameters and `system_fingerprint` match"* — https://developers.openai.com/cookbook/examples/reproducible_outputs_with_the_seed_parameter. **Anthropic has no seed parameter at all.** Dated model IDs (`claude-sonnet-4-5-20250929`) are frozen snapshots; bare aliases roll forward silently.

**Write this paragraph in your README. It converts a gate you cannot pass into one you can:**

> We do not promise bit-identical model outputs — that is impossible over a hosted endpoint, because batch composition varies with server load and inference kernels are not batch-invariant [cite]. We promise four things that are: (1) a byte-identical environment (uv.lock + pinned model snapshot IDs); (2) a byte-identical **default** run via recorded fixtures — `make eval` replays committed responses offline, needs no API key, and reproduces the published report byte-for-byte; (3) bounded live variance — N-trial pass^k with confidence intervals for the live path; (4) full trajectory artifacts for every claim.

### 5.2 The flagship artifact: offline replay

**Hash-cache wrapper around every LLM call.** Cache key = SHA-256 over canonicalized JSON of `{model_snapshot_id, prompt_template_version (git sha), rendered_messages, tool schemas, temperature, max_tokens, response_format, fixture_schema_version}`. Store `fixtures/<key>.json` with the full response body **plus `usage`, `system_fingerprint`, `latency_ms`**.

Three modes:
- `LLM_MODE=replay` (**default**): cache miss → **hard fail** with the missing key and the re-record command. Never silently hit the network.
- `LLM_MODE=record`: call live, write fixture.
- `LLM_MODE=live`: bypass.

```
make eval        # replay, no network, no key -> report/index.html + report/report.json
make eval-live   # live, requires key
make record      # regenerate fixtures/
make verify      # re-run make eval, diff report.json vs committed expected.json, exit 1 on drift
```

Commit `report/expected.json`. **`make verify` is the proof.** Prior art to cite: promptfoo's disk cache (https://www.promptfoo.dev/docs/configuration/caching/), langchain-replay (https://github.com/sixty-north/langchain-replay — replays recorded LLM *decisions* while still executing real tools), pytest-recording/vcrpy (https://til.simonwillison.net/pytest/pytest-recording-vcr — remember `filter_headers: ["authorization", "x-api-key"]`).

**4–5 hours. The single strongest reproducibility signal available.** Because fixtures store `usage`, your *cost table* reproduces offline too.

### 5.3 Cost and latency instrumentation

Anthropic `usage` gotcha: **`total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens`** — `input_tokens` alone is *not* your input total, and naive dashboards undercount badly. Cache write = 1.25x base input (5-min) or 2x (1-hour); cache read = **0.1x**. Break-even ≈ 2 reads. Below the minimum cacheable prefix, **no error is raised — caching just silently doesn't happen**; assert both cache fields are 0 to detect it.

OpenAI: **`completion_tokens_details.reasoning_tokens` are invisible but billed at the output rate** — the most common source of surprise cost.

Emit per call: `{task_id, step_idx, model_snapshot, input_tokens, cache_read, cache_write, output_tokens, reasoning_tokens, cost_usd, latency_ms, retries, tool_name}`. Commit a `PRICES` dict keyed by exact snapshot ID with a `pricing_asof` date. Report **cost/task (p50/p95), latency/task (p50/p95), tokens/task, cache hit rate, steps/task.** ~2 hours.

### 5.4 Environment and the clean-clone test

- `uv.lock` committed. Use **`uv sync --locked`** (re-resolves and *fails* if the lockfile is stale) not `--frozen` (installs silently from a stale lockfile). Pin `.python-version`.
- Pin dated model snapshot IDs in one config module; assert at startup; print in the report header.
- Dockerfile as the fallback path. Devcontainer is optional polish.

**The failure that actually disqualifies people is not missing Docker.** It is `make demo` hitting the network, crashing on a missing `OPENAI_API_KEY`, or a fixture path that only exists on your laptop. **Budget the last hour to clone into a fresh directory, unset every env var, turn off wifi, and run `make demo`. Do it twice.**

### 5.5 Failure taxonomy and resilience

Tag every failed eval run with a **MAST failure-mode code** (FM-1.3 step repetition, FM-2.6 reasoning-action mismatch, FM-3.2 no/incomplete verification, etc.) and chart the distribution. Cheap (2–3h), citable, instantly reads as rigor, and gives you a principled "what I'd fix next."

Resilience essentials — collectively they mean "zero crashed runs":
- Exponential backoff **with jitter** (the omitted part).
- **Idempotency keys on tool calls**: `hash(run_id, step_idx, tool_name, canonical_args)`; side-effecting tools no-op on repeat. Also what makes replay safe.
- **Budget circuit breakers**: hard caps on max_steps, max_tokens, max_cost_usd, wall-clock — with the abort reason written into the trace. MAST FM-1.5 (unaware of termination conditions, 12.4%) is literally this.
- Typed tool errors returned *to the model* as structured content, not raised as exceptions that kill the run.

### 5.6 Human approval gates (rule-book requirement)

Ground rule 04 requires consequential actions be sandboxed/simulated with human approval. Implement it and **make it visible** — free points in both Reproducibility and End-to-End Quality. Pattern: checkpoint state, `interrupt()` with a payload containing enough evidence for the reviewer to decide, resume on command. **Interrupt on irreversible, high-blast-radius actions only, at business decision boundaries** — not every step. 2–3h.

---

## 6. Trajectory capture

### 6.1 Standards
- **OpenTelemetry GenAI semconv** is the de-jure standard-in-progress. Span tree: `invoke_agent` → `chat` + `execute_tool`. **Every `gen_ai.*` attribute still carries a "Development" badge — none are Stable.** Pin the convention version you build against.
- **OpenInference (Arize)** is the de-facto standard by instrumentation coverage (35+ Python instrumentors). Span kinds: LLM, CHAIN, TOOL, AGENT, RETRIEVER. Emits normal OTLP.
- **Pragmatic move:** emit OTel spans and set both attribute sets where they differ (a dict merge, ~1h). Note the choice in your README. Saying accurately that *neither* has won is itself a competence signal.

### 6.2 What the judge can actually open

| Tool | Local, no account | Static artifact | Verdict |
|---|---|---|---|
| **Your own JSONL + self-contained HTML** | Yes | Yes, double-click | **Primary. Build this.** |
| **Inspect `view bundle`** | Yes | Yes, static site | **Best off-the-shelf option** |
| Arize Phoenix | Yes (`phoenix serve`) | Parquet TraceDataset | Good dev-loop |
| otel-gui | Yes (one docker cmd, MIT) | OTLP JSON import/export | Sleeper pick |
| Langfuse | Yes but heavy (Postgres+ClickHouse+Redis+MinIO) | Needs your server | Dev loop only |
| LangSmith / Braintrust / Weave | **No** | Behind login | **Don't** |

### 6.3 Design rules for a human-readable trajectory

A judge gives you 3–5 minutes. Published guidance is thin here — that's the opportunity.

1. **Above the fold, no scrolling:** task, verdict, cost, latency, step count, model snapshot, fixture hash, `replay|live` badge. If they read only this, they can score you.
2. **One line per step, collapsed by default:** `#3 · tool:search_docs · 412ms · $0.0021 · ok`. Expand for full args/results.
3. **Show the decision, not just the text.** What the agent believed, what it chose, why, what came back. Reasoning-action mismatch (13.2% of MAST failures) is invisible otherwise.
4. **Diff-first for failures**: expected vs actual side by side, failing assertion highlighted, MAST code labelled.
5. **Deterministic rendering**: same JSONL in → byte-identical HTML out (sorted keys, no render timestamps, **no CDN assets** — inline all CSS/JS so it works from `file://` offline). Otherwise `make verify` is noise.
6. **Redact by construction** — the renderer strips secret-shaped strings, so a leak is structurally impossible.

Anthropic's acceptance criterion applies to how a judge reads your traces: **"Failures should seem fair: it's clear what the agent got wrong and why."**

### 6.4 Free win: your own build transcripts

The submission requires "representative trajectories for every agent you used." Claude Code writes every session to `~/.claude/projects/<mangled-cwd>/<uuid>.jsonl`. Two one-command renderers produce committable static HTML:
- `uvx claude-code-log@latest` — https://github.com/daaain/claude-code-log — self-contained HTML with **per-message token/cost display**, filters, `--detail {user-only,minimal,low,high,full}`
- `uvx claude-code-transcripts` — https://github.com/simonw/claude-code-transcripts — paginated, mobile-friendly, `--gist` publishing. Example output: https://static.simonwillison.net/static/2025/claude-code-microjs/index.html

Commit `transcripts/` and link from the README. **~1 hour**, satisfies a required deliverable, doubles as evidence of process.

---

## 7. Flagged: fashionable but weakly supported

1. **Reflection / self-critique loops with no external signal.** Actively negative (§1.1). The most common hackathon reflex; the best thing to publicly kill.
2. **Multi-agent debate / "society of minds."** Underperforms cost-matched self-consistency (83.0 vs 88.2 at 9 responses). "Debate hacking" degenerates into cheap talk — https://arxiv.org/abs/2510.20963. Demos well, doesn't work.
3. **Multi-agent as a default architecture.** 90.2% comes with 15x tokens, on a non-reproducible internal eval, caveated by Anthropic for coding. Budget-matched work finds single-agent ≥ MAS across five topologies.
4. **"Our judge agrees with humans 85% of the time."** Raw agreement exceeded chance-corrected κ by 33.8–41.3 points in practice.
5. **5-point / 1-10 Likert judge scores.** Ubiquitous in tutorials, indefensible under questioning.
6. **Pairwise-is-always-better.** Contested since 2025: 35% preference-flip under distractors vs 9% pointwise.
7. **Off-the-shelf metric suites (RAGAS faithfulness, G-Eval) as primary evidence.** RAGAS correlates with human judgment at ~0.55 harmonic mean; G-Eval hits Spearman 0.514 on SummEval. Fine as an *exploration* tool; not a scoreboard.
8. **High self-consistency / test-retest as a quality claim.** The consistency-bias paradox.
9. **Lowering temperature to "reduce eval noise."** Miller: can *triple* irreducible variance while appearing to help.
10. **Mode-aggregating k repeats into one label.** Intuitive, wrong — broken CI coverage except at k=2.
11. **Exact-match trajectory scoring.** Punishes valid alternate routes. Use precision/recall, or grade outcomes.
12. **Vector RAG / GraphRAG as the default retrieval layer.** Anthropic's own guidance prefers agentic grep. Choosing grep and *explaining why* is a stronger claim than adding embeddings.
13. **Structured-output field ordering.** Constrained decoding can degrade reasoning — and **if the answer field precedes the reasoning field in your schema, the model commits before thinking.** Order `reasoning` before `verdict` in every judge and agent schema. Free, one line.
14. **The "~80 tokens / ~5,000 tokens" Agent Skills tier figures.** Widely circulated, **not from Anthropic** (which specifies no token limits). Don't cite them.
15. **"Filesystem as memory."** Strong practitioner support (Manus, Anthropic), thin measurement (LangChain's dedicated post has zero benchmarks). Build it — cheap and demos beautifully — but call it a design pattern, not a measured optimization.

---

## 8. Prioritized shortlist — highest score-per-hour for ~40 working hours

### Tier 0 — Gate (do first, ~8h). Skipping any can zero the submission.

| # | Item | h | Category |
|---|---|---|---|
| 1 | `make demo` runs offline, no API key, <60s. Tested on a clean clone with wifi off. | 3 | Repro (gate) |
| 2 | Hash-cache fixture layer: `replay` (default, hard-fail on miss) / `record` / `live` | 4 | Repro (gate) |
| 3 | `uv.lock` + `--locked`, `.python-version`, pinned dated model snapshot IDs asserted at startup | 1 | Repro |

### Tier 1 — Highest score-per-hour (~14h). Where the 30 + 15 points live.

| # | Item | h | Category | Why |
|---|---|---|---|---|
| 4 | **External-signal verification loop** (tests / linter / schema / state-diff the agent runs itself) | 3 | Engineering | SWE-agent +3.0; MAST FC3 = 23.5% of failures; the Hot Take's proof |
| 5 | **12–15 eval cases with a held-out split** + 1 hard case, written by you from real failures | 3 | Measured Improvement | Anthropic's explicit floor is 20–50; the rubric asks 10+ |
| 6 | **Binary atomic rubric**, one isolated judge call per criterion, reference answer supplied, `UNKNOWN` escape hatch, `reasoning` before `verdict` in the schema | 2 | Measured Improvement | 70%→15% error reduction from reference-guided grading |
| 7 | **Judge validation**: hand-label 30–50, report TPR/TNR + 2×2 confusion matrix + Cohen's κ + bias-corrected estimate via `judgy` | 2 | Measured Improvement | Almost nobody does this. Maximum differentiation per hour. |
| 8 | **Strong baseline including retry** alongside the naive one; cost + latency for both | 2 | Measured Improvement | "AI Agents That Matter": retry alone matches SOTA agents at 1/50th cost |
| 9 | **k=5 repeats; report pass@k AND pass^k**, paired differences, Wilson/Clopper-Pearson CIs, exact McNemar, and your **Minimum Detectable Effect** | 2 | Measured Improvement | pass^k is the most sophisticated-looking metric available |

### Tier 2 — Legible engineering (~10h)

| # | Item | h | Why |
|---|---|---|---|
| 10 | **Actionable tool errors + poka-yoke argument design** | 2 | Highest-ROI single item in the tool literature |
| 11 | **Windowed reads + last-N observations instead of full history** | 3 | SWE-agent: full file −5.3, full history −3.0. Contrarian and citable. |
| 12 | **Structured note-taking (`NOTES.md`) + recitation (`todo.md`)** | 3 | Judges can *read the agent's reasoning trail* |
| 13 | **Cost/latency/token table** with p50/p95 + cache hit rate; accuracy-vs-cost Pareto plot | 2 | The submission template already has these rows |

### Tier 3 — The differentiators (~10h)

| # | Item | h | Why |
|---|---|---|---|
| 14 | **Self-adjudicated multi-agent experiment**: build it, measure it with tokens, remove it, write it up | 5 | Satisfies "one experiment you removed" AND demonstrates *purposeful* choice |
| 15 | **Self-contained static HTML trajectory report** from your JSONL (deterministic render, inlined assets, MAST codes, diff-first failures) + `make verify` byte-diff | 4 | Top judge-legible artifact. Works from `file://` with no network. |
| 16 | **Human approval gate** on any consequential action, with the approval payload visible in the trace | 1 | Ground rule 04 compliance; free End-to-End Quality points |

### Tier 4 — Polish if hours remain (~4h)

| # | Item | h |
|---|---|---|
| 17 | MAST failure-mode tagging + distribution chart | 2 |
| 18 | `claude-code-log` export of your own build sessions, linked from README | 1 |
| 19 | KV-cache-stable prompt prefix (no timestamps, deterministic JSON) | 1 |
| 20 | REPRODUCIBILITY.md with the "what we promise" paragraph citing Thinking Machines | 0.5 |
| 21 | Constraint pinning across compaction (~47 tokens, restores 0% violation) | 1 |

### The four things most likely to separate you from the field
1. **A judge validated against your own hand labels** — confusion matrix, Cohen's κ, bias-corrected estimate with a CI.
2. **pass^k reported next to pass@1**, plus a stated Minimum Detectable Effect.
3. **An offline default path** — `make eval` reproduces the published report byte-for-byte with no API key, no network, no cost, in under a minute.
4. **A measured removal** — the multi-agent (or self-critique) experiment you built, measured, and deleted, with the token cost shown.

### Two things to consciously not do
- Do not add a bare self-reflection loop and call it verification. Add an external signal or add nothing.
- Do not make a judge sign up for anything, run a six-container stack, or spend money to see your result.

---

## Sources
[Huang et al., LLMs Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798) · [Kamoi et al.](https://arxiv.org/html/2406.01297v3) · [The Self-Correction Illusion](https://arxiv.org/pdf/2606.05976) · [CRITIC](https://arxiv.org/abs/2305.11738) · [AlphaCodium](https://arxiv.org/abs/2401.08500) · [Jason Wei, Asymmetry of Verification](https://www.jasonwei.net/blog/asymmetry-of-verification-and-verifiers-law) · [SpecBench](https://arxiv.org/html/2605.21384v1) · [Verification Horizon](https://www.emergentmind.com/papers/2606.26300) · [Anthropic, Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) · [Miller, Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640) · [Kapoor et al., AI Agents That Matter](https://arxiv.org/abs/2407.01502) · [Zheng et al., Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [Position Bias in Pairwise LLM-as-a-Judge](https://arxiv.org/html/2406.07791v5) · [Reliability without Validity](https://arxiv.org/html/2606.19544v1) · [Agreement Metrics for LLM-as-Judge](https://arxiv.org/html/2606.00093v1) · [Pairwise or Pointwise?](https://arxiv.org/abs/2504.14716) · [Self-Preference Bias of LLM Judges](https://arxiv.org/abs/2604.22891) · [Hamel Husain, LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/) · [Using LLM-as-a-Judge](https://hamel.dev/blog/posts/llm-judge/) · [judgy](https://github.com/ai-evals-course/judgy) · [evals-skills](https://github.com/ai-evals-course/evals-skills) · [Inspect AI](https://inspect.aisi.org.uk/) · [Inspect metrics](https://inspect.aisi.org.uk/metrics.html) · [Inspect log viewer](https://inspect.aisi.org.uk/log-viewer.html) · [promptfoo](https://www.promptfoo.dev/docs/configuration/outputs/) · [τ-bench](https://arxiv.org/abs/2406.12045) · [Indeed, Bootstrap CIs for LLM Evaluation](https://engineering.indeedblog.com/blog/2026/07/bootstrap-confidence-intervals-for-llm-evaluation/) · [Stats for LLM Evals](https://statsforevals.com/resources.html) · [Anthropic, Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) · [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) · [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) · [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) · [Claude Code best practices](https://code.claude.com/docs/en/best-practices) · [Claude Agent SDK](https://claude.com/blog/building-agents-with-the-claude-agent-sdk) · [Chroma, Context Rot](https://www.trychroma.com/research/context-rot) · [Lost in the Middle](https://arxiv.org/abs/2307.03172) · [SWE-agent ACI](https://arxiv.org/abs/2405.15793) · [Manus, Context Engineering](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) · [Cognition, Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents) · [Anthropic, Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) · [MAST](https://arxiv.org/abs/2503.13657) · [Single-Agent vs MAS at Equal Token Budgets](https://arxiv.org/html/2604.02460v1) · [When and Why Does Multi-Agent Debate Fail?](https://arxiv.org/abs/2510.20963) · [If MAD is the Answer, What is the Question?](https://arxiv.org/abs/2502.08788) · [Governance Decay](https://arxiv.org/html/2606.22528v2) · [OpenAI, Practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) · [Thinking Machines, Defeating Nondeterminism](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) · [OpenAI seed cookbook](https://developers.openai.com/cookbook/examples/reproducible_outputs_with_the_seed_parameter) · [Claude prompt caching](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching) · [pytest-recording TIL](https://til.simonwillison.net/pytest/pytest-recording-vcr) · [langchain-replay](https://github.com/sixty-north/langchain-replay) · [OTel GenAI agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md) · [OpenInference](https://arize-ai.github.io/openinference/) · [claude-code-log](https://github.com/daaain/claude-code-log) · [claude-code-transcripts](https://github.com/simonw/claude-code-transcripts) · [Self-Consistency Is Losing Its Edge](https://arxiv.org/html/2511.00751)
