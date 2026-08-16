.PHONY: format lint test tests integration_test integration_tests build help

.DEFAULT_GOAL := help

.EXPORT_ALL_VARIABLES:
UV_FROZEN = true

######################
# TESTING
######################

TEST_FILE ?= tests/unit_tests/
PYTEST_EXTRA ?=

integration_test integration_tests: TEST_FILE=tests/integration_tests/

test: ## Run unit tests
test tests:
	uv run --group test pytest -vvv $(PYTEST_EXTRA) --disable-socket --allow-unix-socket $(TEST_FILE)

integration_test: ## Run integration tests (requires a running OpenSandbox server)
integration_test integration_tests:
	uv run --group test pytest -vvv --timeout 120 $(TEST_FILE)

######################
# LINTING AND FORMATTING
######################

PYTHON_FILES=langchain_opensandbox tests

lint: ## Run linters
lint:
	uv run --all-groups ruff check $(PYTHON_FILES)
	uv run --all-groups ruff format $(PYTHON_FILES) --diff

format: ## Run code formatters
format:
	uv run --all-groups ruff format $(PYTHON_FILES)
	uv run --all-groups ruff check --fix $(PYTHON_FILES)

######################
# BUILD
######################

build: ## Build the distribution
	uv build

######################
# HELP
######################

help: ## Show this help message
	@echo "Usage: make [target] [TEST_FILE=path/to/tests/]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
