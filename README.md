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
- **Automatic Testbench Creation** — Comprehensive testbenches with clock gen, reset, directed tests, and assertions
- **Icarus Verilog Simulation** — Compile and simulate entirely from the CLI
- **Autonomous Bug Correction Loop** — AI analyzes simulation failures and iteratively fixes the RTL (up to 3 attempts)
- **YAML-Based Prompt Templates** — Easily customize the AI prompts in `config/prompts.yaml`
- **Rich CLI Output** — Syntax-highlighted Verilog output with status reporting

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Icarus Verilog](http://iverilog.icarus.com/) (`brew install icarus-verilog` on macOS)
- An OpenAI API key (optional — runs in mock mode without one)

### Installation

```bash
git clone https://github.com/KushalPitaliya/ai-eda-playground.git
cd ai-eda-playground
pip install -r requirements.txt

# Optional: set your OpenAI API key
export OPENAI_API_KEY="sk-..."
```

### Usage

```bash
# Check that Icarus Verilog is installed
python -m src.cli check

# Generate a Verilog module from a description
python -m src.cli generate "4-bit up counter with enable" \
  --name counter_4bit \
  -i clk -i rst_n -i enable \
  -o "count[3:0]"
```

---

## Project Structure

```
ai-eda-playground/
├── config/
│   └── prompts.yaml          # AI prompt templates
├── examples/
│   └── counter.yaml           # Example module specification
├── src/
│   ├── __init__.py
│   ├── generator.py           # LLM-powered Verilog generator
│   ├── simulator.py           # Icarus Verilog compile & simulate
│   ├── pipeline.py            # Generate → Simulate → Correct orchestrator
│   └── cli.py                 # CLI interface (Click + Rich)
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Example

Using the included counter example (`examples/counter.yaml`):

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

## Roadmap

- [ ] Web frontend (Next.js)
- [ ] Waveform viewer integration
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
