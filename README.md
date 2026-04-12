# 🔬 AI-Driven EDA Playground

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Icarus Verilog](https://img.shields.io/badge/Simulator-Icarus%20Verilog-green.svg)](http://iverilog.icarus.com/)
[![CI](https://github.com/KushalPitaliya/ai-eda-playground/actions/workflows/ci.yml/badge.svg)](https://github.com/KushalPitaliya/ai-eda-playground/actions)
[![Tests](https://img.shields.io/badge/Tests-73%20passing-brightgreen.svg)](#testing)

An AI-powered RTL design environment (CLI + Web UI) that closes the design-verification loop. Describe a digital circuit in plain English → generate synthesizable Verilog → auto-generate self-checking testbenches → simulate with Icarus Verilog → auto-correct bugs — all in one command.

> 📖 **For a complete deep-dive into the tool's internals and how to build something like this from scratch, see [GUIDE.md](GUIDE.md).**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **🧠 LLM-Powered RTL Generation** | Describe what you want in plain English, get synthesizable Verilog |
| **🔄 Dual LLM Backends** | Supports OpenAI (GPT-4) and Anthropic (Claude), with auto-detection |
| **🌐 OpenRouter / Custom API** | Use any OpenAI-compatible endpoint (OpenRouter, Ollama, vLLM, etc.) |
| **🧪 Auto Testbench Creation** | Self-checking testbenches with clock gen, reset, directed tests, assertions |
| **⚡ Icarus Verilog Simulation** | Compile and simulate from CLI or Web UI |
| **🔧 Autonomous Bug Correction** | AI classifies errors, tracks history, and iteratively fixes RTL (up to 3 cycles) |
| **📊 VCD Waveform Viewer** | ASCII (terminal) and SVG (browser) waveform rendering |
| **🔬 Yosys Synthesis** | Gate-level synthesis, cell counts, resource usage, netlist export |
| **🏗️ Multi-Module Design** | Hierarchical designs: top module + submodules (e.g. full_adder = 2×half_adder) |
| **🖥️ Gradio Web UI** | Full browser interface with example presets and tabbed output |
| **📝 YAML Prompt Templates** | Easily customize AI prompts in `config/prompts.yaml` |
| **🎨 Rich CLI Output** | Syntax-highlighted Verilog with color-coded status reporting |
| **🔌 Mock Mode** | Full offline mode — generates valid Verilog without API calls |

---

## 🏗️ Architecture

```
  "4-bit counter with enable"     ← Natural language input
           │
           ▼
  ┌─────────────────┐
  │  VerilogGenerator│──→ LLM (GPT-4 / Claude / Mock)
  │  (generator.py)  │
  └────────┬────────┘
           │ ① Module RTL    ② Testbench
           ▼
  ┌─────────────────┐
  │   Simulator      │──→ iverilog -g2012 → vvp
  │  (simulator.py)  │
  └────────┬────────┘
           │ ③ Simulation result
           ▼
  ┌─────────────────┐
  │  EDA_Pipeline    │──→ Error classification + correction history
  │  (pipeline.py)   │     ↻ Up to 3 fix cycles
  └────────┬────────┘
           │ ④ Yosys synthesis (optional)
           ▼
  ┌─────────────────┐
  │   Synthesizer    │──→ yosys: synth → stat -json
  │  (synthesizer.py)│     Gate counts, cell types, netlist
  └────────┬────────┘
           │ ⑤ PipelineResult
           ▼
  ┌─────────────────┐
  │  Output Layer    │──→ CLI (Rich) / Web UI (Gradio) / Waveform (SVG/ASCII)
  └─────────────────┘
```

### Module Dependency Graph

```
cli.py ─────────┐
                ├──→ pipeline.py ──→ generator.py ──→ LLM APIs / Mock
webui.py ───────┘         │                │
                          ├──→ simulator.py ──→ iverilog + vvp
                          ├──→ synthesizer.py ──→ yosys
                          └──→ waveform.py ──→ vcdvcd
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Required | Install |
|------|----------|---------|
| Python 3.11+ | ✅ | [python.org](https://www.python.org/) |
| Icarus Verilog | ✅ | `brew install icarus-verilog` (macOS) / `apt install iverilog` (Linux) |
| Yosys | Optional | `brew install yosys` (macOS) / `apt install yosys` (Linux) — for synthesis |
| OpenAI or Anthropic API key | Optional | Runs in mock mode without one |

### Installation

```bash
git clone https://github.com/KushalPitaliya/ai-eda-playground.git
cd ai-eda-playground

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (pick one)
pip install -r requirements.txt          # All dependencies
pip install -e ".[all]"                  # Editable install with all extras
pip install -e "."                       # Core only (no Web UI or waveforms)

# Optional: set API keys
export OPENAI_API_KEY="sk-..."           # For GPT-4
export ANTHROPIC_API_KEY="sk-ant-..."    # For Claude
```

### Verify Setup

```bash
python -m src.cli check
```

```
┌─────────────────────────────────────┐
│ ✅ Icarus Verilog    installed       │
│ ✅ Yosys             installed       │
│ ✅ OPENAI_API_KEY    configured      │
│ ❌ ANTHROPIC_API_KEY not set         │
└─────────────────────────────────────┘
```

---

## 💻 Usage

### Web UI (Recommended)

```bash
./launch_ui.sh
# or
python -m src.cli webui --port 7860
```

Opens at **http://127.0.0.1:7860** with:
- Input form for description, module name, ports
- Backend selection (auto / OpenAI / Anthropic)
- Multi-Module accordion for hierarchical designs
- 4 example presets (Counter, FSM, Flip-Flop, Shift Register)
- Tabbed output: Status → Module → Testbench → Simulation → Waveform → Synthesis
- Standalone VCD file upload for waveform viewing

### CLI

```bash
# Generate a 4-bit counter (uses mock mode if no API key)
python -m src.cli generate "4-bit up counter with enable" \
  --name counter_4bit \
  -i clk -i rst_n -i enable \
  -o "count[3:0]"

# Generate a multi-module hierarchical design
python -m src.cli multimodule "Full adder from half adders" \
  --name full_adder \
  -i a -i b -i cin \
  -o sum -o cout

# Synthesize existing Verilog with Yosys
python -m src.cli synthesize counter.v --top counter_4bit --flatten

# View waveforms from a VCD file
python -m src.cli waveform path/to/dump.vcd --cols 120
```

### CLI Options Reference

```
python -m src.cli generate <DESCRIPTION> [OPTIONS]
  -n, --name TEXT       Module name (default: generated_module)
  -i, --inputs TEXT     Input ports — repeatable (default: clk, rst_n)
  -o, --outputs TEXT    Output ports — repeatable (default: out)
  -b, --backend TEXT    LLM backend: auto | openai | anthropic (default: auto)
  --base-url TEXT       Custom OpenAI-compatible API endpoint
  -m, --model TEXT      Model name (default: gpt-4)

python -m src.cli multimodule <DESCRIPTION> [OPTIONS]
  -n, --name TEXT       Top-level module name (default: top_module)
  -i, --inputs TEXT     Input ports — repeatable
  -o, --outputs TEXT    Output ports — repeatable
  -s, --submodules TEXT Submodule hint (e.g. "use half_adder")
  -b, --backend TEXT    LLM backend (default: auto)

python -m src.cli synthesize <VERILOG_FILES>... [OPTIONS]
  -t, --top TEXT        Top-level module name (auto-detected if omitted)
  --flatten             Flatten hierarchy before reporting stats
  --json-out PATH       Write gate-level JSON netlist to file

python -m src.cli waveform <VCD_FILE> [OPTIONS]
  -c, --cols INT        Terminal width for ASCII render (default: 100)

python -m src.cli webui [OPTIONS]
  -p, --port INT        Server port (default: 7860)
  --host TEXT           Bind address (default: 127.0.0.1)
  --share               Create public Gradio link
```

### Using OpenRouter / Custom API Endpoints

```bash
# Option 1: Environment variables
export OPENAI_API_KEY="sk-or-v1-..."
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export OPENAI_MODEL="google/gemma-4-26b-a4b-it:free"

python -m src.cli generate "D flip-flop" -n dff -i clk -i d -o q

# Option 2: CLI flags
python -m src.cli generate "D flip-flop" -n dff -i clk -i d -o q \
  --backend openai \
  --base-url "https://openrouter.ai/api/v1" \
  --model "google/gemma-4-26b-a4b-it:free"
```

Works with: **OpenRouter**, **Ollama** (`http://localhost:11434/v1`), **vLLM**, **LM Studio**, or any OpenAI-compatible API.

---

## 🔌 Mock Mode (No API Key Needed)

When no API key is configured, the tool automatically runs in **mock mode** — generating syntactically valid, simulatable Verilog without any API calls.

**What mock mode produces:**
- Sequential modules (with clock): counter logic with proper `always @(posedge clk)` blocks
- Combinational modules (no clock): `assign` statements
- Self-checking testbenches with clock gen, reset, directed tests, and assertions
- All mock-generated code **compiles and simulates** with Icarus Verilog

**When it activates:**
- No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` set → mock mode
- `--backend auto` with API failure → falls back to mock silently
- `--backend openai` with API failure → raises error (explicit choice is respected)

---

## 📁 Project Structure

```
ai-eda-playground/
├── .github/workflows/
│   └── ci.yml                  CI: Python 3.11–3.13 + iverilog + yosys
│
├── src/
│   ├── generator.py            ★ Core: LLM ↔ Verilog (640+ lines)
│   │   ├── VerilogGenerator    Main class
│   │   ├── generate_module()   NL → Verilog RTL
│   │   ├── generate_multimodule() NL → hierarchical design (top + subs)
│   │   ├── generate_testbench()Module → self-checking TB
│   │   ├── fix_bugs()          Error context → corrected RTL
│   │   ├── _parse_multimodule()Split LLM response into modules
│   │   ├── _call_llm()         Backend dispatch + fallback
│   │   ├── _mock_module()      Offline sequential/combinational gen
│   │   ├── _mock_multimodule() Offline hierarchical gen (full_adder)
│   │   └── _mock_testbench()   Offline TB with assertions
│   │
│   ├── pipeline.py             ★ Orchestrator (330+ lines)
│   │   ├── EDA_Pipeline.run()  Full generate → simulate → fix loop
│   │   ├── EDA_Pipeline.run_multimodule() Multi-file pipeline
│   │   ├── PipelineResult      Dataclass with all outputs + VCD + synth
│   │   ├── _classify_errors()  Regex-based error categorization
│   │   └── _extract_error_lines() Filtered context for LLM
│   │
│   ├── simulator.py            Icarus Verilog wrapper (116 lines)
│   │   ├── compile()           iverilog -g2012
│   │   ├── simulate()          vvp + VCD detection
│   │   └── compile_and_run()   Both in sequence
│   │
│   ├── synthesizer.py          Yosys synthesis wrapper (273 lines)
│   │   ├── synthesize()        Verilog → gate-level stats (JSON)
│   │   ├── write_netlist()     + JSON netlist export
│   │   ├── SynthResult         Dataclass with gate counts, cell types
│   │   └── check_installed()   Graceful Yosys detection
│   │
│   ├── waveform.py             VCD visualization (318 lines)
│   │   ├── parse_vcd()         VCD → WaveData (via vcdvcd)
│   │   ├── render_ascii()      Terminal waveform viewer
│   │   └── render_svg()        Browser waveform viewer (dark theme)
│   │
│   ├── webui.py                Gradio Web UI (460+ lines)
│   │   ├── build_ui()          Component layout + event wiring
│   │   ├── run_pipeline()      Single-module pipeline
│   │   └── run_multimodule_pipeline() Multi-module pipeline
│   │
│   ├── cli.py                  Click CLI (200+ lines)
│   │   ├── generate            Run full single-module pipeline
│   │   ├── multimodule         Run hierarchical multi-module pipeline
│   │   ├── synthesize          Standalone Yosys synthesis
│   │   ├── waveform            View VCD files
│   │   ├── check               Verify tools & keys
│   │   └── webui               Launch browser UI
│   │
│   └── config/prompts.yaml     LLM prompt templates (65+ lines)
│
├── tests/                      73 tests, all passing
│   ├── conftest.py             Shared fixtures
│   ├── test_generator.py       14 tests (mock, fences, config)
│   ├── test_pipeline.py        14 tests (errors, diff, pipeline)
│   ├── test_simulator.py       7 tests (compile, simulate)
│   ├── test_synthesizer.py     13 tests (synthesis, stats, netlist)
│   ├── test_multimodule.py     13 tests (generator parsing, pipeline)
│   └── test_waveform.py        12 tests (parse, ASCII, SVG)
│
├── pyproject.toml              PEP 621 metadata + entry point
├── requirements.txt            Flat dependency list
├── launch_ui.sh                One-command UI launcher
├── GUIDE.md                    Complete developer guide
├── LICENSE                     MIT
└── README.md                   This file
```

---

## 🧪 Testing

```bash
python -m pytest tests/ -v

# Skip tests requiring iverilog
python -m pytest tests/ -v -k "not integration"
```

**73 tests across 6 test files:**

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_generator.py` | 14 | Markdown fence stripping, config loading, mock module/testbench generation, backend auto-resolution, port parsing |
| `test_pipeline.py` | 14 | Error classification, diff calculation, full mock pipeline runs (counter, MUX, FSM, shift register, etc.) |
| `test_simulator.py` | 7 | Compilation, simulation, VCD detection, timeout handling, temp dir cleanup |
| `test_synthesizer.py` | 13 | Yosys synthesis, stat parsing, gate count, netlist export, SynthResult dataclass |
| `test_multimodule.py` | 13 | Multi-module parsing (markers + fallback), mock hierarchical gen, pipeline integration |
| `test_waveform.py` | 12 | VCD parsing, ASCII rendering, SVG rendering, bus handling, XSS escaping |

All tests run in **mock mode** — no API keys needed, no network calls.

---

## 🔧 How the Bug Correction Loop Works

When simulation fails, the pipeline doesn't just report the error — it tries to fix it:

```
Generate → Compile → Simulate → FAIL
  │
  ├── 1. Classify errors (syntax? width mismatch? undefined signal?)
  ├── 2. Extract relevant error lines (max 20, filtered)
  ├── 3. Build context: current errors + what was already tried
  ├── 4. LLM generates fix (with history to avoid repeated fixes)
  ├── 5. Record unified diff of changes
  └── 6. Re-compile and re-simulate
       └── Repeat up to 3 times or until success
```

**Error categories detected:** `syntax`, `undefined`, `width`, `elaboration`, `assertion`

Each correction attempt includes the **full history** of previous attempts, preventing the LLM from repeating failed fixes or going in circles.

---

## 📊 Waveform Viewer

View simulation waveforms in two formats:

**ASCII (Terminal):**
```bash
python -m src.cli waveform dump.vcd --cols 120
```

**SVG (Web UI):**
- Automatically rendered in the Waveform tab after simulation
- Upload standalone VCD files via the "VCD Upload" accordion
- Dark theme, color-coded signals, responsive scaling

---

## 🗺️ Roadmap

- [x] Gradio Web UI with example presets
- [x] VCD Waveform Viewer (ASCII + SVG)
- [x] Dual backend: OpenAI + Anthropic with auto-detection
- [x] OpenRouter / custom API endpoint support
- [x] Autonomous bug correction with error classification
- [x] Mock mode for offline testing
- [x] 73 tests with full mock coverage
- [x] Multi-module hierarchical design support
- [x] Synthesis targeting (Yosys integration)
- [x] CI/CD pipeline (GitHub Actions)
- [ ] SystemVerilog + Assertions support
- [ ] UVM verification mode
- [ ] Coverage-driven feedback loop
- [ ] FPGA bitstream generation

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Install dev dependencies: `pip install -e ".[all]"`
4. Make changes and add tests
5. Run the test suite: `python -m pytest tests/ -v`
6. Commit with a descriptive message
7. Open a Pull Request

---

## 👤 Author

**Kushal Pitaliya** — [GitHub](https://github.com/KushalPitaliya)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
