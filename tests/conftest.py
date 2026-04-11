"""Shared test fixtures for AI-EDA Playground."""

import tempfile
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory (auto-cleaned by pytest)."""
    return tmp_path


@pytest.fixture
def sample_verilog():
    """A simple toggle module for testing."""
    return textwrap.dedent("""\
        module toggle (
          input  wire clk,
          input  wire rst_n,
          output reg  out
        );
          always @(posedge clk or negedge rst_n) begin
            if (!rst_n) out <= 1'b0;
            else        out <= ~out;
          end
        endmodule
    """)


@pytest.fixture
def sample_testbench():
    """Testbench for the toggle module."""
    return textwrap.dedent("""\
        `timescale 1ns/1ps
        module tb_toggle;
          reg  clk, rst_n;
          wire out;

          toggle uut (.clk(clk), .rst_n(rst_n), .out(out));

          initial clk = 0;
          always #5 clk = ~clk;

          initial begin
            rst_n = 0;
            #20 rst_n = 1;
            #100;
            if (out !== 1'b0 && out !== 1'b1)
              $display("FAILED: out is unknown");
            else
              $display("PASSED");
            $finish;
          end
        endmodule
    """)


@pytest.fixture
def sample_vcd(tmp_path):
    """Create a minimal VCD file for testing."""
    vcd_content = textwrap.dedent("""\
        $timescale 1ns $end
        $scope module tb $end
        $var wire 1 ! clk $end
        $var wire 1 " rst $end
        $var wire 1 # out $end
        $upscope $end
        $enddefinitions $end
        #0
        0!
        1"
        x#
        #5
        1!
        #10
        0!
        0"
        #15
        1!
        0#
        #20
        0!
        #25
        1!
        1#
        #30
        0!
        #35
        1!
        0#
        #40
        0!
        $end
    """)
    vcd_file = tmp_path / "test.vcd"
    vcd_file.write_text(vcd_content)
    return str(vcd_file)


@pytest.fixture
def fenced_verilog():
    """LLM-style response with markdown code fences."""
    return textwrap.dedent("""\
        Here is the Verilog module:

        ```verilog
        module counter (
          input wire clk,
          input wire rst_n,
          output reg [3:0] count
        );
          always @(posedge clk or negedge rst_n) begin
            if (!rst_n) count <= 4'b0;
            else count <= count + 1;
          end
        endmodule
        ```

        This module implements a 4-bit counter.
    """)
