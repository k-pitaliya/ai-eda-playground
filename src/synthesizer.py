"""
Yosys Synthesis Runner
Synthesizes Verilog RTL to gate-level netlists using Yosys.
Provides cell counts, resource usage, and gate-level statistics.
Author: Kushal Pitaliya
"""

import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SynthResult:
    """Synthesis result with gate-level statistics."""
    success: bool
    stdout: str
    stderr: str
    num_wires: int = 0
    num_wire_bits: int = 0
    num_cells: int = 0
    num_ports: int = 0
    num_port_bits: int = 0
    num_memories: int = 0
    num_memory_bits: int = 0
    cell_types: dict[str, int] = field(default_factory=dict)
    modules: list[str] = field(default_factory=list)
    top_module: str = ""

    @property
    def gate_count(self) -> int:
        """Total gate-equivalent count (excludes non-logic cells like scopeinfo)."""
        return sum(
            count for name, count in self.cell_types.items()
            if not name.startswith("$_scopeinfo") and not name.startswith("$scopeinfo")
        )

    def summary(self) -> str:
        """Human-readable synthesis summary."""
        lines = [
            f"Top module:  {self.top_module}",
            f"Gates:       {self.gate_count}",
            f"Cells:       {self.num_cells}",
            f"Wires:       {self.num_wires} ({self.num_wire_bits} bits)",
            f"Ports:       {self.num_ports} ({self.num_port_bits} bits)",
        ]
        if self.num_memories:
            lines.append(f"Memories:    {self.num_memories} ({self.num_memory_bits} bits)")
        if self.cell_types:
            lines.append("\nCell breakdown:")
            for ctype, count in sorted(self.cell_types.items()):
                lines.append(f"  {ctype:20s} × {count}")
        return "\n".join(lines)


class Synthesizer:
    """Runs Yosys synthesis on Verilog files."""

    YOSYS = "yosys"

    def __init__(self, work_dir: str | None = None):
        if work_dir:
            self.work_dir = Path(work_dir)
            self.work_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.work_dir = Path(".")

    def synthesize(
        self,
        *verilog_files: str,
        top_module: str | None = None,
        flatten: bool = False,
    ) -> SynthResult:
        """
        Synthesize Verilog files with Yosys.

        Args:
            *verilog_files: Paths to .v files
            top_module: Top-level module name (auto-detected if one file/one module)
            flatten: If True, flatten hierarchy before stats
        Returns:
            SynthResult with gate statistics
        """
        if not verilog_files:
            return SynthResult(
                success=False, stdout="", stderr="No Verilog files provided"
            )

        # Build Yosys script
        read_cmds = "; ".join(f"read_verilog {f}" for f in verilog_files)
        synth_cmd = "synth"
        if top_module:
            synth_cmd += f" -top {top_module}"
        if flatten:
            synth_cmd += " -flatten"
        script = f"{read_cmds}; {synth_cmd}; stat; stat -json"

        try:
            result = subprocess.run(
                [self.YOSYS, "-p", script],
                capture_output=True,
                text=True,
                cwd=str(self.work_dir),
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return SynthResult(
                success=False, stdout="",
                stderr="Synthesis timed out (120s limit)",
            )
        except FileNotFoundError:
            return SynthResult(
                success=False, stdout="",
                stderr="yosys not found. Install: brew install yosys",
            )

        combined_output = result.stdout + "\n" + result.stderr
        if result.returncode != 0:
            return SynthResult(
                success=False,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        # Parse JSON statistics from Yosys output
        return self._parse_stats(combined_output, top_module or "")

    def write_netlist(
        self,
        *verilog_files: str,
        top_module: str | None = None,
        output_json: str = "netlist.json",
        flatten: bool = False,
    ) -> SynthResult:
        """
        Synthesize and write gate-level JSON netlist.

        Args:
            *verilog_files: Paths to .v files
            top_module: Top-level module name
            output_json: Output JSON file path
            flatten: If True, flatten hierarchy
        Returns:
            SynthResult (netlist written to output_json)
        """
        if not verilog_files:
            return SynthResult(
                success=False, stdout="", stderr="No Verilog files provided"
            )

        read_cmds = "; ".join(f"read_verilog {f}" for f in verilog_files)
        synth_cmd = "synth"
        if top_module:
            synth_cmd += f" -top {top_module}"
        if flatten:
            synth_cmd += " -flatten"

        out_path = self.work_dir / output_json
        script = f"{read_cmds}; {synth_cmd}; stat; stat -json; write_json {out_path}"

        try:
            result = subprocess.run(
                [self.YOSYS, "-p", script],
                capture_output=True,
                text=True,
                cwd=str(self.work_dir),
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return SynthResult(
                success=False, stdout="",
                stderr="Synthesis timed out (120s limit)",
            )
        except FileNotFoundError:
            return SynthResult(
                success=False, stdout="",
                stderr="yosys not found. Install: brew install yosys",
            )

        combined_output = result.stdout + "\n" + result.stderr
        if result.returncode != 0:
            return SynthResult(
                success=False,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        synth_result = self._parse_stats(combined_output, top_module or "")
        return synth_result

    def _parse_stats(self, output: str, top_module: str) -> SynthResult:
        """Extract JSON statistics from Yosys output."""
        # Yosys outputs JSON stats inline — find the last JSON block
        json_start = output.rfind('{\n   "')
        if json_start == -1:
            # Try alternate format
            json_start = output.rfind('"modules"')
            if json_start != -1:
                json_start = output.rfind('{', 0, json_start)

        if json_start == -1:
            return SynthResult(
                success=True,
                stdout=output,
                stderr="Could not parse synthesis statistics",
                top_module=top_module,
            )

        # Find matching closing brace
        brace_depth = 0
        json_end = json_start
        for i in range(json_start, len(output)):
            if output[i] == '{':
                brace_depth += 1
            elif output[i] == '}':
                brace_depth -= 1
                if brace_depth == 0:
                    json_end = i + 1
                    break

        try:
            stats = json.loads(output[json_start:json_end])
        except json.JSONDecodeError:
            return SynthResult(
                success=True,
                stdout=output,
                stderr="Failed to parse JSON statistics",
                top_module=top_module,
            )

        # Extract module list
        modules = list(stats.get("modules", {}).keys())

        # Extract design-level stats (aggregated)
        design = stats.get("design", {})
        if not design:
            # Try getting stats from the first module
            for mod_name, mod_data in stats.get("modules", {}).items():
                if "num_cells" in mod_data:
                    design = mod_data
                    break

        cell_types = design.get("num_cells_by_type", {})

        num_ports = design.get("num_ports", 0)
        if num_ports == 0:
            for mod_name, mod_data in stats.get("modules", {}).items():
                ports_dict = mod_data.get("ports", {})
                if ports_dict:
                    num_ports = len(ports_dict)
                    break
        if num_ports == 0:
            import re
            port_match = re.search(r"Number of ports:\s+(\d+)", output)
            if port_match:
                num_ports = int(port_match.group(1))

        return SynthResult(
            success=True,
            stdout=output,
            stderr="",
            num_wires=design.get("num_wires", 0),
            num_wire_bits=design.get("num_wire_bits", 0),
            num_cells=design.get("num_cells", 0),
            num_ports=num_ports,
            num_port_bits=design.get("num_port_bits", 0),
            num_memories=design.get("num_memories", 0),
            num_memory_bits=design.get("num_memory_bits", 0),
            cell_types=cell_types,
            modules=modules,
            top_module=top_module or (modules[0] if modules else ""),
        )

    def check_installed(self) -> bool:
        """Check if Yosys is available."""
        try:
            subprocess.run(
                [self.YOSYS, "--version"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
