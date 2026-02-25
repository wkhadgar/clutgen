---
# C Lookup Table (LUT) Generator

CLUTGen automates the creation of **Look-Up Tables** for embedded systems, specifically for converting raw ADC (Analog-to-Digital Converter) readings into calibrated physical units (like temperature, pressure, or distance).

### Features

* **Curve Fitting:** Automatically find your fit from many algorithms.
    * Linear Interpolation
    * Cubic Splines
    * Polynomial Interpolation (up to 7th degree)
    * Piecewise Interpolation
    * Inverse Distance Weighting
* **Visual Preview:** Generates plots to compare calibration data against the calculated LUT.
* **C Code Generation:** Outputs production-ready `.c` and `.h` files with Doxygen-style comments.

### Requirements

* Python 3.10+
* `numpy`, `matplotlib`

### Installation

CLUTGen is available on PyPI! To install it on your project, just run:
```bash
# On your virtual environment
pip install clutgen
```

Or, if you want to build it yourself, from the root of this repository:
```bash
# On your virtual environment
pip install .
```


### Usage

```bash
# Generate preview and LUTs with cubic splines fit for every configuration TOML in the given paths.
clutgen -sv ./examples/calibration/temperature.toml ./examples/temperature_copy.toml
```

### TOML Configuration Template

Create a CSV file mapping your POIs with the given schema, where `raw` is the measured ADC raw value, and `calibration` is the desired output for the LUT at that given `raw` value:
```csv
raw,calibration
```

With your table done, create a configuration TOML, e.g.:

```toml
# temperature.toml

name = "temp_sensor"                  # Used for variable names (e.g., temp_sensor_lut)
description = "ambient temperature"   # Used for documentation and plot titles
table_resolution_bits = 12            # Resolution (e.g., 12 bits = 4096 entries)
lut_type = "int16_t"                  # C type (int8_t, uint16_t, etc.)
 
samples_csv = "./data/temperature_samples.csv" # Path to CSV/Excel with 'raw' and 'calibration' columns. Path is global or relative to this file.

# Optionals
interpolation = "polynomial"  # Forces a given interpolation method for this LUT.
preview = true                # Enforce/stop preview generation for this LUT.

```

Currently available interpolation methods are:
| Interpolation Argument | Description |
| :--- | :--- |
| **linear** | Connects points with straight lines; assumes a constant slope between data points. |
| **splines** | Uses smooth, low-degree curves (like cubics) to join points without sharp transitions. |
| **polynomial** | Fits a single high-degree equation to the data; good for global trends but prone to oscillations. |
| **piecewise** | Functions as a **zero-order hold** (ZOH); it holds the value of a point constant until the next one is reached, resulting in a step-like sequence. |
| **idw** | Inverse Distance Weighting; calculates unknown values based on the weighted average of nearby known points. |
