"""
AI-Driven Verilog Module Generator
Uses LLM to convert natural language descriptions to synthesizable Verilog RTL.
Supports OpenAI (GPT-4) and Anthropic (Claude) backends.
Author: Kushal Pitaliya
"""

import os
import re
import yaml
from pathlib import Path
from typing import Optional, Literal

LLMBackend = Literal["openai", "anthropic", "auto"]

_DEFAULT_CONFIG = Path(__file__).resolve().parent / "config" / "prompts.yaml"

# Regex to strip markdown code fences from LLM responses
_FENCE_RE = re.compile(
    r"```(?:verilog|systemverilog|v|sv)?\s*\n(.*?)```",
    re.DOTALL,
)


class VerilogGenerator:
    """Generates Verilog modules from natural language descriptions."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        backend: LLMBackend = "auto",
        openai_key: str | None = None,
        anthropic_key: str | None = None,
    ):
        resolved_path = Path(config_path) if config_path else _DEFAULT_CONFIG
        self.config = self._load_config(resolved_path)
        self.backend = backend
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY")
        # Lazy-initialised LLM clients (created once, reused across calls)
        self._openai_client = None
        self._anthropic_client = None

    @staticmethod
    def _load_config(path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        with open(path) as f:
            return yaml.safe_load(f)

    # ── Code extraction ───────────────────────────────────────────────────────

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Remove markdown code fences from LLM output, returning raw Verilog."""
        matches = _FENCE_RE.findall(text)
        if matches:
            return "\n\n".join(m.strip() for m in matches)
        # No fences found — return as-is (already raw code)
        return text.strip()

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_module(
        self,
        description: str,
        module_name: str,
        inputs: list[str],
        outputs: list[str],
        requirements: Optional[str] = None,
    ) -> str:
        """Generate a Verilog module from a natural language description."""
        prompt_cfg = self.config["verilog_generation"]
        user_prompt = prompt_cfg["user_template"].format(
            description=description,
            module_name=module_name,
            inputs=", ".join(inputs),
            outputs=", ".join(outputs),
            requirements=requirements or "None specified",
        )
        return self._call_llm(prompt_cfg["system"], user_prompt)

    def generate_testbench(self, module_code: str, num_tests: int = 5) -> str:
        """Generate a testbench for an existing Verilog module."""
        prompt_cfg = self.config["testbench_generation"]
        user_prompt = prompt_cfg["user_template"].format(
            module_code=module_code,
            num_tests=num_tests,
        )
        return self._call_llm(prompt_cfg["system"], user_prompt)

    def fix_bugs(self, module_code: str, sim_output: str) -> str:
        """Analyze simulation errors and generate corrected RTL."""
        prompt_cfg = self.config["bug_correction"]
        user_prompt = prompt_cfg["user_template"].format(
            module_code=module_code,
            sim_output=sim_output,
        )
        return self._call_llm(prompt_cfg["system"], user_prompt)

    # ── LLM dispatch ─────────────────────────────────────────────────────────

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM API. Selects backend based on available keys. Falls back to mock."""
        resolved = self._resolve_backend()
        if resolved == "openai":
            raw = self._call_openai(system_prompt, user_prompt)
        elif resolved == "anthropic":
            raw = self._call_anthropic(system_prompt, user_prompt)
        else:
            return self._mock_response(user_prompt)
        return self._strip_fences(raw)

    def _resolve_backend(self) -> str:
        """Pick the active backend: explicit choice > env key availability > mock."""
        if self.backend == "openai":
            return "openai" if self.openai_key else "mock"
        if self.backend == "anthropic":
            return "anthropic" if self.anthropic_key else "mock"
        # auto: prefer anthropic if key available, then openai, then mock
        if self.anthropic_key:
            return "anthropic"
        if self.openai_key:
            return "openai"
        return "mock"

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from openai import OpenAI

            if self._openai_client is None:
                self._openai_client = OpenAI(api_key=self.openai_key)
            response = self._openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI call failed: {e}")

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import anthropic

            if self._anthropic_client is None:
                self._anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
            response = self._anthropic_client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic call failed: {e}")

    # ── Port helper ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_port(port_str: str) -> tuple[str, str]:
        """Parse a port like 'count[3:0]' into ('[3:0]', 'count') or ('', 'clk')."""
        m = re.match(r"(\w+)\s*(\[\d+:\d+\])", port_str)
        if m:
            return m.group(2), m.group(1)  # width, name
        # Could also be '[3:0] count' format already
        m2 = re.match(r"(\[\d+:\d+\])\s*(\w+)", port_str)
        if m2:
            return m2.group(1), m2.group(2)
        return "", port_str.strip()

    def _mock_response(self, prompt: str) -> str:
        """Context-aware mock: generates module, testbench, or bug-fix depending on prompt."""
        if re.search(r"Generate a testbench", prompt, re.I):
            return self._mock_testbench(prompt)
        if re.search(r"simulation errors|corrected Verilog", prompt, re.I):
            return self._mock_bugfix(prompt)
        return self._mock_module(prompt)

    def _mock_module(self, prompt: str) -> str:
        """Mock: generate a Verilog module from the prompt context."""
        m = re.search(r"Module name:\s*(\w+)", prompt)
        mod_name = m.group(1) if m else "example"

        inp_m = re.search(r"Inputs:\s*(.+)", prompt)
        out_m = re.search(r"Outputs:\s*(.+)", prompt)
        raw_inputs = [p.strip() for p in inp_m.group(1).split(",")] if inp_m else ["clk", "rst_n"]
        raw_outputs = [p.strip() for p in out_m.group(1).split(",")] if out_m else ["out"]

        # Detect clock and reset signals
        has_clk = any("clk" in self._parse_port(s)[1].lower() for s in raw_inputs)
        rst_raw = next((s for s in raw_inputs if "rst" in s.lower()), None)
        rst_sig = self._parse_port(rst_raw)[1] if rst_raw else None

        # Collect data inputs (not clk/rst)
        data_inputs = []
        for inp in raw_inputs:
            _, iname = self._parse_port(inp)
            if "clk" not in iname.lower() and "rst" not in iname.lower():
                data_inputs.append(inp)

        _, first_out = self._parse_port(raw_outputs[0]) if raw_outputs else ("", "out")

        # Combinational logic: no clock → use assign with all data inputs
        if not has_clk:
            port_lines = []
            for inp in raw_inputs:
                width, name = self._parse_port(inp)
                port_lines.append(f"  input  wire {width + ' ' if width else ''}{name}")
            for out in raw_outputs:
                width, name = self._parse_port(out)
                port_lines.append(f"  output wire {width + ' ' if width else ''}{name}")
            ports = ",\n".join(port_lines)

            # AND all data inputs together
            data_names = [self._parse_port(d)[1] for d in data_inputs] or ["1'b0"]
            assign_expr = " & ".join(data_names)
            logic = f"  assign {first_out} = {assign_expr};\n"

            return (
                "// Auto-generated by AI-EDA Playground (mock mode)\n\n"
                f"module {mod_name} (\n{ports}\n);\n{logic}endmodule\n"
            )

        # Sequential logic: has clock
        port_lines = []
        for inp in raw_inputs:
            width, name = self._parse_port(inp)
            port_lines.append(f"  input  wire {width + ' ' if width else ''}{name}")
        for out in raw_outputs:
            width, name = self._parse_port(out)
            port_lines.append(f"  output reg  {width + ' ' if width else ''}{name}")
        ports = ",\n".join(port_lines)

        _, first_clk = self._parse_port(raw_inputs[0]) if raw_inputs else ("", "clk")
        rst_val = "0"
        enable_sig = self._parse_port(data_inputs[0])[1] if data_inputs else None

        if rst_sig:
            is_active_low = "n" in rst_sig.lower() or "_n" in rst_sig
            rst_cond = f"!{rst_sig}" if is_active_low else rst_sig
            edge = "negedge" if is_active_low else "posedge"
            if enable_sig:
                inc_logic = (
                    f"    else if ({enable_sig}) {first_out} <= {first_out} + 1;\n"
                    f"    else        {first_out} <= {first_out};\n"
                )
            else:
                inc_logic = f"    else        {first_out} <= {first_out} + 1;\n"
            rst_logic = (
                f"  always @(posedge {first_clk} or {edge} {rst_sig}) begin\n"
                f"    if ({rst_cond}) {first_out} <= {rst_val};\n"
                + inc_logic
                + f"  end\n"
            )
        else:
            if enable_sig:
                rst_logic = (
                    f"  always @(posedge {first_clk}) begin\n"
                    f"    if ({enable_sig}) {first_out} <= {first_out} + 1;\n"
                    f"  end\n"
                )
            else:
                rst_logic = (
                    f"  always @(posedge {first_clk}) begin\n"
                    f"    {first_out} <= {first_out} + 1;\n"
                    f"  end\n"
                )

        return (
            "// Auto-generated by AI-EDA Playground (mock mode)\n\n"
            f"module {mod_name} (\n{ports}\n);\n{rst_logic}endmodule\n"
        )

    def _mock_testbench(self, prompt: str) -> str:
        """Mock: generate a self-checking testbench that instantiates the DUT."""
        mod_m = re.search(r"module\s+(\w+)\s*\(", prompt)
        mod_name = mod_m.group(1) if mod_m else "generated_module"

        # Parse port declarations from the Verilog module in the prompt
        inputs: list[tuple[str, str]] = []   # (width, name) pairs
        outputs: list[tuple[str, str]] = []
        for line in prompt.splitlines():
            line_s = line.strip().rstrip(",").rstrip()
            inp_match = re.match(r"input\s+(?:wire\s+)?(\[\d+:\d+\]\s+)?(\w+)", line_s)
            out_match = re.match(r"output\s+(?:reg\s+|wire\s+)?(\[\d+:\d+\]\s+)?(\w+)", line_s)
            if inp_match:
                w = (inp_match.group(1) or "").strip()
                inputs.append((w, inp_match.group(2)))
            elif out_match:
                w = (out_match.group(1) or "").strip()
                outputs.append((w, out_match.group(2)))

        if not inputs:
            inputs = [("", "clk"), ("", "rst_n")]
        if not outputs:
            outputs = [("", "out")]

        clk_entry = next(((w, n) for w, n in inputs if "clk" in n.lower()), None)
        has_clk = clk_entry is not None

        if not has_clk:
            return self._mock_tb_combinational(mod_name, inputs, outputs)
        return self._mock_tb_sequential(mod_name, inputs, outputs, clk_entry)

    def _mock_tb_combinational(self, mod_name, inputs, outputs):
        """Testbench for combinational (no-clock) modules."""
        reg_lines = []
        for w, n in inputs:
            pfx = w + ' ' if w else ''
            reg_lines.append(f'  reg  {pfx}{n};')
        wire_lines = []
        for w, n in outputs:
            pfx = w + ' ' if w else ''
            wire_lines.append(f'  wire {pfx}{n};')
        conns = ", ".join(f".{n}({n})" for _, n in inputs + outputs)
        first_out = outputs[0][1] if outputs else "out"
        data_names = [n for _, n in inputs]

        L = []  # output lines
        L.append("`timescale 1ns/1ps")
        L.append(f"module tb_{mod_name};")
        L.append("")
        L.extend(reg_lines)
        L.extend(wire_lines)
        L.append("  integer err_count;")
        L.append("")
        L.append(f"  {mod_name} uut ({conns});")
        L.append("")
        L.append("  initial begin")
        L.append('    $dumpfile("dump.vcd");')
        L.append(f'    $dumpvars(0, tb_{mod_name});')
        L.append("    err_count = 0;")
        L.append("")
        for name in data_names:
            L.append(f"    {name} = 0;")
        L.append("    #10;")
        L.append(f"    // Test 1: all inputs = 0")
        L.append(f"    if ({first_out} !== 0) begin")
        L.append(f'      $display("FAIL: {first_out} = %0d with all inputs 0, expected 0", {first_out});')
        L.append("      err_count = err_count + 1;")
        L.append("    end else")
        L.append(f'      $display("PASS: {first_out} = 0 with all inputs 0");')
        L.append("")
        for name in data_names:
            L.append(f"    {name} = 1;")
        L.append("    #10;")
        L.append(f"    // Test 2: all inputs = 1")
        L.append(f"    if ({first_out} !== 1) begin")
        L.append(f'      $display("FAIL: {first_out} = %0d with all inputs 1, expected 1", {first_out});')
        L.append("      err_count = err_count + 1;")
        L.append("    end else")
        L.append(f'      $display("PASS: {first_out} = 1 with all inputs 1");')
        L.append("")
        if len(data_names) >= 2:
            L.append(f"    {data_names[0]} = 0;")
            L.append("    #10;")
            L.append(f"    // Test 3: {data_names[0]}=0, rest=1")
            L.append(f"    if ({first_out} !== 0) begin")
            L.append(f'      $display("FAIL: {first_out} = %0d with {data_names[0]}=0", {first_out});')
            L.append("      err_count = err_count + 1;")
            L.append("    end else")
            L.append(f'      $display("PASS: {first_out} = 0 with {data_names[0]}=0");')
            L.append("")
        L.append("    if (err_count === 0)")
        L.append('      $display("ALL TESTS PASSED");')
        L.append("    else")
        L.append('      $display("%0d TEST(S) FAILED", err_count);')
        L.append("    $finish;")
        L.append("  end")
        L.append("")
        L.append("endmodule")
        return "\n".join(L) + "\n"

    def _mock_tb_sequential(self, mod_name, inputs, outputs, clk_entry):
        """Testbench for sequential (clocked) modules.

        Uses #1 delays after @(posedge clk) to sample post-NBA values, and
        counts transitions to handle single-bit counters that wrap around.
        """
        clk_name = clk_entry[1]
        rst_entry = next(((w, n) for w, n in inputs if "rst" in n.lower()), None)
        data_inputs = [(w, n) for w, n in inputs if "clk" not in n.lower() and "rst" not in n.lower()]

        reg_lines = []
        for w, n in inputs:
            pfx = w + ' ' if w else ''
            reg_lines.append(f'  reg  {pfx}{n};')
        wire_lines = []
        for w, n in outputs:
            pfx = w + ' ' if w else ''
            wire_lines.append(f'  wire {pfx}{n};')
        conns = ", ".join(f".{n}({n})" for _, n in inputs + outputs)
        first_out = outputs[0][1] if outputs else "out"
        first_out_w = outputs[0][0] if outputs else ""
        saved_w = first_out_w + ' ' if first_out_w else ''

        L = []
        L.append("`timescale 1ns/1ps")
        L.append(f"module tb_{mod_name};")
        L.append("")
        L.extend(reg_lines)
        L.extend(wire_lines)
        L.append("  integer err_count;")
        L.append("")
        L.append(f"  {mod_name} uut ({conns});")
        L.append("")
        L.append(f"  initial {clk_name} = 0;")
        L.append(f"  always #5 {clk_name} = ~{clk_name};")
        L.append("")
        L.append("  initial begin")
        L.append('    $dumpfile("dump.vcd");')
        L.append(f'    $dumpvars(0, tb_{mod_name});')
        L.append("    err_count = 0;")
        L.append("")
        # Init data inputs to 0, assert reset
        for _, name in data_inputs:
            L.append(f"    {name} = 0;")
        if rst_entry:
            rst_name = rst_entry[1]
            is_active_low = "n" in rst_name.lower()
            rst_val = "1'b0" if is_active_low else "1'b1"
            rst_rel = "1'b1" if is_active_low else "1'b0"
            L.append(f"    {rst_name} = {rst_val};")
            # Hold reset for 2 clock cycles, sample post-NBA
            L.append(f"    repeat(2) @(posedge {clk_name});")
            L.append("    #1;")
            L.append("")
            # Test 1: Verify q=0 during reset
            L.append(f"    // Test 1: Verify reset holds {first_out} at 0")
            L.append(f"    if ({first_out} !== 0) begin")
            L.append(f'      $display("FAIL: {first_out} = %0d during reset, expected 0", {first_out});')
            L.append("      err_count = err_count + 1;")
            L.append("    end else")
            L.append(f'      $display("PASS: {first_out} = 0 during reset");')
            L.append("")
            # Release reset
            L.append(f"    {rst_name} = {rst_rel};")
        # Drive data inputs to 1
        for _, name in data_inputs:
            L.append(f"    {name} = 1;")
        L.append("")
        # Test 2: After first active cycle, output should have changed from 0
        L.append(f"    // Test 2: Verify output responds after one active cycle")
        L.append(f"    @(posedge {clk_name}); #1;")
        L.append(f"    if ({first_out} === 0) begin")
        L.append(f'      $display("FAIL: {first_out} still 0 after first active cycle");')
        L.append("      err_count = err_count + 1;")
        L.append("    end else")
        L.append(f'      $display("PASS: {first_out} = %0d after first active cycle", {first_out});')
        L.append("")
        # Test 3: Count transitions over 10 cycles (robust for any bit width)
        L.append(f"    // Test 3: Verify output is toggling (count transitions)")
        L.append("    begin")
        L.append("      integer transitions;")
        L.append(f"      reg {saved_w}prev_val;")
        L.append("      transitions = 0;")
        L.append(f"      prev_val = {first_out};")
        L.append(f"      repeat(10) begin")
        L.append(f"        @(posedge {clk_name}); #1;")
        L.append(f"        if ({first_out} !== prev_val) transitions = transitions + 1;")
        L.append(f"        prev_val = {first_out};")
        L.append("      end")
        L.append("      if (transitions === 0) begin")
        L.append(f'        $display("FAIL: {first_out} stuck, 0 transitions in 10 cycles");')
        L.append("        err_count = err_count + 1;")
        L.append("      end else")
        L.append(f'        $display("PASS: {first_out} had %0d transitions in 10 cycles", transitions);')
        L.append("    end")
        L.append("")
        # Summary
        L.append("    if (err_count === 0)")
        L.append('      $display("ALL TESTS PASSED");')
        L.append("    else")
        L.append('      $display("%0d TEST(S) FAILED", err_count);')
        L.append("    $finish;")
        L.append("  end")
        L.append("")
        L.append("endmodule")
        return "\n".join(L) + "\n"

    @staticmethod
    def _mock_bugfix(prompt: str) -> str:
        """Mock: return the module code unchanged (mock can't actually fix bugs)."""
        # Extract the Verilog code block from the prompt
        m = re.search(r"(module\s+\w+\s*\(.*?endmodule)", prompt, re.DOTALL)
        if m:
            return m.group(1) + "\n"
        return "// Mock mode: unable to extract module for correction\n"
