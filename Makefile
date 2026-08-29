PYTHON ?= python3
IMAGE ?= crucible-sandbox:phase1

.PHONY: sandbox probe harvest split validate-candidates verify-split test

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

verify-split:
	$(PYTHON) -m scripts.verify_split

test:
	docker run --rm --entrypoint /opt/venvs/pallets--click--head/bin/python \
		-v "$(CURDIR):/workspace:ro" -w /workspace $(IMAGE) -m pytest -q -p no:cacheprovider
