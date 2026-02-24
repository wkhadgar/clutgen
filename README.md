---
# C Lookup Table (LUT) Generator

CLUTGen automates the creation of **Look-Up Tables** for embedded systems, specifically for converting raw ADC (Analog-to-Digital Converter) readings into calibrated physical units (like temperature, pressure, or distance).

### Features

* **Curve Fitting:** Automatically find your fit from many algorithms.
    * Linear Interpolation
    * Cubic Splines
    * Polynomial Interpolation (up to 7th degree)
    * Piecewise Interpolation
* **Visual Preview:** Generates plots to compare calibration data against the calculated LUT.
* **C Code Generation:** Outputs production-ready `.c` and `.h` files with Doxygen-style comments.

### Requirements

* Python 3.10+
* `numpy`, `pandas`, `matplotlib`, `pyyaml`, `openpyxl` (for Excel support)

### Usage

```bash
# From the root of the repository
pip install .
# Generate LUTs with cubic splines fit for every configuration yaml in the given paths.
clutgen -s -i ./examples/calibration/*.y*ml ./examples/temperature_copy.yml
```

### YAML Configuration Template

Create a table mapping your POIs with the given schema, where `raw` is the measured ADC raw value, and `calibration` is the desired output for the LUT at that given `raw` value:
```csv
raw,calibration
```

With your CSV table done (or Excel one), create a configuration YAML:

```yaml
# temperature.yaml

name: "temp_sensor"                  # Used for variable names (e.g., temp_sensor_lut)
description: "ambient temperature"   # Used for documentation and plot titles
table_resolution_bits: 12            # Resolution (e.g., 12 bits = 4096 entries)
lut_type: "int16_t"                  # C type (int8_t, uint16_t, etc.)
 
generator: "./data/calibration.csv"  # Path to CSV/Excel with 'raw' and 'calibration' columns. Global or relative to this file.

```
