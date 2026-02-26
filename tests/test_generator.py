"""
:file: test_generator.py
:brief: Unit and integration tests for the CLUTGen generator module.
"""

import csv
import textwrap

import numpy as np
import pytest

from src.generator import (
    GenMethod,
    LUTBuilder,
    LUTConfig,
    VirtualSensor,
    _parse_toml_config,
    generate,
)

# ─── Fixtures ────────────────────────────────────────────────────────────────
RESOLUTION = 8  # small resolution for fast tests (256 entries)
MAX_RAW = 2**RESOLUTION

SIMPLE_SAMPLES = {
    0: 0,
    64: 32,
    128: 64,
    192: 96,
    255: 127,
}


@pytest.fixture
def simple_sensor():
    return VirtualSensor(SIMPLE_SAMPLES, resolution=RESOLUTION)


@pytest.fixture
def tmp_toml(tmp_path):
    """Creates a valid TOML + CSV pair and returns the TOML path."""
    csv_path = tmp_path / "samples.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["raw", "calibration"])
        for raw, cal in SIMPLE_SAMPLES.items():
            writer.writerow([raw, cal])

    toml_path = tmp_path / "sensor.toml"
    toml_path.write_text(
        textwrap.dedent(f"""\
            name = "test_sensor"
            description = "test sensor"
            table_resolution_bits = {RESOLUTION}
            lut_type = "int16_t"
            samples_csv = "samples.csv"
        """)
    )
    return toml_path


# ─── VirtualSensor ───────────────────────────────────────────────────────────
class TestVirtualSensor:
    def test_sorts_input(self):
        unsorted = {192: 96, 0: 0, 128: 64}
        sensor = VirtualSensor(unsorted, resolution=RESOLUTION)
        assert list(sensor.x) == sorted(unsorted.keys())

    def test_resolution_stored(self, simple_sensor):
        assert simple_sensor.resolution == RESOLUTION

    def test_does_not_mutate_on_linear(self, simple_sensor):
        x_before = simple_sensor.x.copy()
        y_before = simple_sensor.y.copy()
        simple_sensor.data_gen(GenMethod.LINEAR, max_val=127, min_val=-128)
        assert np.array_equal(simple_sensor.x, x_before)
        assert np.array_equal(simple_sensor.y, y_before)


# ─── data_gen — common contracts across all methods ──────────────────────────
class TestDataGen:
    @pytest.mark.parametrize("method", list(GenMethod))
    def test_output_has_correct_length(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=127, min_val=-128)
        assert len(result) == MAX_RAW

    @pytest.mark.parametrize("method", list(GenMethod))
    def test_keys_are_full_range(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=127, min_val=-128)
        assert list(result.keys()) == list(range(MAX_RAW))

    @pytest.mark.parametrize("method", list(GenMethod))
    def test_values_clamped_unsigned(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=255, min_val=0)
        assert all(0 <= v <= 255 for v in result.values())

    @pytest.mark.parametrize("method", list(GenMethod))
    def test_values_clamped_signed(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=127, min_val=-128)
        assert all(-128 <= v <= 127 for v in result.values())

    @pytest.mark.parametrize("method", list(GenMethod))
    def test_values_are_integers(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=127, min_val=-128)
        assert all(isinstance(v, int) for v in result.values())

    def test_linear_exact_at_known_points(self, simple_sensor):
        result = simple_sensor.data_gen(GenMethod.LINEAR, max_val=127, min_val=-128)
        for raw, cal in SIMPLE_SAMPLES.items():
            assert result[raw] == cal

    def test_idw_exact_at_known_points(self, simple_sensor):
        result = simple_sensor.data_gen(GenMethod.IDW, max_val=127, min_val=-128)
        for raw, cal in SIMPLE_SAMPLES.items():
            assert result[raw] == cal

    def test_piecewise_exact_at_known_points(self, simple_sensor):
        result = simple_sensor.data_gen(GenMethod.PIECEWISE, max_val=127, min_val=-128)
        assert result[0] == SIMPLE_SAMPLES[0]


# ─── LUTBuilder ──────────────────────────────────────────────────────────────
class TestLUTBuilder:
    @pytest.mark.parametrize(
        "output_type,expected_max,expected_min",
        [
            ("uint8_t", 255, 0),
            ("uint16_t", 65535, 0),
            ("int8_t", 127, -127),
            ("int16_t", 32767, -32767),
        ],
    )
    def test_type_bounds(self, tmp_path, output_type, expected_max, expected_min):
        sensor = VirtualSensor({0: -9999, 255: 9999}, resolution=RESOLUTION)
        builder = LUTBuilder(tmp_path, sensor, output_type=output_type, method=GenMethod.LINEAR)
        values = list(builder.interpolated_points.values())
        assert max(values) <= expected_max
        assert min(values) >= expected_min

    def test_definition_contains_code_name(self, tmp_path, simple_sensor):
        builder = LUTBuilder(
            tmp_path, simple_sensor, output_type="int16_t", method=GenMethod.LINEAR
        )
        definition = builder.get_lut_definition("my_sensor")
        assert "my_sensor_lut" in definition

    def test_definition_contains_correct_size(self, tmp_path, simple_sensor):
        builder = LUTBuilder(
            tmp_path, simple_sensor, output_type="int16_t", method=GenMethod.LINEAR
        )
        definition = builder.get_lut_definition("my_sensor")
        assert f"[{MAX_RAW}]" in definition

    def test_declaration_contains_extern(self, tmp_path, simple_sensor):
        builder = LUTBuilder(
            tmp_path, simple_sensor, output_type="int16_t", method=GenMethod.LINEAR
        )
        declaration = builder.get_lut_declaration("my_sensor", "my sensor")
        assert "extern" in declaration

    def test_declaration_contains_doxygen(self, tmp_path, simple_sensor):
        builder = LUTBuilder(
            tmp_path, simple_sensor, output_type="int16_t", method=GenMethod.LINEAR
        )
        declaration = builder.get_lut_declaration("my_sensor", "my sensor")
        assert "@brief" in declaration
        assert "@note" in declaration

    def test_preview_creates_png(self, tmp_path, simple_sensor):
        builder = LUTBuilder(
            tmp_path, simple_sensor, output_type="int16_t", method=GenMethod.LINEAR
        )
        builder.gen_table_preview_plot("my_sensor", "My Sensor")
        assert (tmp_path / "preview" / "my_sensor.png").exists()

    def test_preview_does_not_leave_open_figures(self, tmp_path, simple_sensor):
        import matplotlib.pyplot as plt

        builder = LUTBuilder(
            tmp_path, simple_sensor, output_type="int16_t", method=GenMethod.LINEAR
        )
        builder.gen_table_preview_plot("my_sensor", "My Sensor")
        assert plt.get_fignums() == []


# ─── _parse_toml_config ───────────────────────────────────────────────────────
class TestParseTomlConfig:
    def test_valid_config_returns_lutconfig(self, tmp_toml):
        config = _parse_toml_config(tmp_toml, GenMethod.LINEAR, False)
        assert isinstance(config, LUTConfig)

    def test_fields_parsed_correctly(self, tmp_toml):
        config = _parse_toml_config(tmp_toml, GenMethod.LINEAR, False)
        assert config is not None
        assert config.code_name == "test_sensor"
        assert config.resolution == RESOLUTION
        assert config.output_type == "int16_t"
        assert config.method == GenMethod.LINEAR

    def test_toml_interpolation_overrides_default(self, tmp_path):
        csv_path = tmp_path / "samples.csv"
        csv_path.write_text("raw,calibration\n0,0\n255,100\n")
        toml_path = tmp_path / "sensor.toml"
        toml_path.write_text(
            textwrap.dedent(f"""\
                name = "s"
                description = "s"
                table_resolution_bits = {RESOLUTION}
                lut_type = "int16_t"
                samples_csv = "samples.csv"
                interpolation = "splines"
            """)
        )
        config = _parse_toml_config(toml_path, GenMethod.LINEAR, False)
        assert config is not None
        assert config.method == GenMethod.SPLINES

    def test_toml_preview_overrides_default(self, tmp_path):
        csv_path = tmp_path / "samples.csv"
        csv_path.write_text("raw,calibration\n0,0\n255,100\n")
        toml_path = tmp_path / "sensor.toml"
        toml_path.write_text(
            textwrap.dedent(f"""\
                name = "s"
                description = "s"
                table_resolution_bits = {RESOLUTION}
                lut_type = "int16_t"
                samples_csv = "samples.csv"
                preview = true
            """)
        )
        config = _parse_toml_config(toml_path, GenMethod.LINEAR, False)
        assert config is not None
        assert config.preview is True

    def test_missing_csv_returns_none(self, tmp_path):
        toml_path = tmp_path / "sensor.toml"
        toml_path.write_text(
            textwrap.dedent(f"""\
                name = "s"
                description = "s"
                table_resolution_bits = {RESOLUTION}
                lut_type = "int16_t"
                samples_csv = "nonexistent.csv"
            """)
        )
        assert _parse_toml_config(toml_path, GenMethod.LINEAR, False) is None

    def test_invalid_csv_extension_returns_none(self, tmp_path):
        toml_path = tmp_path / "sensor.toml"
        toml_path.write_text(
            textwrap.dedent(f"""\
                name = "s"
                description = "s"
                table_resolution_bits = {RESOLUTION}
                lut_type = "int16_t"
                samples_csv = "samples.xlsx"
            """)
        )
        assert _parse_toml_config(toml_path, GenMethod.LINEAR, False) is None

    def test_wrong_csv_schema_returns_none(self, tmp_path):
        csv_path = tmp_path / "samples.csv"
        csv_path.write_text("voltage,output\n0,0\n255,100\n")
        toml_path = tmp_path / "sensor.toml"
        toml_path.write_text(
            textwrap.dedent(f"""\
                name = "s"
                description = "s"
                table_resolution_bits = {RESOLUTION}
                lut_type = "int16_t"
                samples_csv = "samples.csv"
            """)
        )
        assert _parse_toml_config(toml_path, GenMethod.LINEAR, False) is None

    def test_missing_required_key_raises(self, tmp_path):
        toml_path = tmp_path / "sensor.toml"
        toml_path.write_text(
            textwrap.dedent("""\
                name = "s"
                description = "s"
                lut_type = "int16_t"
                samples_csv = "samples.csv"
            """)
            # missing table_resolution_bits
        )
        with pytest.raises(KeyError):
            _parse_toml_config(toml_path, GenMethod.LINEAR, False)


# ─── generate() ──────────────────────────────────────────────────────────────
class TestGenerate:
    def test_creates_c_and_h_files(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        assert (tmp_path / "lookup_tables.c").exists()
        assert (tmp_path / "lookup_tables.h").exists()

    def test_h_has_include_guard(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        content = (tmp_path / "lookup_tables.h").read_text()
        assert "#ifndef LOOKUP_TABLES_H" in content
        assert "#define LOOKUP_TABLES_H" in content
        assert "#endif" in content

    def test_h_includes_stdint(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        content = (tmp_path / "lookup_tables.h").read_text()
        assert "#include <stdint.h>" in content

    def test_c_includes_header(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        content = (tmp_path / "lookup_tables.c").read_text()
        assert '#include "lookup_tables.h"' in content

    def test_h_contains_extern_declaration(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        content = (tmp_path / "lookup_tables.h").read_text()
        assert "extern" in content
        assert "test_sensor_lut" in content

    def test_c_contains_array_definition(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        content = (tmp_path / "lookup_tables.c").read_text()
        assert "test_sensor_lut" in content

    def test_invalid_toml_skipped_others_generated(self, tmp_path, tmp_toml):
        bad_toml = tmp_path / "bad.toml"
        bad_toml.write_text(
            textwrap.dedent(f"""\
                name = "bad_sensor"
                description = "bad"
                table_resolution_bits = {RESOLUTION}
                lut_type = "int16_t"
                samples_csv = "nonexistent.csv"
            """)
        )
        generate([tmp_toml, bad_toml], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        content_h = (tmp_path / "lookup_tables.h").read_text()
        assert "test_sensor_lut" in content_h
        assert "bad_sensor_lut" not in content_h

    def test_multiple_tomls_all_in_output(self, tmp_path, tmp_toml):
        csv2 = tmp_path / "pressure.csv"
        csv2.write_text("raw,calibration\n0,0\n255,100\n")
        toml2 = tmp_path / "pressure.toml"
        toml2.write_text(
            textwrap.dedent(f"""\
                name = "pressure_sensor"
                description = "pressure"
                table_resolution_bits = {RESOLUTION}
                lut_type = "uint16_t"
                samples_csv = "pressure.csv"
            """)
        )
        generate([tmp_toml, toml2], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        content_h = (tmp_path / "lookup_tables.h").read_text()
        assert "test_sensor_lut" in content_h
        assert "pressure_sensor_lut" in content_h

    def test_no_tomls_skips_file_creation(self, tmp_path):
        generate([], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        assert not (tmp_path / "lookup_tables.c").exists()
        assert not (tmp_path / "lookup_tables.h").exists()

    def test_preview_false_no_png_created(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR, False)
        assert not (tmp_path / "preview").exists()

    def test_preview_true_png_created(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR, True)
        assert (tmp_path / "preview" / "test_sensor.png").exists()
