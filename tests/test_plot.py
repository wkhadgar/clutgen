"""
:file: test_plot.py
:brief: Tests for interactive Plotly plot generation.
"""

from conftest import RESOLUTION, SIMPLE_SAMPLES

from src.config import GenMethod, LUTConfig
from src.plot import show_interactive_plot


def make_config(name="test_sensor", doc_name="test sensor", output_type="int16_t"):
    raw, cal = zip(*SIMPLE_SAMPLES.items(), strict=False)
    return LUTConfig(
        code_name=name,
        description=doc_name,
        resolution=RESOLUTION,
        output_type=output_type,
        method=GenMethod.LINEAR,
        raw_values=tuple(str(r) for r in raw),
        calibration_values=tuple(str(c) for c in cal),
    )


class TestShowInteractivePlot:
    def test_empty_configs_does_not_crash(self, capsys):
        show_interactive_plot([])
        captured = capsys.readouterr()
        assert "No valid CLUTGen configs" in captured.out

    def test_single_config_builds_figure(self, monkeypatch):
        shown = []
        monkeypatch.setattr("plotly.graph_objects.Figure.show", lambda self: shown.append(self))
        show_interactive_plot([make_config()])
        assert len(shown) == 1

    def test_multiple_configs_single_figure(self, monkeypatch):
        shown = []
        monkeypatch.setattr("plotly.graph_objects.Figure.show", lambda self: shown.append(self))
        configs = [
            make_config("temp_sensor", "temperature"),
            make_config("pressure_sensor", "pressure"),
        ]
        show_interactive_plot(configs)
        assert len(shown) == 1

    def test_single_config_no_dropdown(self, monkeypatch):
        captured_fig = []
        monkeypatch.setattr(
            "plotly.graph_objects.Figure.show",
            lambda self: captured_fig.append(self),
        )
        show_interactive_plot([make_config()])
        fig = captured_fig[0]
        assert fig.layout.updatemenus == ()

    def test_multiple_configs_has_dropdown(self, monkeypatch):
        captured_fig = []
        monkeypatch.setattr(
            "plotly.graph_objects.Figure.show",
            lambda self: captured_fig.append(self),
        )
        configs = [
            make_config("temp_sensor", "temperature"),
            make_config("pressure_sensor", "pressure"),
        ]
        show_interactive_plot(configs)
        fig = captured_fig[0]
        assert len(fig.layout.updatemenus) == 1
        assert len(fig.layout.updatemenus[0].buttons) == 2

    def test_trace_count_per_sensor(self, monkeypatch):
        """Each sensor contributes len(GenMethod) + 1 traces (methods + calibration)."""
        captured_fig = []
        monkeypatch.setattr(
            "plotly.graph_objects.Figure.show",
            lambda self: captured_fig.append(self),
        )
        configs = [
            make_config("temp_sensor", "temperature"),
            make_config("pressure_sensor", "pressure"),
        ]
        show_interactive_plot(configs)
        fig = captured_fig[0]
        expected = len(configs) * (len(GenMethod) + 1)
        assert len(fig.data) == expected

    def test_only_first_sensor_visible_initially(self, monkeypatch):
        captured_fig = []
        monkeypatch.setattr(
            "plotly.graph_objects.Figure.show",
            lambda self: captured_fig.append(self),
        )
        configs = [
            make_config("temp_sensor", "temperature"),
            make_config("pressure_sensor", "pressure"),
        ]
        show_interactive_plot(configs)
        fig = captured_fig[0]
        traces_per_sensor = len(GenMethod) + 1
        first_sensor_traces = fig.data[:traces_per_sensor]
        second_sensor_traces = fig.data[traces_per_sensor:]
        assert all(t.visible for t in first_sensor_traces)
        assert all(not t.visible for t in second_sensor_traces)

    def test_calibration_scatter_is_circle(self, monkeypatch):
        captured_fig = []
        monkeypatch.setattr(
            "plotly.graph_objects.Figure.show",
            lambda self: captured_fig.append(self),
        )
        show_interactive_plot([make_config()])
        fig = captured_fig[0]
        scatter = fig.data[-1]  # calibration is last trace per sensor
        assert scatter.marker.symbol == "circle"

    def test_unsigned_type_config(self, monkeypatch):
        shown = []
        monkeypatch.setattr("plotly.graph_objects.Figure.show", lambda self: shown.append(self))
        show_interactive_plot([make_config(output_type="uint16_t")])
        assert len(shown) == 1
