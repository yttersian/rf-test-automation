import re
import pathlib
import time

import pandas as pd
import pyvisa
import numpy as np

from config import config as cfg, rig
from library.drivers.vsa import FSW43
from library.drivers.vsg import SMW200A
from library.drivers.sensors import NRPZ86


def main(
    frange: str | None = None,
    power_dbm: float | None = None,
    average_count: int = 10,
    write_to_csv: bool = True,
):
    """Call this function with the following optional arguments:
    Args:
        * frange: Supply the product name directly to skip the prompt.
        * power_dbm: Supply the transmission power directly to skip the prompt.
        * average_count: The measurement sample count, which is then averaged. Defaults to 10.
        * write_to_csv: Whether to save the result to a csv file.
    """
    if frange is None:
        frange = generate_frange()
    else:
        frange = generate_frange(prompt=frange)

    if power_dbm is None:
        power_dbm = input("Enter transmission power (default: 0 dBm): ")
    match power_dbm:
        case "":
            power_dbm = 0
        case _:
            power_dbm = float(power_dbm)

    print("Calibration frequencies: ", end="")
    for i, freq in enumerate(frange):
        if i == len(frange) - 1:
            break
        elif i > 1 and i is not len(frange) - 2:
            print(f"{frange[i] / 1e9:.2f}", end=" ... ")
            break
        else:
            print(f"{freq / 1e9:.2f}", end=", ")
    print(f"{frange[-1] / 1e9:.2f} GHz")
    print(f"Transmission power: {power_dbm} dBm\n")

    # adapter_loss = adapter_insertion_loss(file="", freqs=frange, write_to_csv=True)
    try:
        adapter_loss = pd.read_csv(
            pathlib.Path(__file__).parent / "config" / "adapter_deembedded.csv",
            index_col="frequency_hz",
        ).squeeze()
    except:
        adapter_loss = None

    input("\nPress any key to start input loss calibration ")
    input_path_loss = calibrate_input_path_loss(
        frange=frange, power_dbm=power_dbm, average_count=average_count
    )
    print(input_path_loss)
    input(
        "Input loss calibrated. Press any key to continue SA/Sensor loss calibration "
    )
    sa_path_loss, sensor_path_loss = calibrate_sa_sensor_path_loss(
        frange=frange,
        power_dbm=power_dbm,
        input_path_loss=input_path_loss,
        adapter_loss=adapter_loss,
        average_count=average_count,
    )

    path_loss = pd.DataFrame(
        {
            "sg_to_dut_p1_loss_db": input_path_loss,
            "sa_to_dut_p2_loss_db": sa_path_loss,
            "sensor_to_dut_p2_loss_db": sensor_path_loss,
            "frequency": frange,
            "power": [power_dbm for _ in frange],
        }
    ).set_index(["power", "frequency"])
    print(path_loss)
    if write_to_csv:
        dir_config = pathlib.Path(__file__).parent / "config"
        path_loss.to_csv(dir_config / f"pathloss_{date}.csv")


def calibrate_input_path_loss(
    frange: list,
    power_dbm: int | float,
    average_count: int = 10,
    sampling_timeout: float = 1,
) -> pd.Series:
    """
    Args:
        frange (list): Frequencies to perform the measurement on.
        power_dbm (int | float): The signal output power.

    Returns:
        pd.Series: Pandas Series of measured power at the end of the signal cable (input path loss).
    """
    input_path_loss = {}
    for freq in frange:
        sensor.set_frequency(freq)
        vsg.set_rf(frequency=freq, source_power=power_dbm)
        vsg.set_output("ON")
        time.sleep(sampling_timeout)
        input_path_loss[freq] = (
            np.median([sensor.get_power() for _ in range(average_count)]) - power_dbm
        )
    input_path_loss = pd.Series(input_path_loss, name="sg_to_dut_p1_loss_db")
    input_path_loss.index.name = "frequency_hz"
    vsg.set_output("OFF")

    return input_path_loss


def calibrate_sa_path_loss(
    frange: list,
    power_dbm: int | float,
    input_path_loss=None,
    adapter_loss=None,
    average_count: int = 10,
    sampling_timeout: float = 1,
):
    sa_path_loss = {}
    vsa.set_frequency(span=0)
    for freq in frange:
        vsa.set_frequency(center=freq)
        compensation = 0
        if input_path_loss is not None:
            compensation = input_path_loss[freq]
        if adapter_loss is not None:
            compensation = compensation + adapter_loss[freq]
        vsg.set_rf(
            frequency=freq, dut_input_level=power_dbm, compensation_offset=compensation
        )
        vsg.set_output("ON")
        time.sleep(sampling_timeout)
        sa_path_loss[freq] = (
            np.median([vsa.measure_peak() for _ in range(average_count)]) - power_dbm
        )

    sa_path_loss = pd.Series(sa_path_loss, name="sa_to_dut_p2_loss_db")
    sa_path_loss.index.name = "frequency_hz"
    vsg.set_output("OFF")

    return sa_path_loss


def calibrate_sensor_path_loss(
    frange: list,
    power_dbm: int | float,
    input_path_loss=None,
    adapter_loss=None,
    average_count: int = 10,
    sampling_timeout: float = 1,
):
    sensor_path_loss = {}
    for freq in frange:
        sensor.set_frequency(freq)
        compensation = 0
        if input_path_loss is not None:
            compensation = input_path_loss[freq]
        if adapter_loss is not None:
            compensation = compensation + adapter_loss[freq]
        vsg.set_rf(
            frequency=freq, dut_input_level=power_dbm, compensation_offset=compensation
        )
        vsg.set_output("ON")
        time.sleep(sampling_timeout)
        sensor_path_loss[freq] = (
            np.median([sensor.get_power() for _ in range(average_count)]) - power_dbm
        )
    sensor_path_loss = pd.Series(sensor_path_loss, name="sensor_to_dut_p2_loss_db")
    sensor_path_loss.index.name = "frequency_hz"
    vsg.set_output("OFF")

    return sensor_path_loss


def calibrate_sa_sensor_path_loss(
    frange: list,
    power_dbm: int | float,
    input_path_loss=None,
    adapter_loss=None,
    average_count: int = 10,
    sampling_timeout: float = 1,
):
    sa_path_loss = {}
    sensor_path_loss = {}
    vsa.set_frequency(span=0)
    vsg.reset()
    for freq in frange:
        vsa.set_frequency(center=freq)
        sensor.set_frequency(freq)
        compensation = 0
        if input_path_loss is not None:
            compensation = input_path_loss[freq]
        if adapter_loss is not None:
            compensation = compensation + adapter_loss[freq]
        vsg.set_rf(
            frequency=freq, dut_input_level=power_dbm, compensation_offset=compensation
        )
        vsg.set_output("ON")
        time.sleep(sampling_timeout)
        sa_path_loss[freq] = (
            np.median([vsa.measure_peak() for _ in range(average_count)]) - power_dbm
        )
        sensor_path_loss[freq] = (
            np.median([sensor.get_power() for _ in range(average_count)]) - power_dbm
        )
    sa_path_loss = pd.Series(sa_path_loss, name="sa_to_dut_p2_loss_db")
    sa_path_loss.index.name = "frequency_hz"
    sensor_path_loss = pd.Series(sensor_path_loss, name="sensor_to_dut_p2_loss_db")
    sensor_path_loss.index.name = "frequency_hz"
    vsg.set_output("OFF")

    return sa_path_loss, sensor_path_loss


def generate_frange(prompt=None) -> list:
    """Generates a list of the frequenies we test on the selected products.
    Will prompt the user for product name(s), for example:
        * "Product-A"
        * "Product-A Product-B"
    User can also input a custom list of calibration frequencies by manual input or by providing start, stop and step.
    """
    if prompt is None:
        prompt = input(
            """Enter one of the following:
            
* products to calibrate for
* 'custom' for manual input
* 'step' for start/stop/step\n
Input: """
        )
    match prompt:
        case "custom":
            frange = input("Enter frequency range (ex: '3e9 3.3e9 3.6e9'): ")
            frange = [float(freq) for freq in list(frange.split())]

        case "step":
            freqs = input("Enter 'start stop step' (ex. '3.3e9 3.8e9 100e6'): ").split()
            start = float(freqs[0])
            stop = float(freqs[1])
            step = float(freqs[2])
            frange = np.arange(start, stop + step, step)
        case _:
            products = []
            for product in prompt.split():
                for key in cfg.keys():
                    if re.match(product.casefold(), key.casefold()):
                        products.append(key)
            frange = []
            for product in products:
                for freqs in list(cfg[product]["Freqs"].values()):
                    for freq in freqs:
                        frange.append(freq)

    return sorted([*set(frange)])


def adapter_insertion_loss(
    file: str, freqs: list | None = None, write_to_csv=False
) -> pd.Series:
    import skrf as rf

    adapter_calfile = pathlib.Path(__file__).parent / "config" / file
    df = rf.Network(adapter_calfile).to_dataframe()
    df.index.name = "frequency_hz"
    adapter_insertion_loss = df["s_db 21"]
    adapter_insertion_loss.name = "adapter_s21_db"
    if freqs is not None:
        adapter_insertion_loss = adapter_insertion_loss["s_db 21"].filter(items=freqs)
    if write_to_csv:
        adapter_insertion_loss.to_csv(
            adapter_calfile.parent / f"{file.removesuffix('.s2p')}.csv"
        )
    return adapter_insertion_loss


if __name__ == "__main__":

    date = time.strftime("%y%m%d-%Hh%Mm")

    rm = pyvisa.ResourceManager()
    vsa = FSW43(rm, ip_address=rig["SA"]["FSW43"]["ip"])
    vsg = SMW200A(rm, ip_address=rig["SG"]["SMW200A"]["ip"])
    sensor = NRPZ86(
        rm,
        device_id=rig["PowerSensor"]["NRP_Z86"]["device_id"],
        serial=rig["PowerSensor"]["NRP_Z86"]["serial_nu"],
    )
    try:
        main()
    finally:
        vsg.set_output("OFF")
