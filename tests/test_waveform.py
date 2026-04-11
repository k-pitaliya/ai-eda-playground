"""Tests for src/waveform.py"""

import pytest


class TestParseVCD:
    """Test VCD file parsing."""

    def test_parse_basic_vcd(self, sample_vcd):
        from src.waveform import parse_vcd
        wave = parse_vcd(sample_vcd)
        assert wave.signals
        assert wave.end_time > 0
        assert wave.timescale

    def test_signal_names(self, sample_vcd):
        from src.waveform import parse_vcd
        wave = parse_vcd(sample_vcd)
        names = {s.name for s in wave.signals}
        # Should have our signals (possibly with prefix stripped)
        assert len(names) >= 1

    def test_max_signals_limit(self, sample_vcd):
        from src.waveform import parse_vcd
        wave = parse_vcd(sample_vcd, max_signals=1)
        assert len(wave.signals) <= 1


class TestASCIIRenderer:
    """Test ASCII waveform rendering."""

    def test_render_basic(self, sample_vcd):
        from src.waveform import vcd_to_ascii
        output = vcd_to_ascii(sample_vcd, cols=60)
        assert isinstance(output, str)
        assert len(output) > 0
        # Should contain signal rows
        assert "│" in output

    def test_render_empty_data(self):
        from src.waveform import render_ascii, WaveData
        wave = WaveData(timescale="1ns", end_time=0, signals=[])
        assert render_ascii(wave) == "(no waveform data)"


class TestSVGRenderer:
    """Test SVG waveform rendering."""

    def test_render_svg(self, sample_vcd):
        from src.waveform import vcd_to_svg
        svg = vcd_to_svg(sample_vcd)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_render_empty_svg(self):
        from src.waveform import render_svg, WaveData
        wave = WaveData(timescale="1ns", end_time=0, signals=[])
        result = render_svg(wave)
        assert "No waveform data" in result

    def test_svg_html_escaping(self):
        """Signal names with special chars should be HTML-escaped in SVG."""
        from src.waveform import render_svg, WaveData, WaveSignal
        sig = WaveSignal(name='<script>alert("xss")</script>', tv=[(0, "0"), (100, "1")])
        wave = WaveData(timescale="1ns", end_time=200, signals=[sig])
        svg = render_svg(wave)
        assert "<script>" not in svg
        assert "&lt;script&gt;" in svg


class TestWaveSignal:
    """Test WaveSignal data model."""

    def test_width_single_bit(self):
        from src.waveform import WaveSignal
        sig = WaveSignal(name="clk", tv=[])
        assert sig.width == 1
        assert not sig.is_bus

    def test_width_bus(self):
        from src.waveform import WaveSignal
        sig = WaveSignal(name="data[7:0]", tv=[])
        assert sig.width == 8
        assert sig.is_bus

    def test_value_at(self):
        from src.waveform import WaveSignal
        sig = WaveSignal(name="clk", tv=[(0, "0"), (10, "1"), (20, "0")])
        assert sig.value_at(0) == "0"
        assert sig.value_at(5) == "0"
        assert sig.value_at(10) == "1"
        assert sig.value_at(15) == "1"
        assert sig.value_at(25) == "0"

    def test_value_at_before_first(self):
        from src.waveform import WaveSignal
        sig = WaveSignal(name="out", tv=[(10, "1")])
        assert sig.value_at(5) == "x"
