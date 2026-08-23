# Sensors of this repository. The templates ship a richer version; here only what
# there is to measure: a bootstrap with no dependencies and no install step.
.DEFAULT_GOAL := help
.PHONY: help test fixtures

help:  ## List the targets
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

test:  ## Golden tests: greenfield, brownfield, generator ownership
	python3 -m unittest discover -s tests -v

fixtures:  ## Bootstrap both fixtures into /tmp to inspect the output by hand
	@rm -rf /tmp/harness-fixture-new /tmp/harness-fixture-existing
	@mkdir -p /tmp/harness-fixture-new /tmp/harness-fixture-existing
	@printf 'node_modules/\n' > /tmp/harness-fixture-existing/.gitignore
	@printf '.PHONY: test\ntest:\n\tnpm test\n' > /tmp/harness-fixture-existing/Makefile
	@printf '# Projeto\n' > /tmp/harness-fixture-existing/CLAUDE.md
	python3 scripts/init-project.py /tmp/harness-fixture-new
	python3 scripts/init-project.py /tmp/harness-fixture-existing
