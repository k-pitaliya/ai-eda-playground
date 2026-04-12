"""
Gradio Web UI for AI-EDA Playground
Browser-based interface: Natural Language → Verilog → Simulation
Author: Kushal Pitaliya
"""

import sys
from pathlib import Path

# Allow running from repo root or src/
sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr
from .pipeline import EDA_Pipeline, PipelineResult
from .waveform import vcd_to_svg, parse_vcd


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_ports(raw: str) -> list[str]:
    """Split a comma-separated port string into a cleaned list."""
    return [p.strip() for p in raw.split(",") if p.strip()]


def run_pipeline(
    description: str,
    module_name: str,
    inputs_raw: str,
    outputs_raw: str,
    backend: str,
    openai_key: str,
    anthropic_key: str,
    base_url: str = "",
    model_name: str = "",
) -> tuple[str, str, str, str, str, str]:
    """
    Run the full generate→simulate→correct pipeline.
    Returns: (status_md, module_verilog, testbench_verilog, sim_output, waveform_svg, synth_md)
    """
    no_wave = "<p><em>No waveform — run a simulation first.</em></p>"
    no_synth = "_No synthesis data — Yosys may not be installed._"
    if not description.strip():
        return "⚠️ Please enter a module description.", "", "", "", no_wave, no_synth

    # Pass API keys directly to the pipeline (no os.environ mutation)
    oai_key = openai_key.strip() or None
    ant_key = anthropic_key.strip() or None
    oai_base_url = (base_url or "").strip() or None
    oai_model = (model_name or "").strip() or None

    inputs = _parse_ports(inputs_raw) or ["clk", "rst_n"]
    outputs = _parse_ports(outputs_raw) or ["out"]
    name = module_name.strip() or "generated_module"

    try:
        pipeline = EDA_Pipeline(
            backend=backend,
            openai_key=oai_key,
            anthropic_key=ant_key,
            openai_base_url=oai_base_url,
            openai_model=oai_model,
        )
        result: PipelineResult = pipeline.run(
            description=description,
            module_name=name,
            inputs=inputs,
            outputs=outputs,
        )
    except Exception as e:
        return f"❌ Pipeline error: {e}", "", "", "", no_wave, no_synth

    # Build status markdown
    status_icon = "✅ Success" if result.success else "❌ Failed"
    active_backend = pipeline.generator._resolve_backend()
    lines = [
        f"## {status_icon}",
        f"**Backend used:** `{active_backend}`",
        f"**Iterations:** {result.iterations}",
    ]
    if result.corrections:
        lines.append("\n**Auto-corrections applied:**")
        for c in result.corrections:
            lines.append(f"- {c}")

    # Render waveform from VCD content captured inside the temp dir
    wave_html = no_wave
    if result.vcd_content:
        try:
            import tempfile as _tf
            with _tf.NamedTemporaryFile(suffix=".vcd", mode="w", delete=False) as vf:
                vf.write(result.vcd_content)
                vf.flush()
                svg = vcd_to_svg(vf.name)
            import os
            os.unlink(vf.name)
            wave_html = (
                f'<div style="overflow-x:auto;padding:8px;">{svg}</div>'
            )
        except Exception as e:
            wave_html = f"<p><em>Waveform error: {e}</em></p>"

    # Build synthesis markdown
    synth_md = no_synth
    if result.synth_result and result.synth_result.success:
        sr = result.synth_result
        synth_lines = [
            f"**Top module:** `{sr.top_module or '(auto)'}`",
            f"**Gates:** {sr.gate_count}",
            f"**Cells:** {sr.stats.get('num_cells', 'N/A')}",
            f"**Wires:** {sr.stats.get('num_wires', 'N/A')} ({sr.stats.get('num_wire_bits', '?')} bits)",
            "",
            "| Cell Type | Count |",
            "|-----------|-------|",
        ]
        for ct, cnt in sorted(sr.cells_by_type.items()):
            synth_lines.append(f"| `{ct}` | {cnt} |")
        synth_md = "\n".join(synth_lines)
    elif result.synth_result and not result.synth_result.success:
        synth_md = f"_Synthesis failed:_ `{result.synth_result.stderr[:200]}`"

    return (
        "\n".join(lines),
        result.module_code,
        result.testbench_code,
        result.sim_output or "(no simulation output)",
        wave_html,
        synth_md,
    )


# ── UI Layout ─────────────────────────────────────────────────────────────────

def _render_uploaded_vcd(file_obj) -> str:
    """Render a user-uploaded VCD file as SVG HTML."""
    if file_obj is None:
        return "<p><em>No file selected.</em></p>"
    try:
        svg = vcd_to_svg(file_obj.name)
        return f'<div style="overflow-x:auto;padding:8px;">{svg}</div>'
    except Exception as e:
        return f"<p><em>Error rendering VCD: {e}</em></p>"


def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="🔬 AI-EDA Playground",
    ) as demo:

        gr.Markdown(
            """
# 🔬 AI-EDA Playground
**Natural Language → Verilog → Simulation, all in one place.**

Describe a digital module in plain English, hit **Generate**, and watch the AI
design, testbench, and simulate it — correcting bugs automatically if needed.
            """
        )

        # ── Inputs ────────────────────────────────────────────────────────────
        with gr.Row():
            with gr.Column(scale=3):
                description = gr.Textbox(
                    label="📝 Module Description",
                    placeholder="e.g. 4-bit synchronous up counter with active-low reset and enable",
                    lines=3,
                )
                with gr.Row():
                    module_name = gr.Textbox(
                        label="Module Name",
                        placeholder="counter_4bit",
                        value="generated_module",
                    )
                    inputs_raw = gr.Textbox(
                        label="Inputs (comma-separated)",
                        placeholder="clk, rst_n, enable",
                        value="clk, rst_n",
                    )
                    outputs_raw = gr.Textbox(
                        label="Outputs (comma-separated)",
                        placeholder="count[3:0]",
                        value="out",
                    )

            with gr.Column(scale=1):
                backend = gr.Radio(
                    choices=["auto", "openai", "anthropic"],
                    value="auto",
                    label="🤖 LLM Backend",
                    info="'auto' picks from available API keys (Anthropic preferred)",
                )
                openai_key = gr.Textbox(
                    label="🔑 OpenAI API Key",
                    placeholder="sk-… (optional, also works with OpenRouter keys)",
                    type="password",
                    lines=1,
                )
                anthropic_key = gr.Textbox(
                    label="🔑 Anthropic API Key",
                    placeholder="sk-ant-… (optional)",
                    type="password",
                    lines=1,
                )
                with gr.Accordion("🔧 Advanced (OpenRouter / Custom API)", open=False):
                    base_url = gr.Textbox(
                        label="Base URL",
                        placeholder="https://openrouter.ai/api/v1",
                        lines=1,
                    )
                    model_name = gr.Textbox(
                        label="Model Name",
                        placeholder="e.g. google/gemma-4-26b-a4b-it:free",
                        lines=1,
                    )
                gr.Markdown(
                    "_Leave keys blank to run in **mock mode** (no API needed)._"
                )
                generate_btn = gr.Button("⚡ Generate & Simulate", variant="primary", size="lg")

        # ── Example presets ───────────────────────────────────────────────────
        gr.Examples(
            examples=[
                [
                    "4-bit synchronous up counter with active-low reset and enable",
                    "counter_4bit",
                    "clk, rst_n, enable",
                    "count[3:0]",
                ],
                [
                    "Vending machine Mealy FSM that accepts 25p and 50p coins, dispenses product at 50p",
                    "vending_machine",
                    "clk, rst, coin[1:0]",
                    "product, change_25p",
                ],
                [
                    "D flip-flop with synchronous reset",
                    "dff",
                    "clk, rst, d",
                    "q",
                ],
                [
                    "8-bit shift register with parallel load",
                    "shift_reg_8bit",
                    "clk, rst_n, load, data_in[7:0], serial_in",
                    "data_out[7:0]",
                ],
            ],
            inputs=[description, module_name, inputs_raw, outputs_raw],
            label="📚 Example Designs",
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        with gr.Tabs():
            with gr.Tab("📊 Status"):
                status_md = gr.Markdown("_Run a generation to see results here._")

            with gr.Tab("🧩 Generated Module"):
                module_out = gr.Code(
                    label="Verilog RTL",
                    language="cpp",
                    lines=30,
                    interactive=False,
                )

            with gr.Tab("🧪 Testbench"):
                tb_out = gr.Code(
                    label="Testbench Verilog",
                    language="cpp",
                    lines=30,
                    interactive=False,
                )

            with gr.Tab("🖥️ Simulation Output"):
                sim_out = gr.Textbox(
                    label="stdout / stderr from Icarus Verilog",
                    lines=20,
                    interactive=False,
                )

            with gr.Tab("📈 Waveform"):
                wave_out = gr.HTML(
                    value="<p><em>Run a simulation to see waveforms here.</em></p>",
                    label="VCD Waveform Viewer",
                )

            with gr.Tab("🔬 Synthesis"):
                synth_out = gr.Markdown(
                    value="_No synthesis data — run a generation first._",
                    label="Gate-Level Statistics (Yosys)",
                )

        # ── Waveform upload (standalone viewer) ───────────────────────────────
        with gr.Accordion("📂 Open existing VCD file", open=False):
            vcd_upload = gr.File(label="Upload .vcd file", file_types=[".vcd"])
            vcd_wave_out = gr.HTML(value="<p><em>Upload a VCD to view its waveforms.</em></p>")
            vcd_upload.change(fn=_render_uploaded_vcd, inputs=vcd_upload, outputs=vcd_wave_out)

        # ── Wire up generate button ───────────────────────────────────────────
        generate_btn.click(
            fn=run_pipeline,
            inputs=[description, module_name, inputs_raw, outputs_raw, backend, openai_key, anthropic_key, base_url, model_name],
            outputs=[status_md, module_out, tb_out, sim_out, wave_out, synth_out],
        )

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    demo = build_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
    )


if __name__ == "__main__":
    main()
