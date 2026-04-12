# 📖 AI-EDA Playground — Complete Developer & User Guide

> **A comprehensive guide to understanding, using, and building an AI-driven Electronic Design Automation tool from scratch.**

---

## Table of Contents

1. [What Is This Tool?](#1-what-is-this-tool)
2. [How It Works — The Big Picture](#2-how-it-works--the-big-picture)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [Module-by-Module Walkthrough](#4-module-by-module-walkthrough)
5. [The Pipeline: Step by Step](#5-the-pipeline-step-by-step)
6. [Mock Mode vs Real API Mode](#6-mock-mode-vs-real-api-mode)
7. [The Bug Correction Loop](#7-the-bug-correction-loop)
8. [Prompt Engineering](#8-prompt-engineering)
9. [Waveform Visualization](#9-waveform-visualization)
10. [Yosys Synthesis Integration](#10-yosys-synthesis-integration)
11. [Multi-Module Hierarchical Designs](#11-multi-module-hierarchical-designs)
12. [Web UI Architecture](#12-web-ui-architecture)
13. [CLI Reference](#13-cli-reference)
14. [Testing](#14-testing)
15. [How to Build Something Like This](#15-how-to-build-something-like-this)
16. [Troubleshooting](#16-troubleshooting)
17. [Glossary](#17-glossary)

---

## 1. What Is This Tool?

AI-EDA Playground is an **end-to-end AI-powered Verilog design tool** that:

1. Takes a **natural language description** of a digital circuit (e.g., "4-bit counter with enable")
2. **Generates synthesizable Verilog RTL** using an LLM (GPT-4, Claude, or any OpenAI-compatible API)
3. **Supports multi-module hierarchical designs** (e.g., "full adder from half adders")
4. **Auto-generates a self-checking testbench** with clock, reset, directed tests, and assertions
5. **Compiles and simulates** using Icarus Verilog
6. **Automatically detects and fixes bugs** if the simulation fails (up to 3 correction cycles)
7. **Synthesizes with Yosys** — gate counts, cell types, and netlist export
8. **Visualizes waveforms** from VCD files (ASCII in terminal, SVG in browser)

It works via both a **CLI** and a **Gradio-based Web UI**.

### Who Is This For?

- **Students** learning Verilog/digital design — describe what you want, see how it's implemented
- **Engineers** who want rapid prototyping — skip boilerplate, go from idea to simulation in seconds
- **AI/ML enthusiasts** interested in LLM-driven code generation pipelines
- **Educators** demonstrating EDA concepts with interactive tools

---

## 2. How It Works — The Big Picture

```
  You: "4-bit synchronous up counter with enable and active-low reset"
       ↓
  ┌──────────────────────────────────────────────────────────────────┐
  │                     AI-EDA Pipeline                              │
  │                                                                  │
  │  ① LLM generates Verilog module   ─→  counter_4bit.v            │
  │  ② LLM generates testbench        ─→  tb_counter_4bit.v         │
  │  ③ Icarus Verilog compiles & runs  ─→  simulation output         │
  │  ④ If errors → LLM fixes bugs     ─→  corrected counter_4bit.v  │
  │     (repeat ④ up to 3 times)                                     │
  │  ⑤ VCD waveform captured           ─→  waveform viewer           │
  │                                                                  │
  └──────────────────────────────────────────────────────────────────┘
       ↓
  Output: Working Verilog + Testbench + Simulation Log + Waveforms
```

### Data Flow

```
User Input (description + ports)
    │
    ├── generator.py ──→ Raw Verilog RTL
    │       │
    │       ├── _call_openai() / _call_anthropic() / _mock_module()
    │       └── _strip_fences() → Clean code (no markdown wrappers)
    │
    ├── generator.py ──→ Testbench
    │       └── generate_testbench(module_code)
    │
    ├── simulator.py ──→ Compilation + Simulation
    │       ├── iverilog -g2012 → sim.vvp
    │       └── vvp sim.vvp → stdout/stderr + dump.vcd
    │
    ├── pipeline.py ──→ Error Detection & Correction Loop
    │       ├── _classify_errors() → [syntax, width, undefined, ...]
    │       ├── _extract_error_lines() → filtered error context
    │       └── generator.fix_bugs() → corrected RTL
    │
    └── waveform.py ──→ Visualization
            ├── render_ascii() → Terminal waveforms
            └── render_svg() → Browser waveforms
```

---

## 3. Architecture Deep Dive

### File Structure

```
ai-eda-playground/
├── .github/workflows/
│   └── ci.yml                  CI: Python 3.11–3.13 + iverilog + yosys
├── src/
│   ├── __init__.py             Package marker
│   ├── __main__.py             Enables `python -m src`
│   ├── generator.py            ★ Core: LLM ↔ Verilog translation (640+ lines)
│   ├── pipeline.py             ★ Orchestrator: generate → sim → fix (330+ lines)
│   ├── simulator.py            Icarus Verilog wrapper (116 lines)
│   ├── synthesizer.py          Yosys synthesis wrapper (273 lines)
│   ├── waveform.py             VCD parsing + ASCII/SVG rendering (318 lines)
│   ├── webui.py                Gradio browser interface (460+ lines)
│   ├── cli.py                  Click command-line interface (200+ lines)
│   └── config/
│       └── prompts.yaml        LLM prompt templates (65+ lines)
├── tests/
│   ├── conftest.py             Shared test fixtures
│   ├── test_generator.py       14 unit tests
│   ├── test_pipeline.py        14 integration tests
│   ├── test_simulator.py       7 simulator tests
│   ├── test_synthesizer.py     13 synthesis tests
│   ├── test_multimodule.py     13 multi-module tests
│   └── test_waveform.py        12 waveform tests
├── pyproject.toml              PEP 621 project metadata
├── requirements.txt            Flat dependency list
├── launch_ui.sh                One-command Web UI launcher
├── GUIDE.md                    This file
├── LICENSE                     MIT License
└── README.md                   Project documentation
```

### Dependency Graph

```
cli.py ────────┐
               ├──→ pipeline.py ──→ generator.py ──→ LLM APIs / Mock
webui.py ──────┘         │                  │
                         ├──→ simulator.py ──→ Icarus Verilog (iverilog + vvp)
                         │
                         ├──→ synthesizer.py ──→ Yosys
                         │
                         └──→ waveform.py ──→ vcdvcd library
```

### External Dependencies

| Package | Purpose | Required? |
|---------|---------|-----------|
| `openai` | OpenAI/OpenRouter API client | Core |
| `anthropic` | Claude API client | Core |
| `pyyaml` | YAML config loading | Core |
| `click` | CLI framework | Core |
| `rich` | Terminal formatting | Core |
| `gradio` | Web UI | Optional (ui extra) |
| `vcdvcd` | VCD file parsing | Optional (waveform extra) |
| `pytest` | Test framework | Optional (dev extra) |

### External Tools

| Tool | Purpose | Install |
|------|---------|---------|
| `iverilog` | Verilog compiler | `brew install icarus-verilog` (macOS) |
| `vvp` | Simulation runtime | Included with Icarus Verilog |
| `yosys` | RTL synthesis (gate counts, netlist) | `brew install yosys` (macOS) — optional |

---

## 4. Module-by-Module Walkthrough

### 4.1 generator.py — The AI Brain (640+ lines)

This is the heart of the system. It translates between natural language and Verilog using LLMs.

#### Class: `VerilogGenerator`

```python
class VerilogGenerator:
    def __init__(self, config_path=None, backend="auto",
                 openai_key=None, anthropic_key=None,
                 openai_base_url=None, openai_model=None):
```

**Constructor flow:**
1. Loads prompt templates from `config/prompts.yaml`
2. Stores API keys (or reads from environment variables)
3. Resolves which backend to use: explicit choice → env key detection → mock
4. LLM clients are **lazy-initialized** (created on first API call, not at startup)

#### Public Methods

**`generate_module(description, module_name, inputs, outputs, requirements="")`**
- Fills the `verilog_generation` prompt template with user inputs
- Calls the LLM and strips markdown fences from the response
- Returns clean Verilog RTL code

**`generate_testbench(module_code, num_tests=5)`**
- Takes the generated module as input
- LLM creates a self-checking testbench with clock gen, reset, directed tests
- Returns clean testbench code

**`fix_bugs(module_code, sim_output)`**
- Takes buggy module + simulation error output
- LLM analyzes errors and returns corrected RTL
- Returns fixed Verilog code

**`generate_multimodule(description, top_name, inputs, outputs, submodule_hint="")`**
- Generates a hierarchical design with a top module and submodules
- Uses the `multimodule_generation` prompt template
- Returns `dict[str, str]` mapping filenames to Verilog code
- `_parse_multimodule()` splits the LLM response into separate modules

#### LLM Dispatch

```python
def _call_llm(self, system_prompt, user_prompt):
    # Routes to the active backend
    # Falls back to mock if API call fails and backend was auto-resolved
```

The fallback logic is important:
- If you set `--backend auto` and an API call fails (rate limit, no credits), it **silently falls back to mock mode**
- If you explicitly set `--backend openai`, failures are **raised as errors** (you asked for it specifically)

#### Port Parsing

```python
def _parse_port(self, port_str):
    # "count[3:0]" → ("[3:0]", "count")
    # "clk"        → ("", "clk")
```

Handles Verilog bus notation, extracting width and name separately.

#### Mock Mode (Offline Design Generation)

When no API keys are available, the mock backend generates syntactically valid Verilog:

```python
def _mock_module(self, prompt):
    # Detects sequential (has clock) vs combinational modules
    # Generates appropriate always blocks or assign statements

def _mock_multimodule(self, prompt):
    # Generates a full_adder = 2 × half_adder hierarchy
    # Returns dict[str, str] with separate files

def _mock_testbench(self, prompt):
    # Detects sequential vs combinational design under test
    # Generates clock gen, reset sequence, directed tests, assertions

def _mock_bugfix(self, prompt):
    # Extracts existing module code from the prompt (no actual fix)
```

**Why this matters:** Mock mode lets you test the entire pipeline without spending API credits. The generated Verilog compiles, simulates, and passes testbenches.

---

### 4.2 pipeline.py — The Orchestrator (330+ lines)

Coordinates the full generate → simulate → correct workflow, including multi-module and synthesis.

#### Dataclasses

```python
@dataclass
class CorrectionRecord:
    iteration: int              # Which attempt (1, 2, 3)
    error_categories: list[str] # ["syntax", "width"]
    error_snippet: str          # First 20 error lines
    diff: str                   # What changed (unified diff, max 60 lines)

@dataclass
class PipelineResult:
    module_code: str            # Final Verilog RTL
    testbench_code: str         # Generated testbench
    sim_output: str             # Simulation stdout+stderr
    success: bool               # Did it pass?
    iterations: int             # How many correction cycles
    corrections: list[str]      # Human-readable correction log
    vcd_content: str | None     # VCD waveform data (in memory)
    synth_result: SynthResult | None  # Yosys synthesis results
    module_files: dict | None   # Multi-module file map (name → code)
```

#### The `run()` Method — Core Algorithm

```python
def run(self, description, module_name, inputs, outputs):
    # 1. Generate RTL
    module_code = self.generator.generate_module(...)

    # 2. Generate testbench
    tb_code = self.generator.generate_testbench(module_code)

    # 3. Write to temp dir, compile, simulate
    sim_result = simulator.compile_and_run(module_file, tb_file)

    # 4. Correction loop (up to 3 times)
    for i in range(MAX_CORRECTION_ATTEMPTS):
        if sim_result.success:
            break
        # Classify errors, build context with history
        module_code = self.generator.fix_bugs(module_code, error_context)
        # Re-simulate...

    # 5. Capture VCD before temp dir cleanup
    vcd_content = read(vcd_file) if exists else None

    # 6. Synthesize with Yosys (if available)
    synth_result = synthesizer.synthesize(module_file) if yosys_installed else None

    return PipelineResult(...)
```

#### The `run_multimodule()` Method

```python
def run_multimodule(self, description, top_name, inputs, outputs, submodule_hint=""):
    # 1. Generate all modules via generate_multimodule()
    # 2. Write each module to a separate file
    # 3. Generate testbench for the top module
    # 4. Compile all files together + testbench
    # 5. Correction loop applies fixes to top module only
    # 6. Synthesize + capture VCD
    return PipelineResult(module_files=file_map, ...)
```

#### Error Analysis

```python
def _classify_errors(sim_output):
    # Regex patterns for common Verilog error types:
    # - "syntax"      → syntax errors
    # - "undefined"   → undeclared signals
    # - "width"       → port width mismatches
    # - "elaboration" → structural issues
    # - "assertion"   → $error / assertion failures
    return matched_categories

def _extract_error_lines(sim_output, max_lines=20):
    # Filters only lines containing "error" or "warning"
    # Keeps LLM context focused and within token budget
```

---

### 4.3 simulator.py — Icarus Verilog Wrapper (116 lines)

Clean abstraction over the `iverilog` compiler and `vvp` runtime.

```python
class Simulator:
    def compile(self, *verilog_files, output="sim.vvp"):
        # Runs: iverilog -g2012 -o sim.vvp file1.v file2.v
        # Timeout: 30 seconds
        # Returns SimResult

    def simulate(self, vvp_file="sim.vvp"):
        # Runs: vvp sim.vvp
        # Timeout: 60 seconds
        # Auto-detects *.vcd files
        # Returns SimResult

    def compile_and_run(self, *verilog_files):
        # compile() + simulate() in sequence
        # Short-circuits if compilation fails

    @staticmethod
    def check_installed():
        # Returns True if 'iverilog' is in PATH
```

**Key design decisions:**
- `-g2012` flag enables SystemVerilog 2012 features
- Separate compile/simulate steps let you distinguish compilation errors from runtime errors
- Timeout protection prevents runaway simulations
- Auto-detects VCD files by globbing `*.vcd` in the work directory

---

### 4.4 waveform.py — VCD Visualization (318 lines)

Parses VCD (Value Change Dump) files and renders waveforms in two formats.

#### Data Model

```python
@dataclass
class WaveSignal:
    name: str                          # Signal name (e.g., "count[3:0]")
    tv: list[tuple[int, str]]          # Time-value pairs [(0, "0000"), (10, "0001"), ...]
    width: int                         # Bit width (property, derived from name)
    is_bus: bool                       # width > 1 (property)
    def value_at(self, t): ...         # Value at specific time (binary search)

@dataclass
class WaveData:
    timescale: str                     # "1ps", "1ns", etc.
    end_time: int                      # Max timestamp
    signals: list[WaveSignal]          # Up to 20 signals
```

#### ASCII Rendering (Terminal)

```
Time(ns)  0         10        20        30        40
          |         |         |         |         |
clk     : ▔▔▔▔▔____▔▔▔▔▔____▔▔▔▔▔____▔▔▔▔▔____▔▔▔▔▔
rst_n   : ____▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
count   : ╱0x0╲╱0x1╲╱0x2╲╱0x3╲╱0x4╲╱0x5╲╱0x6╲╱0x7╲
```

- Single-bit signals: `▔` (high), `_` (low), `x` (unknown)
- Bus signals: Parallelogram shapes with hex values

#### SVG Rendering (Browser)

- Vector graphics with dark theme (Catppuccin colors)
- Color-coded: `clk` = blue, `rst` = red, bits = green, buses = purple
- Responsive: `px_per_ns` controls horizontal zoom
- XSS prevention: all signal names are HTML-escaped

---

### 4.5 webui.py — Gradio Web Interface (460+ lines)

Browser-based UI built with Gradio.

#### Layout

```
┌────────────────────────────────────────────────┐
│  🔬 AI-Driven EDA Playground                   │
├────────────────┬───────────────────────────────┤
│ Description    │ Backend (auto/openai/claude)   │
│ Module Name    │ OpenAI API Key                 │
│ Inputs         │ Anthropic API Key              │
│ Outputs        │ ▼ Advanced (base URL, model)   │
├────────────────┴───────────────────────────────┤
│  [🚀 Generate & Simulate]                      │
├────────────────────────────────────────────────┤
│ Examples: Counter │ FSM │ Flip-Flop │ Shifter  │
├────────────────────────────────────────────────┤
│ Tab: Status │ Module │ TB │ Sim │ Wave │ Synth │
├────────────────────────────────────────────────┤
│ ▼ Multi-Module Design (accordion)              │
│   Description, Top Name, Inputs, Outputs, Hint │
│   [🚀 Generate Multi-Module]                   │
├────────────────────────────────────────────────┤
│ ▼ VCD File Upload (standalone waveform viewer) │
└────────────────────────────────────────────────┘
```

#### Key Function: `run_pipeline()`

```python
def run_pipeline(description, module_name, inputs_raw, outputs_raw,
                 backend, openai_key, anthropic_key, base_url, model_name):
    # 1. Parse comma-separated ports
    # 2. Build EDA_Pipeline with credentials
    # 3. Run pipeline
    # 4. Build status markdown (success/fail, iterations, corrections)
    # 5. Render VCD to SVG if available
    # Returns: (status_md, module_code, tb_code, sim_output, waveform_svg)
```

**Important Gradio gotcha:** Empty optional text fields come as `None`, not `""`. The code uses `(value or "").strip()` to handle this safely.

---

### 4.6 cli.py — Command-Line Interface (200+ lines)

Six commands built with Click + Rich:

| Command | Purpose |
|---------|---------|
| `generate` | Run the full single-module pipeline from a description |
| `multimodule` | Generate a hierarchical multi-module design |
| `synthesize` | Standalone Yosys synthesis on existing Verilog files |
| `waveform` | View a VCD file as ASCII waveforms |
| `check` | Verify tools (iverilog, Yosys) and API keys |
| `webui` | Launch the Gradio browser interface |

---

## 5. The Pipeline: Step by Step

Here's exactly what happens when you run:

```bash
python -m src.cli generate "4-bit counter with enable" \
  --name counter_4bit -i clk -i rst_n -i enable -o "count[3:0]"
```

### Step 1: Generate RTL Module

The `VerilogGenerator` fills the prompt template:

```
System: You are an expert Verilog RTL designer...
User: Design a Verilog module with:
  - Module name: counter_4bit
  - Inputs: clk, rst_n, enable
  - Outputs: count[3:0]
  - Behavior: 4-bit counter with enable
```

The LLM returns something like:

```verilog
module counter_4bit (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    output reg  [3:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 4'b0;
        else if (enable)
            count <= count + 1;
    end
endmodule
```

### Step 2: Generate Testbench

The module code is passed back to the LLM:

```
System: You are an expert verification engineer...
User: Write a self-checking testbench for: [module code]
      Include 5 directed test cases.
```

The testbench includes:
- Clock generation (`always #5 clk = ~clk;`)
- Reset sequence
- Directed tests with `$display` assertions
- `$dumpfile`/`$dumpvars` for waveform capture
- `$finish` at the end

### Step 3: Compile & Simulate

```bash
iverilog -g2012 -o sim.vvp counter_4bit.v tb_counter_4bit.v
vvp sim.vvp
```

**If successful:** Produces simulation output and `dump.vcd`

**If failed:** Error output is captured for the correction loop

### Step 4: Bug Correction (If Needed)

If simulation fails, the pipeline:

1. **Classifies errors** → `["syntax", "width"]`
2. **Extracts error lines** → Only lines with "error" or "warning" (max 20)
3. **Builds context** → Includes previous correction attempts to avoid repeating fixes
4. **Calls LLM** → "Fix these bugs, here's what was already tried..."
5. **Applies fix** → Records diff, re-compiles, re-simulates
6. **Repeats** up to 3 times

### Step 5: Results

The pipeline returns a `PipelineResult` with:
- Final module code (after any corrections)
- Testbench code
- Simulation output
- Success/failure status
- Number of iterations
- Correction history
- VCD waveform data (captured before temp dir cleanup)

---

## 6. Mock Mode vs Real API Mode

### When Does Mock Mode Activate?

| Scenario | Mode |
|----------|------|
| `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set | Real API |
| `--backend openai` with `OPENAI_API_KEY` set | Real OpenAI |
| `--backend anthropic` with `ANTHROPIC_API_KEY` set | Real Anthropic |
| No API keys set | **Mock mode** |
| `--backend auto` but API call fails | **Falls back to mock** |
| `--backend openai` but API call fails | **Error** (you asked for it) |

### What Mock Mode Generates

Mock mode produces **syntactically valid, simulatable Verilog** without any API calls:

**For sequential modules** (detected by `clk` in inputs):
```verilog
module counter_4bit (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    output reg  [3:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 4'b0;
        else
            count <= count + 1;
    end
endmodule
```

**For combinational modules** (no clock):
```verilog
module my_and (
    input  wire a,
    input  wire b,
    output wire out
);
    assign out = a & b;
endmodule
```

**For testbenches:**
- Detects if DUT is sequential or combinational
- Generates appropriate clock/reset (sequential) or input drivers (combinational)
- Includes self-checking assertions with `$display`
- Includes VCD dump statements

### Why Mock Mode Exists

1. **Free testing** — Test the full pipeline without API costs
2. **Offline development** — Works without internet
3. **CI/CD** — Automated tests don't need API keys
4. **Demo purposes** — Show the tool's capabilities without credentials

---

## 7. The Bug Correction Loop

This is one of the most interesting parts of the system. When simulation fails, the tool doesn't just report the error — it tries to fix it.

### How It Works

```
Iteration 0: Generate → Compile → Simulate → FAIL
    │
    ├── Classify errors: ["syntax", "width"]
    ├── Extract error lines (max 20)
    ├── Context: "No previous attempts"
    │
    ▼ LLM fixes the code
    
Iteration 1: Fix applied → Compile → Simulate → FAIL
    │
    ├── Classify errors: ["assertion"]
    ├── Extract error lines
    ├── Context: "Previous attempt #1: fixed syntax error on line 12"
    │                              "Diff: -wire [3:0] count; +reg [3:0] count;"
    │
    ▼ LLM fixes (knows what was already tried)
    
Iteration 2: Fix applied → Compile → Simulate → PASS ✅
```

### Error Classification

The system uses regex patterns to categorize errors:

| Category | Pattern | Example |
|----------|---------|---------|
| `syntax` | `syntax error`, `unexpected token` | Missing semicolons, typos |
| `undefined` | `not defined`, `unknown module` | Undeclared signals |
| `width` | `port .* width`, `width mismatch` | Bus size mismatches |
| `elaboration` | `elaboration`, `cannot be` | Structural problems |
| `assertion` | `ERROR`, `FAIL`, `assertion` | Testbench assertion failures |

### Context Building

Each correction attempt includes a **history** of previous attempts:

```
Previous correction attempts:
  Attempt 1: Categories: [syntax]
    Changes: -wire [3:0] count;
             +reg [3:0] count;
  Attempt 2: Categories: [width]
    Changes: -output [3:0] count;
             +output reg [3:0] count;
```

This prevents the LLM from:
- Repeating the same fix
- Reverting a previous fix
- Going in circles

### When It Stops

- **Success:** Simulation passes → done
- **Max attempts (3):** Returns the best result so far
- The limit of 3 is a practical balance between thoroughness and API cost

---

## 8. Prompt Engineering

The prompts in `config/prompts.yaml` are carefully crafted:

### Key Principles

1. **Role assignment** — "You are an expert Verilog RTL designer" gives the LLM domain expertise
2. **Output format control** — "Return ONLY the raw Verilog code. Do NOT wrap it in markdown code fences." This is critical because LLMs love to wrap code in ````verilog ... ``` blocks
3. **Quality directives** — "Use non-blocking assignments for sequential logic" ensures synthesizable code
4. **Minimal changes** — Bug fix prompt says "fix with minimal changes" to avoid complete rewrites
5. **History awareness** — "Do NOT repeat fixes that were already attempted" references the correction context

### Why `_strip_fences()` Exists

Despite explicit instructions, LLMs sometimes still wrap code in markdown fences. The `_strip_fences()` function handles this:

```python
def _strip_fences(self, text):
    # Removes: ```verilog ... ``` or ``` ... ```
    # Returns clean Verilog code
```

This is a **defense-in-depth** approach — prompt engineering + post-processing.

### Temperature Setting

The LLM is called with `temperature=0.2` (low). This makes output:
- **More deterministic** — same input produces similar output
- **Less creative** — we want correct Verilog, not creative Verilog
- **More consistent** — easier to strip fences and parse

---

## 9. Waveform Visualization

### VCD Format

VCD (Value Change Dump) is the standard waveform format from Verilog simulations. It records every signal transition:

```
$timescale 1ps $end
$scope module tb $end
$var wire 1 ! clk $end
$var wire 4 " count [3:0] $end
$upscope $end
$enddefinitions $end
#0
0!
b0000 "
#5000
1!
#10000
0!
b0001 "
```

### Parsing (using vcdvcd)

The `parse_vcd()` function:
1. Opens the VCD file using the `vcdvcd` library
2. Extracts signals, filtering for top-level module signals
3. Deduplicates (strips testbench prefix like `tb_foo.`)
4. Limits to 20 signals to keep output manageable

### ASCII Rendering

For terminal output. Uses Unicode characters for clean display:

| Character | Meaning |
|-----------|---------|
| `▔` | Logic high (1) |
| `_` | Logic low (0) |
| `x` | Unknown/undefined |
| `/╲` | Bus transition boundaries |

### SVG Rendering

For the Web UI. Features:
- Dark theme with Catppuccin color palette
- Color-coded signals (clk=blue, rst=red, bits=green, buses=purple)
- Parallelogram shapes for bus value transitions
- Hex labels for bus values
- Responsive horizontal scrolling
- XSS-safe signal labels

---

## 10. Yosys Synthesis Integration

### What Is Synthesis?

Synthesis transforms your RTL Verilog into a **gate-level netlist** — the circuit expressed in terms of logic gates (AND, OR, NOT, flip-flops, etc.) rather than behavioral `always` blocks.

### How It Works

The `Synthesizer` class wraps Yosys:

```python
class Synthesizer:
    def synthesize(self, verilog_path, top_module=None, flatten=False):
        # 1. Runs: yosys -p "read_verilog file.v; synth -top mod; stat -json"
        # 2. Parses the JSON stat output from stdout
        # 3. Returns a SynthResult dataclass

    def write_netlist(self, verilog_path, json_out, top_module=None, flatten=False):
        # Same as synthesize() + writes a JSON netlist file
```

### SynthResult Dataclass

```python
@dataclass
class SynthResult:
    num_wires: int          # Total wire count
    num_wire_bits: int      # Total wire bits
    num_cells: int          # Total cell count
    cell_types: dict        # {"$_AND_": 12, "$_NOT_": 5, "$_DFF_P_": 4}
    raw_log: str            # Full Yosys output

    @property
    def gate_count(self):
        # Cell count excluding $scopeinfo (not a real gate)
        return self.num_cells - self.cell_types.get("$scopeinfo", 0)

    def summary(self):
        # Human-readable multi-line summary
```

### JSON Output

Yosys outputs synthesis stats as JSON inline in stdout. The parser finds the JSON block (starts with `{`, ends with `}`) and extracts the `design` section:

```json
{
  "design": {
    "num_wires": 24,
    "num_wire_bits": 38,
    "num_cells": 16,
    "num_cells_by_type": {
      "$_AND_": 4,
      "$_NOT_": 2,
      "$_DFF_P_": 4,
      "$_OR_": 6
    }
  }
}
```

### Usage

**CLI:**
```bash
python -m src.cli synthesize counter.v --top counter_4bit --flatten
python -m src.cli synthesize counter.v --json-out netlist.json
```

**Pipeline:** Synthesis runs automatically at the end of `pipeline.run()` if Yosys is installed. Results appear in the `synth_result` field of `PipelineResult`.

**Web UI:** The "Synthesis" tab shows gate count, cell breakdown, and wire stats after generation.

---

## 11. Multi-Module Hierarchical Designs

### Concept

Real digital designs are hierarchical. A full adder uses two half adders. An ALU uses adders, MUXes, and shifters. Multi-module support lets you generate these complete hierarchies from a single description.

### How It Works

1. **Prompt:** A dedicated `multimodule_generation` template in `prompts.yaml` instructs the LLM to generate multiple modules with explicit `//--- MODULE: <name> ---` markers between them.

2. **Parsing:** `_parse_multimodule()` splits the response:
   - **Primary:** Looks for `//--- MODULE: <name> ---` markers
   - **Fallback:** Regex splits on `module <name>` declarations
   - Returns `dict[str, str]` mapping filenames to code

3. **Pipeline:** `run_multimodule()` writes each module to a separate `.v` file, generates a testbench for the top module, and compiles all files together.

4. **Bug correction:** Only the top module is modified during correction loops; submodules remain unchanged.

### Mock Mode

Mock multi-module generates a realistic `full_adder = 2 × half_adder` hierarchy:
- `half_adder.v`: XOR for sum, AND for carry
- `full_adder.v`: Instantiates two half adders + OR gate for carry

### Usage

**CLI:**
```bash
python -m src.cli multimodule "Full adder from two half adders" \
  --name full_adder -i a -i b -i cin -o sum -o cout \
  --submodules "use half_adder as building block"
```

**Web UI:** Use the "Multi-Module Design" accordion — fill in the description, top module name, inputs, outputs, and optional submodule hint.

---

## 12. Web UI Architecture

### Technology: Gradio

[Gradio](https://gradio.app/) is a Python library for building ML/AI demos. We chose it because:
- Pure Python (no JavaScript required)
- Built-in component library (textboxes, code viewers, file upload)
- Automatic API generation
- Easy deployment (supports `share=True` for public links)

### Component Layout

The UI is built with `gr.Blocks` for custom layout:

```python
with gr.Blocks(title="AI-EDA Playground") as demo:
    gr.Markdown("# 🔬 AI-Driven EDA Playground")

    with gr.Row():
        with gr.Column():
            # Input fields: description, module name, ports
        with gr.Column():
            # Backend selection, API keys
            with gr.Accordion("Advanced"):
                # Base URL, model name

    gr.Examples(...)  # 4 preset examples

    with gr.Tabs():
        # Status, Module, Testbench, Simulation, Waveform

    with gr.Accordion("VCD Upload"):
        # Standalone waveform viewer
```

### Event Wiring

```python
btn.click(
    fn=run_pipeline,
    inputs=[description, name, inputs, outputs, backend, oai_key, ant_key, base_url, model],
    outputs=[status, module_code, tb_code, sim_output, waveform]
)
```

One button click updates all 6 output tabs atomically (including Synthesis).

### Security Considerations

- API keys are `type="password"` (hidden in UI)
- Keys are passed directly to the pipeline (not stored in environment)
- Signal names are HTML-escaped in SVG to prevent XSS
- No persistent storage — everything is in-memory per request

---

## 13. CLI Reference

### `generate` — Run the Full Pipeline

```bash
python -m src.cli generate <DESCRIPTION> [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--name` | `-n` | `generated_module` | Module name |
| `--inputs` | `-i` | `clk, rst_n` | Input ports (repeatable) |
| `--outputs` | `-o` | `out` | Output ports (repeatable) |
| `--backend` | `-b` | `auto` | LLM backend: `auto`, `openai`, `anthropic` |
| `--base-url` | | env `OPENAI_BASE_URL` | Custom API endpoint |
| `--model` | `-m` | env `OPENAI_MODEL` or `gpt-4` | Model name |

**Examples:**

```bash
# Basic counter (mock mode if no API key)
python -m src.cli generate "4-bit counter" -n cnt4 -i clk -i rst_n -o "count[3:0]"

# With OpenRouter
python -m src.cli generate "D flip-flop" -n dff -i clk -i d -o q \
  --backend openai \
  --base-url "https://openrouter.ai/api/v1" \
  --model "google/gemma-4-26b-a4b-it:free"

# With Anthropic
python -m src.cli generate "2:1 MUX" -n mux2 -i a -i b -i sel -o y \
  --backend anthropic
```

### `multimodule` — Generate Hierarchical Design

```bash
python -m src.cli multimodule <DESCRIPTION> [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--name` | `-n` | `top_module` | Top-level module name |
| `--inputs` | `-i` | `clk, rst_n` | Input ports (repeatable) |
| `--outputs` | `-o` | `out` | Output ports (repeatable) |
| `--submodules` | `-s` | | Submodule hint (e.g., "use half_adder") |
| `--backend` | `-b` | `auto` | LLM backend |

**Example:**
```bash
python -m src.cli multimodule "Full adder using half adders" \
  -n full_adder -i a -i b -i cin -o sum -o cout \
  -s "use half_adder as building block"
```

### `synthesize` — Standalone Yosys Synthesis

```bash
python -m src.cli synthesize <VERILOG_FILES>... [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--top` | `-t` | auto-detected | Top-level module name |
| `--flatten` | | false | Flatten hierarchy before reporting |
| `--json-out` | | | Write JSON netlist to file |

**Example:**
```bash
python -m src.cli synthesize counter.v --top counter_4bit --flatten
python -m src.cli synthesize alu.v -t alu --json-out netlist.json
```

### `waveform` — View VCD Files

```bash
python -m src.cli waveform <VCD_FILE> [--cols N]
```

### `check` — Verify Configuration

```bash
python -m src.cli check
```

Shows: Icarus Verilog status, Yosys status, API keys.

### `webui` — Launch Browser Interface

```bash
python -m src.cli webui [--port 7860] [--host 127.0.0.1] [--share]
```

---

## 14. Testing

### Test Suite (73 tests)

```bash
cd ai-eda-playground
python -m pytest tests/ -v
```

| File | Tests | Coverage |
|------|-------|----------|
| `test_generator.py` | 14 | Fence stripping, config loading, mock generation, backend resolution |
| `test_pipeline.py` | 14 | Error classification, diff calculation, mock pipeline runs |
| `test_simulator.py` | 7 | Compilation, simulation, temp directory cleanup |
| `test_synthesizer.py` | 13 | Yosys synthesis, stat parsing, gate count, netlist export |
| `test_multimodule.py` | 13 | Multi-module parsing (markers + fallback), mock hierarchical gen |
| `test_waveform.py` | 12 | VCD parsing, ASCII rendering, SVG rendering, XSS escaping |

### Key Test Design Decisions

- **Mock mode for CI:** Tests clear API keys to force mock mode (no API calls needed)
- **Real Icarus Verilog:** Tests use real `iverilog`/`vvp` for realistic simulation
- **Fixtures in `conftest.py`:** Shared module/testbench fixtures used across test files
- **Self-checking testbenches:** Mock-generated testbenches include assertions that actually verify behavior

---

## 15. How to Build Something Like This

If you want to build a similar AI-driven EDA tool from scratch, here's the step-by-step approach:

### Phase 1: Core Generator

1. **Set up the Python project** with `pyproject.toml`
2. **Write prompt templates** in YAML — start with the module generation prompt
3. **Build `VerilogGenerator`** — start with just `generate_module()` and OpenAI
4. **Add `_strip_fences()`** — LLMs will wrap code in markdown; handle it
5. **Test manually** — generate a few modules, check they're syntactically correct

### Phase 2: Simulation

6. **Wrap Icarus Verilog** — `subprocess.run()` calls to `iverilog` and `vvp`
7. **Add `generate_testbench()`** — LLM generates a testbench from module code
8. **Create `compile_and_run()`** — compile both files and simulate
9. **Add timeout protection** — simulations can hang; use `subprocess.TimeoutExpired`

### Phase 3: Bug Correction Loop

10. **Build `EDA_Pipeline`** — orchestrate generate → simulate → fix
11. **Add error classification** — regex patterns for common Verilog errors
12. **Implement `fix_bugs()`** — LLM fixes based on error context
13. **Add correction history** — track what was tried to avoid loops
14. **Cap at 3 attempts** — prevent infinite correction cycles

### Phase 4: Mock Mode

15. **Build mock generators** — context-aware mock for testing without API
16. **Make mock testbenches self-checking** — they should actually verify behavior
17. **Write tests using mock mode** — 100% of tests should work offline

### Phase 5: CLI & Web UI

18. **Build Click CLI** — `generate`, `check`, `waveform`, `webui` commands
19. **Build Gradio Web UI** — forms for input, tabs for output
20. **Add waveform viewer** — parse VCD files, render as ASCII and SVG

### Phase 6: Multi-Backend & Polish

21. **Add Anthropic/Claude** — second LLM backend with auto-detection
22. **Add OpenRouter support** — custom `base_url` for any OpenAI-compatible API
23. **Write comprehensive tests** — 70+ tests covering all components
24. **Write documentation** — README, GUIDE, inline comments

### Phase 7: Synthesis & Multi-Module

25. **Integrate Yosys** — synthesize RTL to gate-level, parse JSON stat output
26. **Add multi-module support** — hierarchical designs with submodule parsing
27. **Add CI/CD** — GitHub Actions running tests on every push/PR
28. **Update documentation** — reflect new features in README and GUIDE

### Key Lessons Learned

- **LLMs are inconsistent** — always post-process output (strip fences, validate syntax)
- **Low temperature (0.2) is key** — you want deterministic, correct code
- **Mock mode is essential** — for testing, CI, and demos
- **Prompt engineering matters** — "Return ONLY raw Verilog" saves hours of parsing headaches
- **Error context matters** — telling the LLM what was already tried prevents loops
- **Capture VCD before cleanup** — temp directories are deleted; read files first

---

## 16. Troubleshooting

### "iverilog: command not found"

```bash
# macOS
brew install icarus-verilog

# Ubuntu/Debian
sudo apt-get install iverilog

# Verify
iverilog -V
```

### "No API key found, using mock mode"

This is normal! Mock mode generates valid Verilog without API calls. To use real AI:

```bash
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Rate limited" or "insufficient credits"

With `--backend auto`, the tool falls back to mock mode automatically. With an explicit backend, you'll get an error. Solutions:
- Use a different model (e.g., free models on OpenRouter)
- Use mock mode for testing
- Add credits to your API account

### Web UI shows "Error" toast

Check the terminal where you launched the UI for the full traceback. Common causes:
- Missing dependencies: `pip install gradio vcdvcd`
- API failures (will show in terminal)

### Testbench fails but module looks correct

The auto-generated testbench may have incorrect expectations. Try:
1. Check simulation output for specific assertion failures
2. The correction loop should handle this (up to 3 attempts)
3. In mock mode, testbenches are designed to match mock module behavior

### VCD waveform is empty

The testbench needs `$dumpfile` and `$dumpvars` statements. AI-generated testbenches include these, but if you're using a custom testbench, add:

```verilog
initial begin
    $dumpfile("dump.vcd");
    $dumpvars(0, tb_module);
end
```

---

## 17. Glossary

| Term | Definition |
|------|-----------|
| **RTL** | Register Transfer Level — hardware description abstraction level |
| **Verilog** | Hardware Description Language (HDL) for digital circuits |
| **EDA** | Electronic Design Automation — software tools for chip design |
| **LLM** | Large Language Model (GPT-4, Claude, etc.) |
| **VCD** | Value Change Dump — standard waveform file format |
| **Testbench** | Verilog code that tests a module by driving inputs and checking outputs |
| **Icarus Verilog** | Open-source Verilog compiler and simulator |
| **iverilog** | Icarus Verilog compiler command |
| **vvp** | Icarus Verilog simulation runtime |
| **Yosys** | Open-source synthesis framework for Verilog |
| **Synthesis** | Converting RTL to gate-level netlist (AND, OR, flip-flops) |
| **Netlist** | Circuit described as interconnected gates/cells |
| **Gate count** | Number of logic cells after synthesis |
| **Mock mode** | Offline mode that generates Verilog without API calls |
| **NBA** | Non-Blocking Assignment (`<=`) — used in sequential logic |
| **Synthesizable** | Code that can be converted to actual hardware gates |
| **Combinational** | Logic without memory/state (e.g., AND gate) |
| **Sequential** | Logic with memory/state, driven by a clock (e.g., counter) |
| **Bus** | Multi-bit signal (e.g., `count[3:0]` is a 4-bit bus) |
| **Hierarchy** | Module instantiation structure (top module → submodules) |
| **Gradio** | Python library for building web UIs for ML/AI tools |
| **OpenRouter** | API gateway for multiple LLM providers |
| **CI/CD** | Continuous Integration / Continuous Deployment |

---

*This guide was written for AI-EDA Playground v0.1.0. For the latest information, see the [README](README.md).*
