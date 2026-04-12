"""Tests for multi-module generation and pipeline."""

import subprocess
import textwrap

import pytest

from src.generator import VerilogGenerator
from src.pipeline import EDA_Pipeline


def _iverilog_available():
    try:
        subprocess.run(["iverilog", "-V"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


_needs_iverilog = pytest.mark.skipif(
    not _iverilog_available(),
    reason="Icarus Verilog not installed",
)


# ── Generator tests (pure unit tests, no external tools) ─────────────────────

class TestMultimoduleGenerator:

    def test_generate_multimodule_returns_dict(self):
        gen = VerilogGenerator()
        result = gen.generate_multimodule(
            description="Full adder from half adders",
            module_name="full_adder",
            inputs=["a", "b", "cin"],
            outputs=["sum", "cout"],
        )
        assert isinstance(result, dict)
        assert len(result) >= 2

    def test_generate_multimodule_has_top_and_sub(self):
        gen = VerilogGenerator()
        result = gen.generate_multimodule(
            description="Full adder from half adders",
            module_name="full_adder",
            inputs=["a", "b", "cin"],
            outputs=["sum", "cout"],
        )
        assert "full_adder" in result
        assert "half_adder" in result

    def test_generate_multimodule_contains_valid_verilog(self):
        gen = VerilogGenerator()
        result = gen.generate_multimodule(
            description="Full adder",
            module_name="full_adder",
            inputs=["a", "b", "cin"],
            outputs=["sum", "cout"],
        )
        for name, code in result.items():
            assert f"module {name}" in code
            assert "endmodule" in code

    def test_generate_multimodule_custom_ports(self):
        gen = VerilogGenerator()
        result = gen.generate_multimodule(
            description="Adder",
            module_name="my_adder",
            inputs=["x", "y", "carry_in"],
            outputs=["result", "carry_out"],
        )
        assert "my_adder" in result
        top_code = result["my_adder"]
        assert "x" in top_code
        assert "y" in top_code
        assert "carry_in" in top_code

    def test_parse_multimodule_marker_format(self):
        raw = textwrap.dedent("""\
            //--- MODULE: sub_a ---
            module sub_a (input wire x, output wire y);
              assign y = ~x;
            endmodule

            //--- MODULE: top ---
            module top (input wire a, output wire b);
              sub_a u1 (.x(a), .y(b));
            endmodule
        """)
        result = VerilogGenerator._parse_multimodule(raw, "top")
        assert "sub_a" in result
        assert "top" in result
        assert "module sub_a" in result["sub_a"]
        assert "module top" in result["top"]

    def test_parse_multimodule_fallback_no_markers(self):
        raw = textwrap.dedent("""\
            module sub_a (input wire x, output wire y);
              assign y = ~x;
            endmodule

            module top (input wire a, output wire b);
              sub_a u1 (.x(a), .y(b));
            endmodule
        """)
        result = VerilogGenerator._parse_multimodule(raw, "top")
        assert "sub_a" in result
        assert "top" in result

    def test_parse_multimodule_single_module(self):
        raw = textwrap.dedent("""\
            module only_one (input wire a, output wire b);
              assign b = a;
            endmodule
        """)
        result = VerilogGenerator._parse_multimodule(raw, "only_one")
        assert "only_one" in result
        assert len(result) == 1

    def test_parse_multimodule_with_fences(self):
        raw = textwrap.dedent("""\
            Here is the design:

            ```verilog
            //--- MODULE: half ---
            module half (input a, output b);
              assign b = a;
            endmodule

            //--- MODULE: top ---
            module top (input x, output y);
              half h (.a(x), .b(y));
            endmodule
            ```
        """)
        result = VerilogGenerator._parse_multimodule(raw, "top")
        assert "half" in result
        assert "top" in result


# ── Pipeline tests (need iverilog) ────────────────────────────────────────────

@_needs_iverilog
class TestMultimodulePipeline:

    def test_pipeline_multimodule_success(self):
        pipeline = EDA_Pipeline()
        result = pipeline.run_multimodule(
            description="Full adder from half adders",
            module_name="full_adder",
            inputs=["a", "b", "cin"],
            outputs=["sum", "cout"],
        )
        assert result.success
        assert result.module_files is not None
        assert "half_adder" in result.module_files
        assert "full_adder" in result.module_files

    def test_pipeline_multimodule_has_combined_code(self):
        pipeline = EDA_Pipeline()
        result = pipeline.run_multimodule(
            description="Full adder",
            module_name="full_adder",
            inputs=["a", "b", "cin"],
            outputs=["sum", "cout"],
        )
        assert "module half_adder" in result.module_code
        assert "module full_adder" in result.module_code

    def test_pipeline_multimodule_has_testbench(self):
        pipeline = EDA_Pipeline()
        result = pipeline.run_multimodule(
            description="Full adder",
            module_name="full_adder",
            inputs=["a", "b", "cin"],
            outputs=["sum", "cout"],
        )
        assert "tb_full_adder" in result.testbench_code

    def test_pipeline_multimodule_has_vcd(self):
        pipeline = EDA_Pipeline()
        result = pipeline.run_multimodule(
            description="Full adder",
            module_name="full_adder",
            inputs=["a", "b", "cin"],
            outputs=["sum", "cout"],
        )
        assert result.vcd_content is not None
        assert "$timescale" in result.vcd_content or "$end" in result.vcd_content

    def test_pipeline_multimodule_synthesis(self):
        """Synthesis should work on multi-module designs."""
        pipeline = EDA_Pipeline()
        result = pipeline.run_multimodule(
            description="Full adder",
            module_name="full_adder",
            inputs=["a", "b", "cin"],
            outputs=["sum", "cout"],
        )
        if result.synth_result:
            assert result.synth_result.success
            assert result.synth_result.gate_count > 0
