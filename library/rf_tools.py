"""Placeholder for shared common functions / test cases. These could be run_power_sweep(), find_pout() and so on that high level scripts like "main.py" or "pa_characterization.py" can use.
    
    Import the module in the high level scripts with:
    
    import library.rf_tools as rf
    
    Then they can simply be called in the high level script, e.g. rf.run_power_sweep(vsg, sensor, start, ...)
    ! Remember that instruments must be passed on to this module as arguments. See an example of this below:
    
def run_power_sweep(
    vsg,
    sensor,
    start: float,
    stop: float,
    step: float,
    sensor_path_loss: float,
    average_count: int = 10,
    timeout: float = 0.5,
) -> pd.DataFrame:

    dut_pout = {}
    dut_gain = {}
    vsg.set_rf(dut_input_level=start)
    vsg.set_output("ON")
    time.sleep(2 - timeout)
    for pwr in np.arange(start, stop + step, step):
        vsg.set_rf(dut_input_level=pwr)
        time.sleep(timeout)
        dut_pout[pwr] = (
            np.median([sensor.get_power()() for _ in range(average_count)])
            - sensor_path_loss
        )
        dut_gain[pwr] = dut_pout[pwr] - pwr
    sweep_data = pd.DataFrame({"dut_pout_dbm": dut_pout, "dut_gain_db": dut_gain})
    sweep_data.index.name = "dut_pin_dbm"
    vsg.set_output("OFF")

    return sweep_data
    
    
"""
