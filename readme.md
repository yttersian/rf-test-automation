# RF Test Automation

Python-based framework for automating DUT (Device Under Test) test and characterization. The current implementation focused on RF devices and contains:

* SCPI drivers for select RF instruments
* A calibration script for generating path loss files
* A PA characterization script for measuring metrics such as:
  * P1dB
  * 2nd/3rd Harmonics
  * PAE
  * ACLR/DPD evaluation

This framework can be adapted for a variety of DUTs and test scenarios.

## Setup

**Prerequisite!** Requires Python >=3.10.

Create and activate a virtual environment, and install the packages:
```
python -m venv .venv

source .venv/bin/activate    # MacOS/Linux
.venv\Scripts\activate       # Windows

pip install -r requirements.txt
```


## Usage
1. Calibrate the path loss if needed (see [Calibration](#calibration) for details).

2. Modify the test plan in the `config/config.toml` file to match your device and test requirements.

3. Run the test script, e.g:
    ```
    python pa_characterization.py
    ```

    Results will be logged to the console and saved to output files in the `output/` directory.

### Calibration

The calibration process adjusts for path loss and ensures accurate measurements.

1. Run `calibrate.py`

2. When prompted, enter the product names (separated by spaces) that you wish to calibrate for (ex: 'Product-A Product-B'), or follow the steps to manually select calibration frequencies.

3. Enter the transmission power level to calibrate at. Note that higher power levels may speed up the calibration process, depending on your sensor equiment.

4. Follow the on-screen instructions to complete the calibration.

The calibration data will be stored as a CSV file in the `config/` directory for use during testing.