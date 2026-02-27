"""
:file: generator.py
:author: Paulo Santos (@wkhadgar)
:brief: LUT generation orchestration.
:version: 0.1
:date: 27-02-2026

:copyright: Copyright (c) 2026
"""

from __future__ import annotations

import csv
from pathlib import Path

import tomllib

from src import codegen
from src.codegen import LUTBuilder
from src.config import GenMethod, LUTConfig
from src.sensor import VirtualSensor


def _parse_toml_config(gen_toml: Path, default_method: GenMethod) -> LUTConfig | None:
    """
    Parses a single TOML config file and its associated CSV.

    :param gen_toml: Path to the TOML config file.
    :param default_method: Fallback interpolation method if not specified in TOML.
    :param gen_preview: Fallback preview flag if not specified in TOML.
    :return: Parsed LUTConfig, or None if the config is invalid.
    """
    with open(gen_toml, "rb") as toml:
        lut_descriptor = tomllib.load(toml)

    code_name: str = lut_descriptor["name"]
    description: str = lut_descriptor["description"]
    resolution: int = int(lut_descriptor["table_resolution_bits"])
    output_type: str = lut_descriptor["lut_type"]
    samples: Path = Path(lut_descriptor["samples_csv"])
    overwrite_method = lut_descriptor.get("interpolation", default_method.value)

    if samples.suffix != ".csv":
        print(f"-- Invalid samples file '{samples}' for {code_name}. Must be a CSV.")
        return None

    try:
        path = (gen_toml.parent / samples).resolve(strict=True)
    except FileNotFoundError:
        try:
            path = samples.resolve(strict=True)
        except FileNotFoundError:
            print(f"-- CSV not found for {code_name}: '{samples}'")
            return None

    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        csv_header = next(reader)
        if csv_header[0] != "raw" or csv_header[1] != "calibration":
            print(f"-- {path} schema must be: 'raw,calibration'. Skipping.")
            return None
        raw_values, calibration_values = zip(*list(reader), strict=True)

    return LUTConfig(
        code_name=code_name,
        description=description,
        resolution=resolution,
        output_type=output_type,
        method=GenMethod(overwrite_method),
        raw_values=raw_values,
        calibration_values=calibration_values,
    )


def parse_configs(in_files: list[Path], default_method: GenMethod) -> list[LUTConfig]:
    tomls = [f.resolve(strict=True) for f in in_files if f.suffix == ".toml"]
    return [c for toml in tomls if (c := _parse_toml_config(toml, default_method)) is not None]


def generate(in_files: list[Path], out_dir: Path, filename: str, method: GenMethod):
    out_path_c = out_dir / (filename + ".c")
    out_path_h = out_dir / (filename + ".h")

    print("-- Running scripts to generate LUTs")

    calibration_data_tomls = [f.resolve(strict=True) for f in in_files if f.suffix == ".toml"]

    if not calibration_data_tomls:
        print("-- No configuration TOMLs found.")
        return

    luts_c = []
    luts_h = []

    for gen_toml in calibration_data_tomls:
        config = _parse_toml_config(gen_toml, method)
        if config is None:
            continue

        sensor = VirtualSensor(
            {
                int(raw): int(val)
                for raw, val in zip(config.raw_values, config.calibration_values, strict=True)
            },
            resolution=config.resolution,
        )

        print(f"-- Generating {config.code_name} LUT...")
        builder = LUTBuilder(
            out_dir,
            sensor,
            code_name=config.code_name,
            description=config.description,
            output_type=config.output_type,
            method=config.method,
        )
        luts_c.append(builder.get_lut_definition())
        luts_h.append(builder.get_lut_declaration())

    out_dir.mkdir(exist_ok=True, parents=True)

    with open(out_path_c, "w", encoding="utf8") as out:
        print(f"-- Generating source {filename}.c...")
        out.write(codegen.get_header_c(filename))
        for lut in luts_c:
            out.write(lut)

    with open(out_path_h, "w", encoding="utf8") as out:
        print(f"-- Generating header {filename}.h...")
        out.write(codegen.get_header_h(filename))
        for lut in luts_h:
            out.write(lut)
        out.write(codegen.get_footer_h(filename))

    print("-- LUTs generated successfully.")
