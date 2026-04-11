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
@click.option(
    "--backend", "-b",
    type=click.Choice(["auto", "openai", "anthropic"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="LLM backend (auto picks from available API keys)",
)
@click.option("--base-url", default=None, envvar="OPENAI_BASE_URL",
              help="Custom OpenAI-compatible API base URL (e.g. https://openrouter.ai/api/v1)")
@click.option("--model", "-m", default=None, envvar="OPENAI_MODEL",
              help="Model name for OpenAI backend (default: gpt-4)")
def generate(description: str, name: str, inputs: tuple, outputs: tuple,
             backend: str, base_url: str | None, model: str | None):
    """Generate and verify a Verilog module from a description."""
    console.print(Panel(f"[bold cyan]Generating:[/] {description}", title="AI-EDA Playground"))

    pipeline = EDA_Pipeline(backend=backend, openai_base_url=base_url, openai_model=model)
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
@click.argument("vcd_file", type=click.Path(exists=True))
@click.option("--cols", "-c", default=100, show_default=True, help="Terminal width for ASCII render")
def waveform(vcd_file: str, cols: int):
    """Render a VCD waveform file as ASCII in the terminal."""
    from .waveform import vcd_to_ascii
    try:
        output = vcd_to_ascii(vcd_file, cols=cols)
        console.print(output)
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


@cli.command()
def check():
    """Check if required tools are installed."""
    import os
    from .simulator import Simulator
    sim = Simulator()
    if sim.check_installed():
        console.print("[green]✅ Icarus Verilog is installed[/]")
    else:
        console.print("[red]❌ Icarus Verilog not found — install with: brew install icarus-verilog[/]")

    if os.getenv("OPENAI_API_KEY"):
        console.print("[green]✅ OPENAI_API_KEY is set[/]")
    else:
        console.print("[yellow]⚠️  OPENAI_API_KEY not set[/]")

    if os.getenv("ANTHROPIC_API_KEY"):
        console.print("[green]✅ ANTHROPIC_API_KEY is set[/]")
    else:
        console.print("[yellow]⚠️  ANTHROPIC_API_KEY not set[/]")

    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        console.print(f"[green]✅ OPENAI_BASE_URL = {base_url}[/]")
    model = os.getenv("OPENAI_MODEL")
    if model:
        console.print(f"[green]✅ OPENAI_MODEL = {model}[/]")


@cli.command()
@click.option("--port", "-p", default=7860, show_default=True, help="Port to listen on")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind to")
@click.option("--share", is_flag=True, default=False, help="Create a public Gradio share link")
def webui(port: int, host: str, share: bool):
    """Launch the browser-based Web UI."""
    try:
        from .webui import build_ui
    except ImportError:
        console.print("[red]Gradio not installed. Run: pip install gradio[/]")
        raise SystemExit(1)

    console.print(Panel(f"[bold cyan]AI-EDA Playground Web UI[/]\nOpen [link]http://{host}:{port}[/link]"))
    demo = build_ui()
    demo.launch(server_name=host, server_port=port, share=share, inbrowser=True)


if __name__ == "__main__":
    cli()
