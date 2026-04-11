"""
AI-EDA Pipeline Orchestrator
Connects generation → simulation → bug correction in a closed loop.
Author: Kushal Pitaliya
"""

import re
import tempfile
from pathlib import Path
from dataclasses import dataclass, field

from .generator import VerilogGenerator
from .simulator import Simulator, SimResult


# ── Error classification ──────────────────────────────────────────────────────

_ERROR_PATTERNS = {
    "syntax":      re.compile(r"syntax error|parse error", re.I),
    "undefined":   re.compile(r"undefined|undeclared|unknown identifier", re.I),
    "width":       re.compile(r"width mismatch|port connection|bit width", re.I),
    "elaboration": re.compile(r"error: elaboration|cannot find module", re.I),
    "assertion":   re.compile(r"FAILED|assertion|mismatch", re.I),
}


def _classify_errors(sim_output: str) -> list[str]:
    """Return a list of matched error category names."""
    return [name for name, pat in _ERROR_PATTERNS.items() if pat.search(sim_output)]


def _extract_error_lines(sim_output: str, max_lines: int = 20) -> str:
    """Return only lines that look like errors/warnings."""
    lines = [
        l for l in sim_output.splitlines()
        if re.search(r"error|warning|FAILED|undefined|mismatch", l, re.I)
    ]
    return "\n".join(lines[:max_lines]) or sim_output[:500]


def _unified_diff(old: str, new: str) -> str:
    """Return a compact line-level diff between two versions of code."""
    import difflib
    diff = list(difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile="before",
        tofile="after",
        n=2,
    ))
    return "".join(diff[:60])  # cap at 60 lines to stay within token budget


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class CorrectionRecord:
    iteration: int
    error_categories: list[str]
    error_snippet: str
    diff: str


@dataclass
class PipelineResult:
    """Full pipeline execution result."""
    module_code: str
    testbench_code: str
    sim_output: str
    success: bool
    iterations: int
    corrections: list[str] = field(default_factory=list)
    vcd_content: str | None = None


# ── Pipeline ──────────────────────────────────────────────────────────────────

class EDA_Pipeline:
    """Orchestrates the generate → simulate → correct loop."""

    MAX_CORRECTION_ATTEMPTS = 3

    def __init__(
        self,
        backend: str = "auto",
        openai_key: str | None = None,
        anthropic_key: str | None = None,
        openai_base_url: str | None = None,
        openai_model: str | None = None,
    ):
        self.generator = VerilogGenerator(
            backend=backend,
            openai_key=openai_key,
            anthropic_key=anthropic_key,
            openai_base_url=openai_base_url,
            openai_model=openai_model,
        )

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
        4. If errors, classify them, build structured context, auto-correct, repeat
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

        # Step 3: Write files and simulate (TemporaryDirectory auto-cleans up)
        with tempfile.TemporaryDirectory(prefix="ai_eda_") as work_dir:
            work_path = Path(work_dir)
            rtl_path = work_path / f"{module_name}.v"
            tb_path = work_path / f"tb_{module_name}.v"

            rtl_path.write_text(module_code)
            tb_path.write_text(tb_code)

            sim = Simulator(str(work_path))
            result = sim.compile_and_run(str(rtl_path), str(tb_path))

            corrections: list[str] = []
            correction_history: list[CorrectionRecord] = []
            iteration = 0

            # Step 4: Structured auto-correction loop
            while not result.success and iteration < self.MAX_CORRECTION_ATTEMPTS:
                iteration += 1
                raw_errors = result.stderr + "\n" + result.stdout
                error_snippet = _extract_error_lines(raw_errors)
                categories = _classify_errors(raw_errors)

                # Build rich context for the LLM: include prior diffs so it knows
                # what was already tried and can avoid repeating the same fix.
                history_ctx = ""
                if correction_history:
                    history_ctx = "\n\nPrevious correction attempts:\n" + "\n".join(
                        f"Attempt {r.iteration} (categories: {', '.join(r.error_categories) or 'unknown'}):\n"
                        f"Errors fixed:\n{r.error_snippet}\n"
                        f"Diff applied:\n{r.diff}"
                        for r in correction_history
                    )

                prev_code = module_code
                module_code = self.generator.fix_bugs(
                    module_code,
                    error_snippet + history_ctx,
                )

                diff = _unified_diff(prev_code, module_code)
                record = CorrectionRecord(
                    iteration=iteration,
                    error_categories=categories,
                    error_snippet=error_snippet,
                    diff=diff,
                )
                correction_history.append(record)
                corrections.append(
                    f"Iteration {iteration} [{', '.join(categories) or 'unknown'}]: "
                    f"{error_snippet[:150].replace(chr(10), ' ')}"
                )

                rtl_path.write_text(module_code)
                result = sim.compile_and_run(str(rtl_path), str(tb_path))

            # Read VCD content before temp dir is cleaned up
            vcd_content = None
            vcd_files = list(work_path.glob("*.vcd"))
            if vcd_files:
                try:
                    vcd_content = vcd_files[0].read_text()
                except OSError:
                    pass

            return PipelineResult(
                module_code=module_code,
                testbench_code=tb_code,
                sim_output=result.stdout + result.stderr,
                success=result.success,
                iterations=iteration + 1,
                corrections=corrections,
                vcd_content=vcd_content,
            )
