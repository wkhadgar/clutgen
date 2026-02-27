"""
:file: test_codegen.py
:brief: Tests for LUTBuilder and C code generation helpers.
"""

import pytest
from conftest import MAX_RAW, RESOLUTION

from src.codegen import LUT_LINE_WIDTH, LUTBuilder, get_footer_h, get_header_c, get_header_h
from src.config import GenMethod
from src.sensor import VirtualSensor


def make_builder(tmp_path, output_type="int16_t", method=GenMethod.LINEAR, samples=None):
    if samples is None:
        samples = {0: 0, 128: 64, 255: 127}
    sensor = VirtualSensor(samples, resolution=RESOLUTION)
    return LUTBuilder(
        tmp_path,
        sensor,
        code_name="test_sensor",
        description="test sensor",
        output_type=output_type,
        method=method,
    )


class TestLUTBuilderBounds:
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
        builder = LUTBuilder(
            tmp_path,
            sensor,
            code_name="s",
            description="s",
            output_type=output_type,
            method=GenMethod.LINEAR,
        )
        values = list(builder.interpolated_points.values())
        assert max(values) <= expected_max
        assert min(values) >= expected_min

    def test_unsigned_type_str(self, tmp_path):
        builder = make_builder(tmp_path, output_type="uint8_t")
        assert "const uint8_t" in builder.type_str

    def test_signed_type_str(self, tmp_path):
        builder = make_builder(tmp_path, output_type="int8_t")
        assert "const int8_t" in builder.type_str


class TestLUTDefinition:
    def test_contains_code_name(self, tmp_path):
        builder = make_builder(tmp_path)
        assert "test_sensor_lut" in builder.get_lut_definition()

    def test_contains_correct_size(self, tmp_path):
        builder = make_builder(tmp_path)
        assert f"[{MAX_RAW}]" in builder.get_lut_definition()

    def test_contains_type_str(self, tmp_path):
        builder = make_builder(tmp_path)
        assert "const int16_t" in builder.get_lut_definition()

    def test_line_wrapping_respected(self, tmp_path):
        builder = make_builder(tmp_path)
        definition = builder.get_lut_definition()
        for line in definition.splitlines():
            assert len(line) <= LUT_LINE_WIDTH + len("\t")  # allow tab indent


class TestLUTDeclaration:
    def test_contains_extern(self, tmp_path):
        builder = make_builder(tmp_path)
        assert "extern" in builder.get_lut_declaration()

    def test_contains_code_name(self, tmp_path):
        builder = make_builder(tmp_path)
        assert "test_sensor_lut" in builder.get_lut_declaration()

    def test_contains_doxygen_brief(self, tmp_path):
        builder = make_builder(tmp_path)
        assert "@brief" in builder.get_lut_declaration()

    def test_contains_doxygen_note(self, tmp_path):
        builder = make_builder(tmp_path)
        assert "@note" in builder.get_lut_declaration()

    def test_contains_description(self, tmp_path):
        builder = make_builder(tmp_path)
        assert "test sensor" in builder.get_lut_declaration()

    def test_contains_resolution(self, tmp_path):
        builder = make_builder(tmp_path)
        assert str(RESOLUTION) in builder.get_lut_declaration()


class TestHeaderFooter:
    def test_header_h_include_guard(self):
        result = get_header_h("lookup_tables")
        assert "#ifndef LOOKUP_TABLES_H" in result
        assert "#define LOOKUP_TABLES_H" in result

    def test_header_h_includes_stdint(self):
        assert "#include <stdint.h>" in get_header_h("lookup_tables")

    def test_header_h_filename_in_file_tag(self):
        assert "lookup_tables.h" in get_header_h("lookup_tables")

    def test_header_h_uppercases_underscored_name(self):
        result = get_header_h("my_sensor_luts")
        assert "#ifndef MY_SENSOR_LUTS_H" in result

    def test_header_c_includes_header(self):
        assert '#include "lookup_tables.h"' in get_header_c("lookup_tables")

    def test_header_c_filename_in_file_tag(self):
        assert "lookup_tables.c" in get_header_c("lookup_tables")

    def test_footer_closes_include_guard(self):
        result = get_footer_h("lookup_tables")
        assert "#endif" in result
        assert "LOOKUP_TABLES_H" in result

    def test_header_footer_pair_consistent(self):
        name = "my_luts"
        header = get_header_h(name)
        footer = get_footer_h(name)
        guard = "MY_LUTS_H"
        assert f"#ifndef {guard}" in header
        assert guard in footer
