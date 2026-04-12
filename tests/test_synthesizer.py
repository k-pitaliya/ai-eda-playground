"""Tests for the Yosys Synthesizer."""

import tempfile
from pathlib import Path

import pytest

from src.synthesizer import Synthesizer, SynthResult


# Skip all tests if Yosys is not installed
pytestmark = pytest.mark.skipif(
    not Synthesizer().check_installed(),
    reason="Yosys not installed",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

COUNTER_V = """\
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
"""

HALF_ADDER_V = """\
module half_adder (
    input  wire a,
    input  wire b,
    output wire sum,
    output wire carry
);
    assign sum   = a ^ b;
    assign carry = a & b;
endmodule
"""

FULL_ADDER_V = """\
module full_adder (
    input  wire a,
    input  wire b,
    input  wire cin,
    output wire sum,
    output wire cout
);
    wire s1, c1, c2;
    half_adder ha1 (.a(a), .b(b), .sum(s1), .carry(c1));
    half_adder ha2 (.a(s1), .b(cin), .sum(sum), .carry(c2));
    assign cout = c1 | c2;
endmodule
"""

BAD_V = "module bad; wire [3:0 x; endmodule"


@pytest.fixture
def work_dir():
    with tempfile.TemporaryDirectory(prefix="synth_test_") as d:
        yield d


@pytest.fixture
def counter_file(work_dir):
    p = Path(work_dir) / "counter.v"
    p.write_text(COUNTER_V)
    return str(p)


@pytest.fixture
def half_adder_file(work_dir):
    p = Path(work_dir) / "half_adder.v"
    p.write_text(HALF_ADDER_V)
    return str(p)


@pytest.fixture
def full_adder_file(work_dir):
    p = Path(work_dir) / "full_adder.v"
    p.write_text(FULL_ADDER_V)
    return str(p)


@pytest.fixture
def bad_file(work_dir):
    p = Path(work_dir) / "bad.v"
    p.write_text(BAD_V)
    return str(p)


# ── Tests ────────────────────────────────────────────────────────────────────

class TestSynthesizer:

    def test_check_installed(self):
        s = Synthesizer()
        assert s.check_installed() is True

    def test_synthesize_counter(self, work_dir, counter_file):
        s = Synthesizer(work_dir)
        r = s.synthesize(counter_file, top_module="counter_4bit")
        assert r.success is True
        assert r.num_cells > 0
        assert r.gate_count > 0
        assert r.num_ports == 4  # clk, rst_n, enable, count
        assert len(r.cell_types) > 0

    def test_synthesize_combinational(self, work_dir, half_adder_file):
        s = Synthesizer(work_dir)
        r = s.synthesize(half_adder_file, top_module="half_adder")
        assert r.success is True
        assert r.gate_count > 0
        assert r.num_ports == 4  # a, b, sum, carry

    def test_synthesize_multi_module(self, work_dir, half_adder_file, full_adder_file):
        s = Synthesizer(work_dir)
        r = s.synthesize(half_adder_file, full_adder_file, top_module="full_adder")
        assert r.success is True
        assert r.gate_count > 0
        assert len(r.modules) >= 1

    def test_synthesize_flatten(self, work_dir, half_adder_file, full_adder_file):
        s = Synthesizer(work_dir)
        r = s.synthesize(half_adder_file, full_adder_file, top_module="full_adder", flatten=True)
        assert r.success is True
        # Flattened design should not have submodule instances
        assert "half_adder" not in r.cell_types

    def test_synthesize_bad_verilog(self, work_dir, bad_file):
        s = Synthesizer(work_dir)
        r = s.synthesize(bad_file, top_module="bad")
        assert r.success is False
        assert "error" in r.stderr.lower() or "ERROR" in r.stdout

    def test_synthesize_no_files(self, work_dir):
        s = Synthesizer(work_dir)
        r = s.synthesize()
        assert r.success is False
        assert "No Verilog files" in r.stderr

    def test_summary_format(self, work_dir, counter_file):
        s = Synthesizer(work_dir)
        r = s.synthesize(counter_file, top_module="counter_4bit")
        summary = r.summary()
        assert "counter_4bit" in summary
        assert "Gates:" in summary
        assert "Cells:" in summary
        assert "Cell breakdown:" in summary

    def test_write_netlist(self, work_dir, counter_file):
        s = Synthesizer(work_dir)
        r = s.write_netlist(counter_file, top_module="counter_4bit", output_json="net.json")
        assert r.success is True
        netlist_path = Path(work_dir) / "net.json"
        assert netlist_path.exists()
        import json
        with open(netlist_path) as f:
            data = json.load(f)
        assert "modules" in data
        assert "counter_4bit" in data["modules"]


class TestSynthResult:

    def test_gate_count_excludes_scopeinfo(self):
        r = SynthResult(
            success=True, stdout="", stderr="",
            num_cells=5,
            cell_types={"$_AND_": 2, "$_XOR_": 1, "$scopeinfo": 2},
        )
        assert r.gate_count == 3  # excludes scopeinfo

    def test_gate_count_empty(self):
        r = SynthResult(success=True, stdout="", stderr="")
        assert r.gate_count == 0

    def test_summary_no_memories(self):
        r = SynthResult(
            success=True, stdout="", stderr="",
            top_module="test", num_cells=3,
            cell_types={"$_AND_": 3},
        )
        summary = r.summary()
        assert "Memories" not in summary

    def test_summary_with_memories(self):
        r = SynthResult(
            success=True, stdout="", stderr="",
            top_module="test", num_memories=2, num_memory_bits=256,
        )
        summary = r.summary()
        assert "Memories" in summary
        assert "256" in summary
