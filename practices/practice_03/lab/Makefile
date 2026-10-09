.PHONY: install test build-models build-agent build-experiment verify-models experiment report
install:
	@python3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'; print('Standard library only: ready')"
test: install
	$(MAKE) -C demo test

# Build local Ollama models from Modelfiles
build-models: build-agent build-experiment

build-agent:
	@which ollama >/dev/null 2>&1 || { echo "Ollama CLI not found. Install Ollama first: https://ollama.com"; exit 1; }
	ollama create itmo-agent -f Modelfile.agent
	@echo "Built model: itmo-agent"

build-experiment:
	@which ollama >/dev/null 2>&1 || { echo "Ollama CLI not found. Install Ollama first: https://ollama.com"; exit 1; }
	ollama create itmo-experiment -f Modelfile
	@echo "Built model: itmo-experiment"

# Verify models exist locally
verify-models:
	@which ollama >/dev/null 2>&1 || { echo "Ollama CLI not found. Install Ollama first: https://ollama.com"; exit 1; }
	@ollama show itmo-agent >/dev/null 2>&1 || { echo "Model itmo-agent not found. Run: make build-agent"; exit 1; }
	@ollama show itmo-experiment >/dev/null 2>&1 || { echo "Model itmo-experiment not found. Run: make build-experiment"; exit 1; }
	@echo "Models present."

# Run a pair of controlled experiments (baseline vs system prompt)
experiment: verify-models
	@mkdir -p exp
	python3 experiment.py --mode baseline --model itmo-experiment --output exp/baseline.json
	python3 experiment.py --mode system --model itmo-experiment --output exp/system.json
	@echo "Experiment results saved under ./exp"

# Generate REPORT.md with local environment and model info (read-only usage)
report:
	python3 gen_report.py --output REPORT.md
