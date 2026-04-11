"""Tests for src/pipeline.py"""

import pytest
from src.pipeline import (
    EDA_Pipeline,
    PipelineResult,
    _classify_errors,
    _extract_error_lines,
    _unified_diff,
)


class TestErrorClassification:
    """Test error classification patterns."""

    def test_syntax_error(self):
        cats = _classify_errors("foo.v:5: syntax error, unexpected ';'")
        assert "syntax" in cats

    def test_undefined_error(self):
        cats = _classify_errors("error: undefined variable 'foo'")
        assert "undefined" in cats

    def test_width_mismatch(self):
        cats = _classify_errors("warning: width mismatch on port A")
        assert "width" in cats

    def test_elaboration_error(self):
        cats = _classify_errors("error: elaboration failed")
        assert "elaboration" in cats

    def test_assertion_failure(self):
        cats = _classify_errors("test 3 FAILED: expected 1, got 0")
        assert "assertion" in cats

    def test_no_match(self):
        cats = _classify_errors("Everything looks fine!")
        assert cats == []

    def test_multiple_categories(self):
        cats = _classify_errors("syntax error on line 5\nFAILED assertion at line 10")
        assert "syntax" in cats
        assert "assertion" in cats


class TestExtractErrorLines:
    def test_filters_errors(self):
        output = "info: compiling ok\nERROR: bad signal\ninfo: done"
        result = _extract_error_lines(output)
        assert "ERROR" in result
        assert "compiling ok" not in result

    def test_respects_max_lines(self):
        output = "\n".join(f"ERROR line {i}" for i in range(50))
        result = _extract_error_lines(output, max_lines=5)
        assert result.count("\n") == 4  # 5 lines = 4 newlines

    def test_fallback_on_no_match(self):
        output = "just some regular output"
        result = _extract_error_lines(output)
        assert result == output[:500]


class TestUnifiedDiff:
    def test_produces_diff(self):
        old = "line1\nline2\nline3\n"
        new = "line1\nline2_changed\nline3\n"
        diff = _unified_diff(old, new)
        assert "line2" in diff
        assert "line2_changed" in diff

    def test_identical_no_diff(self):
        code = "module a; endmodule\n"
        diff = _unified_diff(code, code)
        assert diff == ""


class TestPipelineMockMode:
    """Test the full pipeline in mock mode (no API keys)."""

    def test_pipeline_runs_in_mock(self):
        pipeline = EDA_Pipeline(backend="auto", openai_key=None, anthropic_key=None)
        # Force mock mode
        pipeline.generator.openai_key = None
        pipeline.generator.anthropic_key = None

        result = pipeline.run(
            description="simple toggle",
            module_name="toggle_test",
            inputs=["clk", "rst_n"],
            outputs=["out"],
        )
        assert isinstance(result, PipelineResult)
        assert result.module_code
        assert result.testbench_code
        assert result.iterations >= 1

    def test_pipeline_result_fields(self):
        pipeline = EDA_Pipeline(backend="auto")
        pipeline.generator.openai_key = None
        pipeline.generator.anthropic_key = None

        result = pipeline.run(
            description="test",
            module_name="test_mod",
            inputs=["clk"],
            outputs=["out"],
        )
        assert hasattr(result, "module_code")
        assert hasattr(result, "testbench_code")
        assert hasattr(result, "sim_output")
        assert hasattr(result, "success")
        assert hasattr(result, "iterations")
        assert hasattr(result, "corrections")
