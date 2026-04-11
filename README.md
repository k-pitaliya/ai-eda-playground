# 🔬 AI-Driven EDA Playground

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Icarus Verilog](https://img.shields.io/badge/Simulator-Icarus%20Verilog-green.svg)](http://iverilog.icarus.com/)

A browser-based/CLI RTL design environment that uses AI to close the design-verification loop. Describe a module in natural language → generate Verilog → auto-generate testbenches → simulate with Icarus Verilog → auto-correct bugs.

---

## Architecture

```
Natural Language Description
        ↓
 ┌──────────────┐
 │ AI Generator  │ → Verilog Module (.v)
 └──────┬───────┘
        ↓
 ┌──────────────┐
 │ TB Generator  │ → Testbench (.v)
 └──────┬───────┘
        ↓
 ┌──────────────┐
 │ Icarus Verilog│ → Simulation
 └──────┬───────┘
        ↓
   Pass? → Done ✅
   Fail? → [Bug Corrector] → Loop back ↑ (max 3 attempts)
```

---

## Features

- **LLM-Powered Verilog Generation** — Describe what you want in plain English, get synthesizable RTL
- **Dual LLM Backends** — Supports both OpenAI (GPT-4) and Anthropic (Claude), with auto-detection
- **OpenRouter / Custom API Support** — Use any OpenAI-compatible endpoint (OpenRouter, Ollama, vLLM, etc.)
- **Automatic Testbench Creation** — Comprehensive testbenches with clock gen, reset, directed tests, and assertions
- **Icarus Verilog Simulation** — Compile and simulate entirely from the CLI or Web UI
- **Autonomous Bug Correction Loop** — AI classifies errors, tracks correction history, and iteratively fixes the RTL (up to 3 attempts)
- **VCD Waveform Viewer** — ASCII (terminal) and SVG (browser) waveform rendering from VCD files
- **Gradio Web UI** — Full browser-based interface with example presets and tabbed output
- **YAML-Based Prompt Templates** — Easily customize the AI prompts in `config/prompts.yaml`
- **Rich CLI Output** — Syntax-highlighted Verilog output with status reporting

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Icarus Verilog](http://iverilog.icarus.com/) (`brew install icarus-verilog` on macOS)
- An OpenAI or Anthropic API key (optional — runs in mock mode without one)

### Installation

```bash
git clone https://github.com/KushalPitaliya/ai-eda-playground.git
cd ai-eda-playground

# Using venv (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Or install as a package
pip install -e ".[all]"

# Optional: set your API keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Usage

```bash
# Check that tools and API keys are configured
python -m src.cli check

# ── Web UI (recommended) ──────────────────────────────────────────────────────
./launch_ui.sh                    # opens browser at http://127.0.0.1:7860
# or
python -m src.cli webui

# ── CLI ───────────────────────────────────────────────────────────────────────
# Generate a Verilog module from a description
python -m src.cli generate "4-bit up counter with enable" \
  --name counter_4bit \
  -i clk -i rst_n -i enable \
  -o "count[3:0]" \
  --backend auto

# View VCD waveforms in the terminal
python -m src.cli waveform path/to/dump.vcd
```

### Using OpenRouter or Custom API Endpoints

The tool works with any OpenAI-compatible API via `--base-url` and `--model`:

```bash
# Set env vars (or pass via CLI flags)
export OPENAI_API_KEY="sk-or-v1-..."
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"

# Use a free model on OpenRouter
python -m src.cli generate "4-bit counter" \
  -n cnt4 -i clk -i rst_n -o "count[3:0]" \
  --backend openai \
  --model "google/gemma-4-26b-a4b-it:free"

# Or use CLI flags directly
python -m src.cli generate "D flip-flop" \
  --backend openai \
  --base-url "https://openrouter.ai/api/v1" \
  --model "openai/gpt-4"
```

Env vars: `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_API_KEY`

---

## Project Structure

```
ai-eda-playground/
├── config/
│   └── prompts.yaml           # AI prompt templates (generation, testbench, correction)
├── examples/
│   └── counter.yaml           # Example module specification
├── src/
│   ├── __init__.py
│   ├── __main__.py            # python -m src entry point
│   ├── cli.py                 # CLI interface (Click + Rich)
│   ├── generator.py           # LLM-powered Verilog generator (OpenAI + Anthropic)
│   ├── simulator.py           # Icarus Verilog compile & simulate runner
│   ├── pipeline.py            # Generate → Simulate → Correct orchestrator
│   ├── waveform.py            # VCD waveform viewer (ASCII + SVG)
│   └── webui.py               # Gradio Web UI
├── tests/
│   ├── conftest.py            # Shared fixtures
│   ├── test_generator.py      # Generator unit tests
│   ├── test_simulator.py      # Simulator unit tests
│   ├── test_waveform.py       # Waveform renderer tests
│   └── test_pipeline.py       # Pipeline integration tests
├── pyproject.toml             # PEP 621 project metadata + packaging
├── requirements.txt           # Pinned dependencies
├── launch_ui.sh               # One-command Web UI launcher
├── LICENSE
└── README.md
```

---

## Example

```bash
python -m src.cli generate \
  "4-bit synchronous up counter with enable and active-low reset" \
  --name counter_4bit \
  -i clk -i rst_n -i enable \
  -o "count[3:0]"
```

The pipeline will:

1. **Generate** a synthesizable `counter_4bit.v` module
2. **Create** a self-checking testbench `tb_counter_4bit.v`
3. **Compile & simulate** with Icarus Verilog
4. **Auto-correct** any simulation errors (up to 3 iterations)

---

## Running Tests

```bash
# From the project root
python -m pytest tests/ -v
```

---

## Roadmap

- [x] Gradio Web UI
- [x] VCD Waveform Viewer (ASCII + SVG)
- [x] Anthropic/Claude backend support
- [x] Structured bug correction with error classification
- [ ] Multi-file project support
- [ ] Synthesis targeting (Yosys)
- [ ] SystemVerilog support
- [ ] CI/CD pipeline for automated regression

---

## Author

**Kushal Pitaliya**

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
