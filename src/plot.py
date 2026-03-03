"""
:file: plot.py
:author: Paulo Santos (@wkhadgar)
:brief: Interactive LUT exploration plots.
:version: 0.1
:date: 27-02-2026

:copyright: Copyright (c) 2026
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from src.config import GenMethod, LUTConfig
from src.sensor import VirtualSensor

pio.templates.default = "seaborn"

_COLORS = [
    "#4C72B0",  # blue     — linear
    "#DD8452",  # orange   — splines
    "#55A868",  # green    — polynomial
    "#C44E52",  # reddish  — piecewise
    "#8172B3",  # purple   — idw
]
_METHODS = list(GenMethod)


def _get_type_bounds(output_type: str) -> tuple[int, int, int]:
    """
    Computes the min/max integer bounds for a given C type string.

    :param output_type: C type string (e.g. 'int16_t', 'uint8_t').
    :return: (max_int, min_int, var_size_bits) tuple.
    """
    var_size_bits = int(output_type.removeprefix("u").removeprefix("int").removesuffix("_t"))

    if output_type.startswith("u"):
        return (2**var_size_bits) - 1, 0, var_size_bits

    max = (2 ** (var_size_bits - 1)) - 1

    return max, -max, var_size_bits


def _truncate(text: str, max_len: int = 32) -> str:
    """Truncates a string to max_len characters, appending ellipsis if needed."""
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _build_sensor_traces(config: LUTConfig) -> list[go.Scatter]:
    """
    Builds all traces for a single sensor — one line per method plus calibration scatter.

    :param config: Parsed LUTConfig for this sensor.
    :return: List of scatter trace objects.
    """
    max_int, min_int, _ = _get_type_bounds(config.output_type)
    traces = []

    for i, method in enumerate(_METHODS):
        sensor = VirtualSensor(
            {
                int(raw): int(val)
                for raw, val in zip(config.raw_values, config.calibration_values, strict=True)
            },
            resolution=config.resolution,
        )
        lut = sensor.data_gen(method, max_val=max_int, min_val=min_int)

        traces.append(
            go.Scatter(
                x=list(lut.keys()),
                y=list(lut.values()),
                mode="lines",
                name=method.value,
                line=dict(color=_COLORS[i], width=1.5),
                opacity=0.85,
                legendgroup=method.value,
                hovertemplate="<br>%{y}<extra>" + method.value + "</extra>",
                visible=True,
            )
        )

    cal_x = [int(r) for r in config.raw_values]
    cal_y = [int(v) for v in config.calibration_values]

    traces.append(
        go.Scatter(
            x=cal_x,
            y=cal_y,
            mode="markers",
            name="calibration samples",
            marker=dict(
                color="crimson",
                size=7,
                symbol="circle",
                line=dict(width=0.8, color="white"),
            ),
            hovertemplate="<br>%{y}<extra>samples</extra>",
            visible=True,
        )
    )

    return traces


def show_interactive_plot(configs: list[LUTConfig]) -> None:
    """
    Opens a single interactive figure with a dropdown to switch between sensors.
    Each sensor shows all interpolation methods overlaid against calibration points.

    :param configs: List of parsed LUTConfig instances.
    """
    if not configs:
        print("-- No valid CLUTGen configs to preview.")
        return

    traces_per_sensor_count = len(_METHODS) + 1  # methods + calibration scatter

    fig = go.Figure()

    for sensor_idx, config in enumerate(configs):
        for trace in _build_sensor_traces(config):
            trace.visible = sensor_idx == 0
            fig.add_trace(trace)

    buttons = []
    for sensor_idx, config in enumerate(configs):
        visibility = []
        for s_idx in range(len(configs)):
            visibility += [s_idx == sensor_idx] * traces_per_sensor_count

        plot_description = _truncate(config.description.capitalize(), max_len=50)

        plot_title = (
            f"CLUTGen Preview - {plot_description} @ {config.resolution}-bit, {config.output_type}"
        )

        buttons.append(
            dict(
                label=_truncate(config.description.capitalize()),
                method="update",
                args=[
                    {"visible": visibility},
                    {
                        "title.text": plot_title,
                        "yaxis.title.text": "LUT value",
                    },
                ],
            )
        )

    this_plot_data = buttons[0]["args"][1]
    fig.update_layout(
        paper_bgcolor="ghostwhite",
        title=dict(
            text=this_plot_data["title.text"],
            subtitle=dict(text=""),
            x=0.5,
            xanchor="center",
            y=0.98,
            yanchor="top",
            font=dict(size=18, color="#2d2d2d"),
        ),
        xaxis=dict(
            title="ADC raw value",
            title_font=dict(size=13, color="#444444"),
            tickfont=dict(color="#444444"),
            gridwidth=1,
            gridcolor="#C8C8DA",
            griddash="dot",
            autorange=True,
        ),
        yaxis=dict(
            title=this_plot_data["yaxis.title.text"],
            title_font=dict(size=13, color="#444444"),
            tickfont=dict(color="#444444"),
            gridwidth=1,
            gridcolor="#C8C8DA",
            griddash="dot",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(20, 20, 20, 0.85)",
            font_color="white",
            bordercolor="rgba(0,0,0,0)",
            font_size=12,
        ),
        font=dict(family="Roboto, Arial, sans-serif"),
        legend=dict(
            groupclick="toggleitem",
            bordercolor="#B0B0C8",
            borderwidth=1,
            x=1.003,
            xanchor="left",
            y=1.0,
            yanchor="top",
        ),
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                showactive=True,
                bordercolor="#B0B0C8",
                font=dict(color="#2d2d2d"),
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom",
            )
        ]
        if len(configs) > 1
        else [],
        margin=dict(t=80, l=5, r=0, b=60),
        autosize=True,
    )

    fig.show(
        config=dict(
            displaylogo=False,
        )
    )
