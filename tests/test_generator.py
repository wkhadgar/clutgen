"""
:file: test_generator.py
:brief: Tests for TOML parsing, config collection, and full generation pipeline.
"""

import textwrap

import pytest
from conftest import RESOLUTION

from src.config import GenMethod, LUTConfig
from src.generator import _parse_toml_config, generate, parse_configs


class TestParseTomlConfig:
    def test_valid_config_returns_lutconfig(self, tmp_toml):
        config = _parse_toml_config(tmp_toml, GenMethod.LINEAR)
        assert isinstance(config, LUTConfig)

    def test_fields_parsed_correctly(self, tmp_toml):
        config = _parse_toml_config(tmp_toml, GenMethod.LINEAR)
        assert config is not None
        assert config.code_name == "test_sensor"
        assert config.resolution == RESOLUTION
        assert config.output_type == "int16_t"
        assert config.method == GenMethod.LINEAR

    def test_toml_interpolation_overrides_default(self, tmp_toml_with_method):
        config = _parse_toml_config(tmp_toml_with_method, GenMethod.LINEAR)
        assert config is not None
        assert config.method == GenMethod.SPLINES

    def test_default_method_used_when_not_in_toml(self, tmp_toml):
        config = _parse_toml_config(tmp_toml, GenMethod.IDW)
        assert config is not None
        assert config.method == GenMethod.IDW

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
        assert _parse_toml_config(toml_path, GenMethod.LINEAR) is None

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
        assert _parse_toml_config(toml_path, GenMethod.LINEAR) is None

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
        assert _parse_toml_config(toml_path, GenMethod.LINEAR) is None

    def test_missing_required_key_raises(self, tmp_path):
        toml_path = tmp_path / "sensor.toml"
        toml_path.write_text(
            textwrap.dedent("""\
                name = "s"
                description = "s"
                lut_type = "int16_t"
                samples_csv = "samples.csv"
            """)
        )
        with pytest.raises(KeyError):
            _parse_toml_config(toml_path, GenMethod.LINEAR)

    def test_absolute_csv_path(self, tmp_path):
        csv_path = tmp_path / "samples.csv"
        csv_path.write_text("raw,calibration\n0,0\n255,100\n")
        toml_path = tmp_path / "sensor.toml"
        toml_path.write_text(
            textwrap.dedent(f"""\
                name = "s"
                description = "s"
                table_resolution_bits = {RESOLUTION}
                lut_type = "int16_t"
                samples_csv = "{csv_path}"
            """)
        )
        config = _parse_toml_config(toml_path, GenMethod.LINEAR)
        assert config is not None

    def test_invalid_interpolation_value_raises(self, tmp_path):
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
                interpolation = "cubic"
            """)
        )
        with pytest.raises(ValueError):
            _parse_toml_config(toml_path, GenMethod.LINEAR)


class TestParseConfigs:
    def test_returns_list_of_lutconfigs(self, tmp_toml):
        configs = parse_configs([tmp_toml], GenMethod.LINEAR)
        assert isinstance(configs, list)
        assert all(isinstance(c, LUTConfig) for c in configs)

    def test_valid_tomls_all_returned(self, tmp_toml, tmp_second_toml):
        configs = parse_configs([tmp_toml, tmp_second_toml], GenMethod.LINEAR)
        assert len(configs) == 2

    def test_invalid_toml_skipped(self, tmp_path, tmp_toml):
        bad_toml = tmp_path / "bad.toml"
        bad_toml.write_text(
            textwrap.dedent(f"""\
                name = "bad"
                description = "bad"
                table_resolution_bits = {RESOLUTION}
                lut_type = "int16_t"
                samples_csv = "nonexistent.csv"
            """)
        )
        configs = parse_configs([tmp_toml, bad_toml], GenMethod.LINEAR)
        assert len(configs) == 1
        assert configs[0].code_name == "test_sensor"

    def test_non_toml_files_skipped(self, tmp_path, tmp_toml):
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("not a toml")
        configs = parse_configs([tmp_toml, txt_file], GenMethod.LINEAR)
        assert len(configs) == 1

    def test_empty_list_returns_empty(self):
        configs = parse_configs([], GenMethod.LINEAR)
        assert configs == []

    def test_all_invalid_returns_empty(self, tmp_path):
        bad_toml = tmp_path / "bad.toml"
        bad_toml.write_text(
            textwrap.dedent(f"""\
                name = "bad"
                description = "bad"
                table_resolution_bits = {RESOLUTION}
                lut_type = "int16_t"
                samples_csv = "nonexistent.csv"
            """)
        )
        configs = parse_configs([bad_toml], GenMethod.LINEAR)
        assert configs == []


class TestGenerate:
    def test_creates_c_and_h_files(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR)
        assert (tmp_path / "lookup_tables.c").exists()
        assert (tmp_path / "lookup_tables.h").exists()

    def test_custom_filename(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "sensor_luts", GenMethod.LINEAR)
        assert (tmp_path / "sensor_luts.c").exists()
        assert (tmp_path / "sensor_luts.h").exists()

    def test_h_has_include_guard(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR)
        content = (tmp_path / "lookup_tables.h").read_text()
        assert "#ifndef LOOKUP_TABLES_H" in content
        assert "#define LOOKUP_TABLES_H" in content
        assert "#endif" in content

    def test_h_includes_stdint(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR)
        content = (tmp_path / "lookup_tables.h").read_text()
        assert "#include <stdint.h>" in content

    def test_c_includes_header(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR)
        content = (tmp_path / "lookup_tables.c").read_text()
        assert '#include "lookup_tables.h"' in content

    def test_h_contains_extern_declaration(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR)
        content = (tmp_path / "lookup_tables.h").read_text()
        assert "extern" in content
        assert "test_sensor_lut" in content

    def test_c_contains_array_definition(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR)
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
        generate([tmp_toml, bad_toml], tmp_path, "lookup_tables", GenMethod.LINEAR)
        content_h = (tmp_path / "lookup_tables.h").read_text()
        assert "test_sensor_lut" in content_h
        assert "bad_sensor_lut" not in content_h

    def test_multiple_tomls_all_in_output(self, tmp_path, tmp_toml, tmp_second_toml):
        generate([tmp_toml, tmp_second_toml], tmp_path, "lookup_tables", GenMethod.LINEAR)
        content_h = (tmp_path / "lookup_tables.h").read_text()
        assert "test_sensor_lut" in content_h
        assert "pressure_sensor_lut" in content_h

    def test_no_tomls_skips_file_creation(self, tmp_path):
        generate([], tmp_path, "lookup_tables", GenMethod.LINEAR)
        assert not (tmp_path / "lookup_tables.c").exists()
        assert not (tmp_path / "lookup_tables.h").exists()

    def test_no_preview_directory_created(self, tmp_path, tmp_toml):
        generate([tmp_toml], tmp_path, "lookup_tables", GenMethod.LINEAR)
        assert not (tmp_path / "preview").exists()
