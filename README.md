# 🔬 AI-Driven EDA Playground

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Icarus Verilog](https://img.shields.io/badge/Simulator-Icarus%20Verilog-green.svg)](http://iverilog.icarus.com/)
[![Tests](https://img.shields.io/badge/Tests-47%20passing-brightgreen.svg)](#testing)

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
           │ ④ PipelineResult
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
                          └──→ waveform.py ──→ vcdvcd
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Required | Install |
|------|----------|---------|
| Python 3.11+ | ✅ | [python.org](https://www.python.org/) |
| Icarus Verilog | ✅ | `brew install icarus-verilog` (macOS) / `apt install iverilog` (Linux) |
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
│ ✅ OPENAI_API_KEY    configured      │
│ ❌ ANTHROPIC_API_KEY not set         │
│    OPENAI_BASE_URL   (default)       │
│    OPENAI_MODEL      gpt-4           │
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
- 4 example presets (Counter, FSM, Flip-Flop, Shift Register)
- Tabbed output: Status → Module → Testbench → Simulation → Waveform
- Standalone VCD file upload for waveform viewing

### CLI

```bash
# Generate a 4-bit counter (uses mock mode if no API key)
python -m src.cli generate "4-bit up counter with enable" \
  --name counter_4bit \
  -i clk -i rst_n -i enable \
  -o "count[3:0]"

# View waveforms from a VCD file
python -m src.cli waveform path/to/dump.vcd --cols 120
```

### CLI Options Reference

```
python -m src.cli generate <DESCRIPTION> [OPTIONS]

Options:
  -n, --name TEXT       Module name (default: generated_module)
  -i, --inputs TEXT     Input ports — repeatable (default: clk, rst_n)
  -o, --outputs TEXT    Output ports — repeatable (default: out)
  -b, --backend TEXT    LLM backend: auto | openai | anthropic (default: auto)
  --base-url TEXT       Custom OpenAI-compatible API endpoint
  -m, --model TEXT      Model name (default: gpt-4)

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
ai-eda-playground/              2,223 lines total
├── src/
│   ├── generator.py            ★ Core: LLM ↔ Verilog (512 lines)
│   │   ├── VerilogGenerator    Main class
│   │   ├── generate_module()   NL → Verilog RTL
│   │   ├── generate_testbench()Module → self-checking TB
│   │   ├── fix_bugs()          Error context → corrected RTL
│   │   ├── _call_llm()         Backend dispatch + fallback
│   │   ├── _mock_module()      Offline sequential/combinational gen
│   │   ├── _mock_testbench()   Offline TB with assertions
│   │   └── _strip_fences()     Remove markdown code wrappers
│   │
│   ├── pipeline.py             ★ Orchestrator (197 lines)
│   │   ├── EDA_Pipeline.run()  Full generate → simulate → fix loop
│   │   ├── PipelineResult      Dataclass with all outputs + VCD
│   │   ├── _classify_errors()  Regex-based error categorization
│   │   └── _extract_error_lines() Filtered context for LLM
│   │
│   ├── simulator.py            Icarus Verilog wrapper (116 lines)
│   │   ├── compile()           iverilog -g2012
│   │   ├── simulate()          vvp + VCD detection
│   │   └── compile_and_run()   Both in sequence
│   │
│   ├── waveform.py             VCD visualization (318 lines)
│   │   ├── parse_vcd()         VCD → WaveData (via vcdvcd)
│   │   ├── render_ascii()      Terminal waveform viewer
│   │   └── render_svg()        Browser waveform viewer (dark theme)
│   │
│   ├── webui.py                Gradio Web UI (293 lines)
│   │   ├── build_ui()          Component layout + event wiring
│   │   └── run_pipeline()      UI → Pipeline → formatted output
│   │
│   ├── cli.py                  Click CLI (127 lines)
│   │   ├── generate            Run full pipeline
│   │   ├── waveform            View VCD files
│   │   ├── check               Verify tools & keys
│   │   └── webui               Launch browser UI
│   │
│   └── config/prompts.yaml     LLM prompt templates (48 lines)
│
├── tests/                      47 tests, all passing
│   ├── conftest.py             Shared fixtures
│   ├── test_generator.py       14 tests (mock, fences, config)
│   ├── test_pipeline.py        14 tests (errors, diff, pipeline)
│   ├── test_simulator.py       7 tests (compile, simulate)
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
```

**47 tests across 4 test files:**

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_generator.py` | 14 | Markdown fence stripping, config loading, mock module/testbench generation, backend auto-resolution, port parsing |
| `test_pipeline.py` | 14 | Error classification, diff calculation, full mock pipeline runs (counter, MUX, FSM, shift register, etc.) |
| `test_simulator.py` | 7 | Compilation, simulation, VCD detection, timeout handling, temp dir cleanup |
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
- [x] 47 tests with full mock coverage
- [ ] Multi-file project support
- [ ] Synthesis targeting (Yosys integration)
- [ ] SystemVerilog support
- [ ] CI/CD pipeline for automated regression
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
