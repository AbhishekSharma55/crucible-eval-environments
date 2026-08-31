PYTHON ?= python3
IMAGE ?= crucible-sandbox:phase1

.PHONY: sandbox probe harvest split validate-candidates validate-rescue sample baselines review-set review-labels review-metrics solvability-set solvability verify-split phase3-sandbox validate-b sample-b baselines-b replay-b agent-c replay-c report-c test

sandbox:
	docker build --pull --no-cache --progress=plain -t $(IMAGE) .

probe:
	$(PYTHON) -m scripts.probe --image $(IMAGE) --workers 3

harvest:
	env -u GITHUB_TOKEN $(PYTHON) -m scripts.harvest

split: harvest
	$(PYTHON) -m scripts.verify_split

validate-candidates:
	$(PYTHON) -m scripts.validate_candidates --image $(IMAGE) --workers 3

validate-rescue:
	$(PYTHON) -m scripts.validate_rescue_candidates --image $(IMAGE) --workers 3

sample:
	$(PYTHON) -m scripts.sample_phase2

baselines:
	$(PYTHON) -m scripts.run_baselines all

review-set:
	$(PYTHON) -m scripts.prepare_leakage_review

review-labels:
	@test -n "$(LABELER)" || (echo "usage: make review-labels LABELER='your identity'" && exit 2)
	$(PYTHON) -m scripts.review_leakage --labeler "$(LABELER)"

review-metrics:
	$(PYTHON) -m scripts.leakage_metrics

solvability-set:
	$(PYTHON) -m scripts.prepare_solvability

solvability:
	$(PYTHON) -m scripts.run_solvability

verify-split:
	$(PYTHON) -m scripts.verify_split

phase3-sandbox:
	docker build -f Dockerfile.phase3 -t crucible-sandbox:phase3 .

validate-b:
	$(PYTHON) -m scripts.validate_phase3_candidates --image crucible-sandbox:phase3 --workers 6

sample-b:
	$(PYTHON) -m scripts.sample_phase3

baselines-b:
	$(PYTHON) -m scripts.run_phase3_baselines all --image crucible-sandbox:phase3

replay-b:
	env -u OPENROUTER_API_KEY $(PYTHON) -m scripts.run_phase3_baselines all --fixture-mode replay --image crucible-sandbox:phase3

agent-c:
	$(PYTHON) -m scripts.run_phase4_agent --fixture-mode replay --rollout-plan subset --image crucible-sandbox:phase3

replay-c:
	env -u OPENROUTER_API_KEY $(PYTHON) -m scripts.run_phase4_agent --fixture-mode replay --rollout-plan subset --image crucible-sandbox:phase3

report-c:
	$(PYTHON) -m scripts.report_phase4

test:
	docker run --rm --entrypoint /opt/venvs/pallets--click--head/bin/python \
		-v "$(CURDIR):/workspace:ro" -w /workspace $(IMAGE) -m pytest -q -p no:cacheprovider
