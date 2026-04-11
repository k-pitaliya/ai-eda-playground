"""
CLI Interface for AI-EDA Playground
Author: Kushal Pitaliya
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .pipeline import EDA_Pipeline

console = Console()


@click.group()
def cli():
    """🔬 AI-EDA Playground — Natural Language to Verified Verilog"""
    pass


@cli.command()
@click.argument("description")
@click.option("--name", "-n", default="generated_module", help="Module name")
@click.option("--inputs", "-i", multiple=True, default=["clk", "rst_n"], help="Input ports")
@click.option("--outputs", "-o", multiple=True, default=["out"], help="Output ports")
def generate(description: str, name: str, inputs: tuple, outputs: tuple):
    """Generate and verify a Verilog module from a description."""
    console.print(Panel(f"[bold cyan]Generating:[/] {description}", title="AI-EDA Playground"))

    pipeline = EDA_Pipeline()
    result = pipeline.run(
        description=description,
        module_name=name,
        inputs=list(inputs),
        outputs=list(outputs),
    )

    # Display results
    console.print(f"\n[bold]Status:[/] {'✅ Success' if result.success else '❌ Failed'}")
    console.print(f"[bold]Iterations:[/] {result.iterations}")

    if result.corrections:
        console.print("\n[bold yellow]Corrections applied:[/]")
        for c in result.corrections:
            console.print(f"  → {c}")

    console.print("\n[bold]Generated Module:[/]")
    console.print(Syntax(result.module_code, "verilog", theme="monokai"))

    console.print("\n[bold]Testbench:[/]")
    console.print(Syntax(result.testbench_code, "verilog", theme="monokai"))


@cli.command()
def check():
    """Check if required tools are installed."""
    from .simulator import Simulator
    sim = Simulator()
    if sim.check_installed():
        console.print("[green]✅ Icarus Verilog is installed[/]")
    else:
        console.print("[red]❌ Icarus Verilog not found — install with: brew install icarus-verilog[/]")


if __name__ == "__main__":
    cli()
