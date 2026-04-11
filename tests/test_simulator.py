"""Tests for src/simulator.py"""

import subprocess
import pytest
from src.simulator import Simulator, SimResult


class TestSimulator:
    """Test simulator compilation and execution."""

    def test_check_installed(self):
        sim = Simulator()
        # Should return True/False without raising
        result = sim.check_installed()
        assert isinstance(result, bool)

    def test_compile_valid_verilog(self, tmp_dir, sample_verilog):
        rtl_path = tmp_dir / "toggle.v"
        rtl_path.write_text(sample_verilog)

        sim = Simulator(str(tmp_dir))
        if not sim.check_installed():
            pytest.skip("Icarus Verilog not installed")

        result = sim.compile(str(rtl_path))
        assert result.success
        assert result.return_code == 0

    def test_compile_invalid_verilog(self, tmp_dir):
        bad_file = tmp_dir / "bad.v"
        bad_file.write_text("this is not verilog at all!")

        sim = Simulator(str(tmp_dir))
        if not sim.check_installed():
            pytest.skip("Icarus Verilog not installed")

        result = sim.compile(str(bad_file))
        assert not result.success

    def test_compile_and_run(self, tmp_dir, sample_verilog, sample_testbench):
        rtl = tmp_dir / "toggle.v"
        tb = tmp_dir / "tb_toggle.v"
        rtl.write_text(sample_verilog)
        tb.write_text(sample_testbench)

        sim = Simulator(str(tmp_dir))
        if not sim.check_installed():
            pytest.skip("Icarus Verilog not installed")

        result = sim.compile_and_run(str(rtl), str(tb))
        assert result.success
        assert "PASSED" in result.stdout

    def test_simulate_missing_vvp(self, tmp_dir):
        sim = Simulator(str(tmp_dir))
        result = sim.simulate("nonexistent.vvp")
        assert not result.success
        assert "not found" in result.stderr.lower()

    def test_no_tempdir_leak(self, tmp_dir):
        """Simulator should not create temp dirs when work_dir is provided."""
        sim = Simulator(str(tmp_dir))
        assert sim.work_dir == tmp_dir

    def test_default_work_dir(self):
        """Without work_dir, simulator should use current directory."""
        sim = Simulator()
        assert str(sim.work_dir) == "."
