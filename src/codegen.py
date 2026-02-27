"""
:file: codegen.py
:author: Paulo Santos (@wkhadgar)
:brief: C code generation for CLUTGen LUT output.
:version: 0.1
:date: 27-02-2026

:copyright: Copyright (c) 2026
"""

from __future__ import annotations

import datetime
from pathlib import Path

from src.config import GenMethod
from src.sensor import VirtualSensor

LUT_LINE_WIDTH = 95


class LUTBuilder:
    def __init__(
        self,
        out_path: Path,
        sensor: VirtualSensor,
        code_name: str,
        description: str,
        *,
        output_type: str,
        method: GenMethod,
    ):
        """
        Builds C LUT strings from a virtual sensor's interpolated data.

        :param out_path: Output directory path.
        :param sensor: Virtual sensor to generate data from.
        :param output_type: C type used in the generated output.
        :param method: Interpolation method to use.
        """
        self.sensor = sensor
        self.var_size_bits: int = int(
            output_type.removeprefix("u").removeprefix("int").removesuffix("_t")
        )
        self.code_name: str = code_name
        self.description: str = description
        self.type_str: str = f"const {output_type}"
        self.out_dir = out_path

        if output_type.startswith("u"):
            max_int = (2**self.var_size_bits) - 1
            min_int = 0
        else:
            max_int = (2 ** (self.var_size_bits - 1)) - 1
            min_int = -max_int

        self.interpolated_points = self.sensor.data_gen(method, max_val=max_int, min_val=min_int)

    def __get_lut_values_str(self) -> str:
        """
        Formats the LUT values as a C array initializer string.

        :return: Formatted C array initializer.
        """
        line_dim = 0
        output_str = ""

        for v in self.interpolated_points.values():
            current_temp_str = f"{v}, "

            if (line_dim + len(current_temp_str)) >= LUT_LINE_WIDTH:
                current_temp_str = "\n\t" + current_temp_str
                line_dim = 0

            output_str += current_temp_str
            line_dim += len(current_temp_str)

        return "{\n\t" + output_str + "\n};\n\n"

    def get_lut_definition(self) -> str:
        """
        Generates a syntactically correct C string for the .c file definition.

        :param code_name: Name used in the code for the generated LUT.
        :return: Formatted string for use in definition.
        """
        return (
            f"{self.type_str} {self.code_name}_lut[{2**self.sensor.resolution}] = "
            + self.__get_lut_values_str()
        )

    def get_lut_declaration(self) -> str:
        """
        Generates a documented C declaration string for external use in code.

        :param code_name: Name used in the code for the generated LUT.
        :param doc_name: Natural language name for the generated LUT.
        :return: Formatted string for use in declaration.
        """
        docs = (
            "/**\n"
            f" * @brief LUT for {self.description} measurements.\n"
            " *\n"
            f" * @note The value read by the ADC is scaled to {self.sensor.resolution} bits "
            f"(0 to {(2**self.sensor.resolution) - 1}), and used as an index for this LUT.\n"
            " */"
        )
        return (
            docs
            + f"\nextern {self.type_str} {self.code_name}_lut[{2**self.sensor.resolution}];\n\n"
        )


def get_header_h(filename: str) -> str:
    """
    Generates the .h file header with include guard and standard includes.

    :param filename: Base name of the generated file.
    :return: Formatted header string.
    """
    return (
        "/**\n"
        f" * @file {filename}.h\n"
        " * @author CLUTGen <github.com/wkhadgar/clutgen>\n"
        " * @brief Organizes lookup tables to speed up sensor readings.\n"
        " * @note The code in this file is generated and should not be modified.\n"
        " * @version 0.1\n"
        f" * @date {datetime.datetime.now().strftime('%d-%m-%Y')}\n"
        " *\n"
        " */\n"
        "\n"
        f"#ifndef {filename.upper()}_H\n"
        f"#define {filename.upper()}_H\n"
        "\n"
        "#include <stdint.h>\n\n"
    )


def get_footer_h(filename: str) -> str:
    """
    Generates the .h file footer closing the include guard.

    :param filename: Base name of the generated file.
    :return: Formatted footer string.
    """

    return f"\n#endif /* {filename.upper()}_H */\n"


def get_header_c(filename: str) -> str:
    """
    Generates the .c file header with the corresponding .h include.

    :param filename: Base name of the generated file.
    :return: Formatted header string.
    """
    return (
        "/**\n"
        f" * @file {filename}.c\n"
        " * @author CLUTGen <github.com/wkhadgar/clutgen>\n"
        " * @brief Defines lookup tables to speed up sensor readings.\n"
        " * @note The code in this file is generated and should not be modified.\n"
        " * @version 0.1\n"
        f" * @date {datetime.datetime.now().strftime('%d-%m-%Y')}\n"
        " *\n"
        " */\n"
        "\n"
        f'#include "{filename}.h"\n\n'
    )
