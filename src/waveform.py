"""
VCD Waveform Viewer
Parses Verilog VCD files and renders waveforms as ASCII (CLI) or
inline SVG (Gradio Web UI).
Author: Kushal Pitaliya
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class WaveSignal:
    name: str
    tv: list[tuple[int, str]]   # (timestamp_ps, value) pairs

    @property
    def width(self) -> int:
        """Infer bus width from signal name (e.g. coin[1:0] → 2)."""
        import re
        m = re.search(r"\[(\d+):(\d+)\]", self.name)
        if m:
            return int(m.group(1)) - int(m.group(2)) + 1
        return 1

    @property
    def is_bus(self) -> bool:
        return self.width > 1

    def value_at(self, t: int) -> str:
        """Return signal value at time t (ps)."""
        val = "x"
        for ts, v in self.tv:
            if ts <= t:
                val = v
            else:
                break
        return val


@dataclass
class WaveData:
    timescale: str
    end_time: int
    signals: list[WaveSignal] = field(default_factory=list)


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_vcd(vcd_path: str, max_signals: int = 20) -> WaveData:
    """Parse a VCD file into a WaveData object."""
    try:
        import vcdvcd
    except ImportError:
        raise ImportError("Install vcdvcd: pip install vcdvcd")

    v = vcdvcd.VCDVCD(vcd_path)

    # Filter to top-level module signals (exclude hierarchy duplicates)
    top_prefix = _find_top_prefix(list(v.signals))
    seen_short: set[str] = set()
    signals: list[WaveSignal] = []

    for full_name in v.signals:
        short = full_name[len(top_prefix):] if full_name.startswith(top_prefix) else full_name
        if short in seen_short or short.startswith("uut."):
            continue
        seen_short.add(short)
        tv = list(v[full_name].tv)
        signals.append(WaveSignal(name=short, tv=tv))
        if len(signals) >= max_signals:
            break

    end_time = max((tv[-1][0] for s in signals if (tv := s.tv)), default=0)
    return WaveData(timescale=str(v.timescale), end_time=end_time, signals=signals)


def _find_top_prefix(names: list[str]) -> str:
    """Return the common module prefix to strip (e.g. 'tb_foo.')."""
    if not names:
        return ""
    parts = names[0].split(".")
    return parts[0] + "." if len(parts) > 1 else ""


# ── ASCII renderer ────────────────────────────────────────────────────────────

def render_ascii(wave: WaveData, cols: int = 80, show_time: bool = True) -> str:
    """Render waveforms as an ASCII string."""
    if not wave.signals or wave.end_time == 0:
        return "(no waveform data)"

    name_w = max(len(s.name) for s in wave.signals) + 1
    wave_w = cols - name_w - 3

    lines: list[str] = []

    if show_time:
        # Time ruler
        step = wave.end_time / wave_w
        ruler = " " * (name_w + 2)
        marks = ""
        for i in range(0, wave_w, 10):
            t_label = f"{int(i * step / 1000)}ns"
            marks += t_label.ljust(10)
        lines.append(ruler + marks[:wave_w])
        lines.append(" " * (name_w + 2) + "─" * wave_w)

    for sig in wave.signals:
        row = _render_signal_row(sig, wave.end_time, wave_w)
        label = sig.name.rjust(name_w)
        lines.append(f"{label} │{row}")

    return "\n".join(lines)


def _render_signal_row(sig: WaveSignal, end_time: int, width: int) -> str:
    """Render a single signal as a row of ASCII characters."""
    chars = []
    prev_val = "x"
    for i in range(width):
        t = int(i * end_time / width)
        val = sig.value_at(t)
        if sig.is_bus:
            if val != prev_val:
                hex_val = _bin_to_hex(val)
                label = hex_val[:4].center(4)
                chars.append("┤" + label)
            else:
                chars.append("─")
        else:
            if val == "1":
                chars.append("▔")
            elif val == "0":
                chars.append("_")
            else:
                chars.append("x")
        prev_val = val

    return "".join(chars[:width])


def _bin_to_hex(b: str) -> str:
    """Convert binary string to hex, handling x/z."""
    if any(c in b for c in ("x", "z")):
        return "??"
    try:
        return format(int(b, 2), "X")
    except ValueError:
        return "??"


# ── SVG renderer ─────────────────────────────────────────────────────────────

_COLORS = {
    "clk":    "#4fc3f7",
    "rst":    "#ef9a9a",
    "rst_n":  "#ef9a9a",
    "default_bit": "#a5d6a7",
    "default_bus": "#ce93d8",
}
_TRANSITION_W = 4   # px width of slant transition for buses


def _esc(text: str) -> str:
    """HTML-escape text for safe SVG embedding."""
    return html.escape(text, quote=True)


def render_svg(wave: WaveData, px_per_ns: float = 0.05, row_h: int = 28,
               name_w: int = 140) -> str:
    """Render waveforms as an SVG string suitable for embedding in HTML."""
    if not wave.signals or wave.end_time == 0:
        return "<p><em>No waveform data available.</em></p>"

    total_ns = wave.end_time / 1000  # ps → ns
    wave_w = max(int(total_ns * px_per_ns), 400)
    n_sigs = len(wave.signals)
    svg_h = n_sigs * row_h + 40   # 40px header
    svg_w = name_w + wave_w + 20

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
        f'style="background:#1e1e2e;font-family:monospace;font-size:11px;">'
    )

    # Grid and time axis
    parts.append(_svg_time_axis(name_w, svg_w, svg_h, total_ns, wave_w))

    # Signal rows
    for idx, sig in enumerate(wave.signals):
        y = idx * row_h + 30
        color = _COLORS.get(sig.name.lower(),
                _COLORS["default_bus"] if sig.is_bus else _COLORS["default_bit"])
        # Label (HTML-escaped to prevent XSS)
        parts.append(
            f'<text x="{name_w - 6}" y="{y + row_h // 2 + 4}" '
            f'text-anchor="end" fill="#cdd6f4">{_esc(sig.name)}</text>'
        )
        # Waveform path
        if sig.is_bus:
            parts.append(_svg_bus_path(sig, wave.end_time, name_w, y, row_h, wave_w, color))
        else:
            parts.append(_svg_bit_path(sig, wave.end_time, name_w, y, row_h, wave_w, color))

    parts.append("</svg>")
    return "\n".join(parts)


def _svg_time_axis(name_w: int, svg_w: int, svg_h: int,
                   total_ns: float, wave_w: int) -> str:
    lines = [f'<line x1="{name_w}" y1="28" x2="{svg_w}" y2="28" '
             f'stroke="#45475a" stroke-width="1"/>']
    step_ns = _nice_step(total_ns, target_ticks=10)
    t = 0.0
    while t <= total_ns:
        x = name_w + int(t / total_ns * wave_w)
        lines.append(f'<line x1="{x}" y1="20" x2="{x}" y2="{svg_h}" '
                     f'stroke="#45475a" stroke-width="0.5" stroke-dasharray="3,4"/>')
        label = f"{t:.0f}ns" if t == int(t) else f"{t:.1f}ns"
        lines.append(f'<text x="{x+2}" y="18" fill="#6c7086" font-size="9">{_esc(label)}</text>')
        t += step_ns
    return "\n".join(lines)


def _nice_step(total: float, target_ticks: int) -> float:
    raw = total / target_ticks
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for mult in (1, 2, 5, 10):
        if mag * mult >= raw:
            return mag * mult
    return raw


def _svg_bit_path(sig: WaveSignal, end_time: int, x0: int, y: int,
                  row_h: int, wave_w: int, color: str) -> str:
    hi = y + 3
    lo = y + row_h - 3
    mid = (hi + lo) // 2

    path_pts: list[str] = []
    prev_v = "x"

    events = sig.tv + [(end_time, sig.tv[-1][1] if sig.tv else "x")]
    for ts, v in events:
        px = x0 + int(ts / end_time * wave_w) if end_time else x0
        if prev_v == "x":
            py = mid
        else:
            py = hi if prev_v == "1" else lo
        if not path_pts:
            path_pts.append(f"M {px} {py}")
        else:
            path_pts.append(f"L {px} {py}")
        # vertical transition
        new_py = hi if v == "1" else (lo if v == "0" else mid)
        if new_py != py:
            path_pts.append(f"L {px} {new_py}")
        prev_v = v

    d = " ".join(path_pts)
    return (f'<path d="{d}" stroke="{color}" stroke-width="1.5" '
            f'fill="none" stroke-linejoin="round"/>')


def _svg_bus_path(sig: WaveSignal, end_time: int, x0: int, y: int,
                  row_h: int, wave_w: int, color: str) -> str:
    hi = y + 3
    lo = y + row_h - 3
    tw = _TRANSITION_W

    parts: list[str] = []
    tv = sig.tv + [(end_time, sig.tv[-1][1] if sig.tv else "x")]

    for i in range(len(tv) - 1):
        ts, v = tv[i]
        ts_next = tv[i + 1][0]
        x1 = x0 + int(ts / end_time * wave_w) if end_time else x0
        x2 = x0 + int(ts_next / end_time * wave_w) if end_time else x0

        if x2 <= x1:
            continue

        # Parallelogram shape
        top = f"M {x1+tw} {hi} L {x2} {hi} L {x2-tw} {lo} L {x1} {lo} Z"
        hex_val = _esc(_bin_to_hex(v))
        cx = (x1 + x2) // 2
        cy = y + row_h // 2 + 4

        parts.append(f'<path d="{top}" stroke="{color}" stroke-width="1" '
                     f'fill="{color}22"/>')
        if x2 - x1 > 20:
            parts.append(f'<text x="{cx}" y="{cy}" text-anchor="middle" '
                         f'fill="{color}" font-size="10">{hex_val}</text>')

    return "\n".join(parts)


# ── Convenience: load + render ────────────────────────────────────────────────

def vcd_to_svg(vcd_path: str) -> str:
    """Parse a VCD file and return an SVG string."""
    wave = parse_vcd(vcd_path)
    return render_svg(wave)


def vcd_to_ascii(vcd_path: str, cols: int = 100) -> str:
    """Parse a VCD file and return an ASCII waveform string."""
    wave = parse_vcd(vcd_path)
    return render_ascii(wave, cols=cols)
