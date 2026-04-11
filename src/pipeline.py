"""
AI-EDA Pipeline Orchestrator
Connects generation → simulation → bug correction in a closed loop.
Author: Kushal Pitaliya
"""

import tempfile
from pathlib import Path
from dataclasses import dataclass, field

from .generator import VerilogGenerator
from .simulator import Simulator


@dataclass
class PipelineResult:
    """Full pipeline execution result."""
    module_code: str
    testbench_code: str
    sim_output: str
    success: bool
    iterations: int
    corrections: list[str] = field(default_factory=list)


class EDA_Pipeline:
    """Orchestrates the generate → simulate → correct loop."""

    MAX_CORRECTION_ATTEMPTS = 3

    def __init__(self):
        self.generator = VerilogGenerator()
        self.simulator = Simulator()

    def run(
        self,
        description: str,
        module_name: str,
        inputs: list[str],
        outputs: list[str],
    ) -> PipelineResult:
        """
        Full pipeline:
        1. Generate Verilog from description
        2. Generate testbench
        3. Simulate
        4. If errors, auto-correct and re-simulate (up to MAX attempts)
        """
        # Step 1: Generate RTL
        module_code = self.generator.generate_module(
            description=description,
            module_name=module_name,
            inputs=inputs,
            outputs=outputs,
        )

        # Step 2: Generate testbench
        tb_code = self.generator.generate_testbench(module_code)

        # Step 3: Write files and simulate
        work_dir = Path(tempfile.mkdtemp())
        rtl_path = work_dir / f"{module_name}.v"
        tb_path = work_dir / f"tb_{module_name}.v"

        rtl_path.write_text(module_code)
        tb_path.write_text(tb_code)

        sim = Simulator(str(work_dir))
        result = sim.compile_and_run(str(rtl_path), str(tb_path))

        corrections = []
        iteration = 0

        # Step 4: Auto-correction loop
        while not result.success and iteration < self.MAX_CORRECTION_ATTEMPTS:
            iteration += 1
            error_output = result.stderr or result.stdout

            corrected = self.generator.fix_bugs(module_code, error_output)
            corrections.append(f"Iteration {iteration}: {error_output[:200]}")

            module_code = corrected
            rtl_path.write_text(module_code)
            result = sim.compile_and_run(str(rtl_path), str(tb_path))

        return PipelineResult(
            module_code=module_code,
            testbench_code=tb_code,
            sim_output=result.stdout + result.stderr,
            success=result.success,
            iterations=iteration + 1,
            corrections=corrections,
        )
