"""Tests for src/generator.py"""

import re
import pytest
from src.generator import VerilogGenerator, _FENCE_RE


class TestStripFences:
    """Test markdown fence stripping."""

    def test_strips_verilog_fence(self, fenced_verilog):
        result = VerilogGenerator._strip_fences(fenced_verilog)
        assert "```" not in result
        assert "module counter" in result
        assert "endmodule" in result

    def test_preserves_raw_code(self, sample_verilog):
        result = VerilogGenerator._strip_fences(sample_verilog)
        assert result.strip() == sample_verilog.strip()

    def test_strips_multiple_fences(self):
        text = "```verilog\nmodule a; endmodule\n```\ntext\n```verilog\nmodule b; endmodule\n```"
        result = VerilogGenerator._strip_fences(text)
        assert "module a" in result
        assert "module b" in result
        assert "```" not in result

    def test_strips_sv_fence(self):
        text = "```systemverilog\nmodule x; endmodule\n```"
        result = VerilogGenerator._strip_fences(text)
        assert "module x" in result
        assert "```" not in result

    def test_empty_string(self):
        assert VerilogGenerator._strip_fences("") == ""


class TestConfigPath:
    """Test config path resolution."""

    def test_default_config_loads(self):
        gen = VerilogGenerator()
        assert "verilog_generation" in gen.config
        assert "testbench_generation" in gen.config
        assert "bug_correction" in gen.config

    def test_missing_config_raises(self, tmp_dir):
        with pytest.raises(FileNotFoundError):
            VerilogGenerator(config_path=tmp_dir / "nonexistent.yaml")


class TestMockResponse:
    """Test mock mode generates correct module names and ports."""

    def test_mock_uses_module_name(self):
        gen = VerilogGenerator(backend="auto")
        result = gen.generate_module(
            description="test module",
            module_name="my_counter",
            inputs=["clk", "rst_n"],
            outputs=["count"],
        )
        assert "module my_counter" in result

    def test_mock_uses_custom_ports(self):
        gen = VerilogGenerator(backend="auto")
        result = gen.generate_module(
            description="test",
            module_name="test_mod",
            inputs=["clk", "enable", "data_in"],
            outputs=["data_out"],
        )
        assert "data_in" in result or "enable" in result
        assert "data_out" in result

    def test_mock_returns_valid_verilog(self):
        gen = VerilogGenerator(backend="auto")
        result = gen.generate_module(
            description="simple test",
            module_name="dff",
            inputs=["clk", "d"],
            outputs=["q"],
        )
        assert "module dff" in result
        assert "endmodule" in result


class TestResolveBackend:
    """Test backend resolution logic."""

    def test_no_keys_returns_mock(self):
        gen = VerilogGenerator(backend="auto", openai_key=None, anthropic_key=None)
        # Clear env-based keys too
        gen.openai_key = None
        gen.anthropic_key = None
        assert gen._resolve_backend() == "mock"

    def test_anthropic_preferred_in_auto(self):
        gen = VerilogGenerator(backend="auto", openai_key="sk-test", anthropic_key="sk-ant-test")
        assert gen._resolve_backend() == "anthropic"

    def test_explicit_openai(self):
        gen = VerilogGenerator(backend="openai", openai_key="sk-test")
        assert gen._resolve_backend() == "openai"

    def test_explicit_backend_without_key_falls_to_mock(self):
        gen = VerilogGenerator(backend="openai", openai_key=None)
        gen.openai_key = None
        assert gen._resolve_backend() == "mock"
