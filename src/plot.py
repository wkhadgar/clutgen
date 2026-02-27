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

from src.config import GenMethod, LUTConfig
from src.sensor import VirtualSensor

_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
_METHODS = list(GenMethod)


def _build_sensor_traces(config: LUTConfig) -> list[go.Scatter]:
    """
    Builds all traces for a single sensor — one line per method plus calibration scatter.

    :param config: Parsed LUTConfig for this sensor.
    :return: List of scatter trace objects.
    """
    output_type = config.output_type
    var_size_bits = int(output_type.removeprefix("u").removeprefix("int").removesuffix("_t"))
    if output_type.startswith("u"):
        max_int = (2**var_size_bits) - 1
        min_int = 0
    else:
        max_int = (2 ** (var_size_bits - 1)) - 1
        min_int = -max_int

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
                line=dict(color=_COLORS[i]),
                legendgroup=method.value,
                hovertemplate="raw: %{x}<br>value: %{y}<extra>" + method.value + "</extra>",
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
            name="calibration points",
            marker=dict(color="red", size=8, symbol="circle"),
            hovertemplate="raw: %{x}<br>calibration: %{y}<extra>calibration</extra>",
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

        buttons.append(
            dict(
                label=config.description.capitalize(),
                method="update",
                args=[
                    {"visible": visibility},
                    {
                        "title.text": f"CLUTGen Preview — {config.description.capitalize()} "
                        f"@ ({config.resolution}-bit, {config.output_type})",
                        "yaxis.title.text": "LUT value",
                    },
                ],
            )
        )

    fig.update_layout(
        title=dict(
            text=f"CLUTGen Preview — {configs[0].description.capitalize()} "
            f"({configs[0].resolution}-bit, {configs[0].output_type})",
            x=0.5,
            xanchor="center",
            y=0.98,
            yanchor="top",
        ),
        xaxis=dict(title="ADC raw value"),
        yaxis=dict(title=f"LUT value ({configs[0].output_type})"),
        hovermode="x unified",
        legend=dict(groupclick="toggleitem"),
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.0,
                yanchor="top",
            )
        ]
        if len(configs) > 1
        else [],
        margin=dict(t=100, l=60, r=40, b=60),
        autosize=True,
    )

    fig.show()
