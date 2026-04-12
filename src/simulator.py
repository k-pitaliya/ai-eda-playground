"""
Icarus Verilog Simulation Runner
Compiles and runs Verilog simulations, captures output for analysis.
Author: Kushal Pitaliya
"""

import subprocess
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SimResult:
    """Simulation result container."""
    success: bool
    stdout: str
    stderr: str
    vcd_path: str | None = None
    return_code: int = 0


class Simulator:
    """Runs Icarus Verilog simulations."""

    IVERILOG = "iverilog"
    VVP = "vvp"

    def __init__(self, work_dir: str | None = None):
        if work_dir:
            self.work_dir = Path(work_dir)
            self.work_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.work_dir = Path(".")

    def compile(self, *verilog_files: str, output: str = "sim.vvp") -> SimResult:
        """Compile Verilog files with Icarus Verilog."""
        out_path = self.work_dir / output
        cmd = [self.IVERILOG, "-g2012", "-o", str(out_path)] + list(verilog_files)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
        except subprocess.TimeoutExpired:
            return SimResult(
                success=False, stdout="",
                stderr="Compilation timed out (30s limit)", return_code=-1,
            )
        except FileNotFoundError:
            return SimResult(
                success=False, stdout="",
                stderr=f"iverilog not found. Install: brew install icarus-verilog",
                return_code=-1,
            )
        return SimResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
        )

    def simulate(self, vvp_file: str = "sim.vvp") -> SimResult:
        """Run compiled simulation."""
        vvp_path = self.work_dir / vvp_file
        if not vvp_path.exists():
            return SimResult(success=False, stdout="", stderr="VVP file not found")

        try:
            result = subprocess.run(
                [self.VVP, str(vvp_path)],
                capture_output=True,
                text=True,
                cwd=str(self.work_dir),
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return SimResult(
                success=False, stdout="",
                stderr="Simulation timed out (60s limit)", return_code=-1,
            )
        except FileNotFoundError:
            return SimResult(
                success=False, stdout="",
                stderr="vvp not found. Install: brew install icarus-verilog",
                return_code=-1,
            )

        vcd_files = list(self.work_dir.glob("*.vcd"))
        vcd_path = str(vcd_files[0]) if vcd_files else None

        return SimResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            vcd_path=vcd_path,
            return_code=result.returncode,
        )

    def compile_and_run(self, *verilog_files: str) -> SimResult:
        """Compile and simulate in one step."""
        compile_result = self.compile(*verilog_files)
        if not compile_result.success:
            return compile_result
        return self.simulate()

    def check_installed(self) -> bool:
        """Check if Icarus Verilog is available."""
        try:
            subprocess.run(
                [self.IVERILOG, "-V"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
