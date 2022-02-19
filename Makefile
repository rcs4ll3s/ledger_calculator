define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("	%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

PIP := pip install -r
PROJECT_NAME := ampla
PYTHON_VERSION := 3.9.1
VENV_NAME := $(PROJECT_NAME)-$(PYTHON_VERSION)


.DEFAULT: help
.PHONY: help clean setup-dev test

help: ## List all available commands
	@echo "Usage: make <command> \n"
	@echo "options:"
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.create-venv: ## Create virtual environment using pyenv
	pyenv install -s $(PYTHON_VERSION)
	pyenv uninstall -f $(VENV_NAME)
	pyenv virtualenv $(PYTHON_VERSION) $(VENV_NAME)
	pyenv local $(VENV_NAME)

.pip:
	pip install pip --upgrade

deps: .pip  ## Install all requirements
	$(PIP) requirements.txt

setup-dev: .create-venv deps ## Create virtual environment, install requirements requirements.txt

all: setup-dev clean ## Run setup-dev + clean

.clean-build: ## Remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

.clean-pyc: ## Remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.clean-test: ## Remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr reports/
	rm -fr .pytest_cache/

clean: .clean-build .clean-pyc .clean-test ## Remove all build, test, coverage and Python artifacts

test:
	python -m unittest tests.test_cli

format:
	black -l 79 --skip-string-normalization domain
