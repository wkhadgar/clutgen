"""
:file: config.py
:author: Paulo Santos (@wkhadgar)
:brief: Configuration data structures for CLUTGen.
:version: 0.2
:date: 27-02-2026

:copyright: Copyright (c) 2026
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GenMethod(Enum):
    LINEAR = "linear"
    SPLINES = "splines"
    POLYNOMIAL = "polynomial"
    PIECEWISE = "piecewise"
    IDW = "idw"


@dataclass
class LUTConfig:
    code_name: str
    description: str
    resolution: int
    output_type: str
    method: GenMethod
    raw_values: tuple[str, ...]
    calibration_values: tuple[str, ...]
