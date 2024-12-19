# Standard library imports
import pathlib
import time
import zipfile

# Third party imports
import pandas as pd
import pyvisa
import numpy as np

# Local imports
from config import config as cfg, config_path, rig, path_loss, path_loss_path
from library.drivers.vsa import FSW43
from library.drivers.vsg import SMW200A
from library.drivers.power_supplies import E36313A
from library.drivers.sensors import NRPZ86


def main() -> None:

    if (test_lasig := cfg["test_lasig"]) == "":
        match input("Test large signals (Y/n)? ").casefold():
            case "y" | "yes":
                test_lasig = True
            case _:
                test_lasig = False
    if (test_aclr := cfg["test_aclr"]) == "":
        match input("Test ACLR (Y/n)? ").casefold():
            case "y" | "yes":
                test_aclr = True
            case _:
                test_aclr = False
    if (with_dpd := cfg["with_dpd"]) == "":
        match input("ACLR with DPD (Y/n)? ").casefold():
            case "y" | "yes":
                with_dpd = True
            case _:
                with_dpd = False

    vcc = cfg["PowerSupply"]["ps1_ch1_voltage"]
    icc = cfg["PowerSupply"]["ps1_ch1_current"]
    vbias = cfg["PowerSupply"]["ps2_ch1_voltage"]
    ibias = cfg["PowerSupply"]["ps2_ch1_current"]
    vpaen = cfg["PowerSupply"]["ps2_ch2_voltage"]
    ipaen = cfg["PowerSupply"]["ps2_ch2_current"]

    for ch in [1, 2, 3]:
        ps1.set_channel(ch, voltage=vcc, current=icc)
    ps2.set_channel(1, voltage=vbias, current=ibias)
    ps2.set_channel(2, voltage=vpaen, current=ipaen)

    ps1.turn_on(1, 2, 3)
    ps2.turn_on(1, 2)

    dir_log = pathlib.Path(__file__).parent / "log" / product / serial
    dir_log.mkdir(parents=True, exist_ok=True)

    if test_lasig:
        lasig_log = dir_log / f"LASIG_{product}_SER{serial}_DATE{date}.csv"
        sweep_log = dir_log / f"SWEEP_{product}_SER{serial}_DATE{date}.csv"
        lasig_data, sweep_data = run_lasig()
        lasig_data.to_csv(lasig_log)
        sweep_data.to_csv(sweep_log)
        print(lasig_data)

    if test_aclr:
        aclr_log = dir_log / f"ACLR_{product}_SER{serial}_DATE{date}.csv"
        aclr_data = run_aclr(with_dpd=with_dpd)
        aclr_data.to_csv(aclr_log)
        print(aclr_data)

    data = dir_log / f"{product}_SER{serial}_DATE{date}.zip"
    with zipfile.ZipFile(data, mode="w") as archive:
        archive.write(config_path, arcname=config_path.name)
        archive.write(path_loss_path, arcname=path_loss_path.name)
        if test_lasig:
            archive.write(lasig_log, arcname=lasig_log.name)
            archive.write(sweep_log, arcname=sweep_log.name)
        if test_aclr:
            archive.write(aclr_log, arcname=aclr_log.name)


def run_lasig() -> tuple[pd.DataFrame, pd.DataFrame]:

    vsa.reset(wait=True, clear_status=True)
    vsg.reset(wait=True, clear_status=True)
    sensor.reset()

    frange = cfg[product]["Freqs"]["lasig"]

    match (pout_targets := cfg["pout_target_dbm"]):
        case int():
            pout_targets = [pout_targets]
        case list():
            pass

    sweep = {}
    tmp = []
    for freq in frange:
        input_path_loss = path_loss.at[freq, "sg_to_dut_p1_loss_db"]
        sa_path_loss = path_loss.at[freq, "sa_to_dut_p2_loss_db"]
        sensor_path_loss = path_loss.at[freq, "sensor_to_dut_p2_loss_db"]
        vsa.set_reference_level(offset=(-sa_path_loss))

        vsa.set_frequency(center=freq, span=0)
        vsg.set_rf(frequency=freq, compensation_offset=input_path_loss)
        sensor.set_frequency(freq)

        sweep[freq] = run_power_sweep(
            start=cfg[product]["sweep_start_dbm"],
            stop=cfg[product]["sweep_stop_dbm"],
            step=cfg[product]["sweep_step_dbm"],
            sensor_path_loss=sensor_path_loss,
            average_count=1,
            timeout=0.2,
        )

        gain_compression = find_gain_compression(
            sweep_data=sweep[freq], dbm_at_linear_gain=cfg[product]["sweep_start_dbm"]
        )
        tmp.append(
            pd.DataFrame(
                {
                    "frequency_hz": [freq for _ in gain_compression],
                    "condition": gain_compression.keys(),
                    "pout_dbm": gain_compression.values(),
                }
            )
        )
        for pout_target in pout_targets:
            dut_pin, dut_pout = find_pout(
                target_dbm=pout_target,
                sensor_path_loss=sensor_path_loss,
                pin_low=cfg[product]["sweep_start_dbm"],
                pin_high=cfg[product]["sweep_stop_dbm"],
                average_count=3,
                timeout=0.25,
            )

            conditions = {"frequency_hz": freq, "condition": f"{pout_target}dbm"}
            gain = {"pout_dbm": dut_pout, "gain_db": dut_pout - dut_pin}
            harmonics = measure_harmonic(multiple=[2, 3], fundamental_frequency=freq)
            pae = {
                "pae": measure_pae(sensor_path_loss=sensor_path_loss, pin=dut_pin) * 100
            }
            tmp.append(pd.DataFrame([conditions | gain | harmonics | pae]))
        vsg.set_output("off")
    lasig_data = pd.concat(tmp).set_index(["frequency_hz", "condition"])
    sweep_data = pd.concat(sweep)

    return lasig_data, sweep_data


def run_aclr(with_dpd: bool = False):

    vsa.reset(wait=True, clear_status=True)
    vsg.reset(wait=True, clear_status=True)
    sensor.reset()

    frange = cfg[product]["Freqs"]["modulated"]
    signal_bandwidth = cfg[product]["signal_bw"]
    resolution_bandwidth = cfg["ACLR"]["resolution_bandwidth"]
    sweep_time = cfg["ACLR"]["sweep_time"]
    carrier_number = cfg[product]["carrier_number"]
    sa_ref_level = cfg[product]["sa_ref_level"]
    sa_inp_att_level = cfg[product]["sa_inp_att_level"]
    sg_att_level = cfg[product]["sg_att_level"]

    match (pout_targets := cfg["pout_target_dbm"]):
        case int():
            pout_targets = [pout_targets]
        case list():
            pass
        case _:
            raise Exception

    if with_dpd:
        dpd_gain_exp = cfg[product]["dpd_expansion"]
        dpd_iteration = cfg["DPD"]["iteration"]
        dpd_tradeoff = cfg["DPD"]["tradeoff"]
        estim_range = cfg["DPD"]["estim_range"]
        iq_count = cfg["DPD"]["iq_count"]

    match cfg["test_rig"].casefold():
        case "a":
            usb_drive = "UDISK"
        case "b":
            usb_drive = "GG"

    match (carrier_number, signal_bandwidth):
        case (int(), 20e6):
            aclr_channel_bandwidth = 19080000
            aclr_adjacent_channels = carrier_number
            signal_pathname = (
                f"'/usb/{usb_drive}/5GNR_ETM31_{carrier_number}X20MHZ_85DB_CCDF001'"
            )
        case (1, 100e6):
            aclr_channel_bandwidth = 98280000
            aclr_adjacent_channels = 2
            signal_pathname = f"'/usb/{usb_drive}/5gnrfdd_BW_100_CF_8.5dB_mkr'"

    if sg_att_level > 0:
        vsg.set_output(attenuation=sg_att_level)
    vsg.set_baseband(digital_modulation="on", optimization_mode="high quality table")
    vsg.set_arb(waveform_pathname=signal_pathname, state="on")
    vsa.create_channel(kind="spectrum", name="ACLR")

    if with_dpd:
        vsa.create_channel(kind="amplifier", name="DPD")
        vsa.configure_window(replace="ACP")
        vsa.configure_aclr(
            transmission_channels=carrier_number,
            transmission_channel_spacing=signal_bandwidth,
            transmission_channel_bandwidth=aclr_channel_bandwidth,
            adjacent_channels=aclr_adjacent_channels,
            adjacent_channel_spacing=signal_bandwidth,
            adjacent_channel_bandwidth=aclr_channel_bandwidth,
            automatic_measurement_bandwidth="on",
        )
        vsa.set_resolution_bandwidth(rbw=resolution_bandwidth)
        vsa.configure_signal_generator(state="on", ip_address=vsg.ip_address)
        time.sleep(0.5)
        vsa.configure_ddpd(
            count=dpd_iteration,
            gain_expansion_db=dpd_gain_exp,
            tradeoff=dpd_tradeoff,
        )
        if cfg["DPD"]["estim_flag"]:
            vsa.set_synchronization(
                estimation_range=estim_range, evaluation_range=estim_range
            )
        if cfg["DPD"]["iq_flag"]:
            vsa.set_sweep_statistics(count=iq_count)
        if signal_bandwidth == 100e6:
            vsa.set_trigger(source="external")
            vsa.set_sample_rate(bandwitdh=6e8)
        vsa.configure_reference_signal(read_from_signal_generator=True)
        vsa.select_channel(name="ACLR")

    vsa.configure_aclr(
        preset="eutra",
        transmission_channels=carrier_number,
        transmission_channel_spacing=signal_bandwidth,
        transmission_channel_bandwidth=aclr_channel_bandwidth,
        adjacent_channels=aclr_adjacent_channels,
        adjacent_channel_spacing=signal_bandwidth,
        adjacent_channel_bandwidth=aclr_channel_bandwidth,
    )
    vsa.set_resolution_bandwidth(rbw=resolution_bandwidth)
    vsa.set_sweep(time=sweep_time)

    tmp = []
    for freq in frange:
        input_path_loss = path_loss.at[freq, "sg_to_dut_p1_loss_db"]
        sa_path_loss = path_loss.at[freq, "sa_to_dut_p2_loss_db"]
        sensor_path_loss = path_loss.at[freq, "sensor_to_dut_p2_loss_db"]
        vsa.set_reference_level(offset=(-sa_path_loss), value=sa_ref_level)

        vsa.set_frequency(center=freq)
        vsg.set_rf(frequency=freq, compensation_offset=input_path_loss)
        sensor.set_frequency(freq)

        vsa.set_input_attenuation(level="auto")
        for pout_target in pout_targets:
            dut_pin, dut_pout = find_pout(
                target_dbm=pout_target,
                sensor_path_loss=sensor_path_loss,
                pin_low=cfg[product]["sweep_start_dbm"],
                pin_high=cfg[product]["sweep_stop_dbm"],
                average_count=3,
                timeout=0.25,
            )
            vsa.set_input_attenuation(level=sa_inp_att_level)
            aclr_data = vsa.get_aclr_channel_power()
            metadata = {
                "frequency_hz": freq,
                "pout_target": pout_target,
            }

            if with_dpd:
                vsa.select_channel(name="DPD")
                vsa.set_frequency(center=freq)
                vsa.set_reference_level(offset=(-sa_path_loss), value=sa_ref_level)
                # vsa.set_input_attenuation(level=sa_inp_att_level)
                vsa.start_ddpd()
                while vsa.get_ddpd_iteration() < dpd_iteration:
                    time.sleep(1)
                time.sleep(20)

                metadata["pout_max_dbm"] = vsa.get_power_maximum()
                metadata["evm_pct"] = vsa.get_raw_evm_current()
                vsa.select_channel(name="ACLR")
                aclr_with_dpd = vsa.get_aclr_channel_power()
                for key in aclr_with_dpd:
                    aclr_data[key + "_dpd"] = aclr_with_dpd[key]

                vsa.select_channel(name="DPD")
                vsa.apply_ddpd(state="off")
                vsa.select_channel(name="ACLR")
            tmp.append(pd.DataFrame([aclr_data | metadata]))

    return pd.concat(tmp).set_index(["frequency_hz", "pout_target"])


def run_power_sweep(
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
            np.median([sensor.get_power() for _ in range(average_count)])
            - sensor_path_loss
        )
        dut_gain[pwr] = dut_pout[pwr] - pwr
    sweep_data = pd.DataFrame({"dut_pout_dbm": dut_pout, "dut_gain_db": dut_gain})
    sweep_data.index.name = "dut_pin_dbm"
    vsg.set_output("OFF")

    return sweep_data


def find_gain_compression(sweep_data: pd.DataFrame, dbm_at_linear_gain: float) -> dict:

    linear_gain = sweep_data.at[dbm_at_linear_gain, "dut_gain_db"]
    try:
        op1db = sweep_data[
            sweep_data.dut_gain_db < linear_gain - 1
        ].dut_pout_dbm.values[0]
    except:
        return {"op1db": None, "op3db": None, "op5db": None}
    try:
        op3db = sweep_data[
            sweep_data.dut_gain_db < linear_gain - 3
        ].dut_pout_dbm.values[0]
    except:
        return {"op1db": op1db, "op3db": None, "op5db": None}
    try:
        op5db = sweep_data[
            sweep_data.dut_gain_db < linear_gain - 5
        ].dut_pout_dbm.values[0]
    except:
        return {"op1db": op1db, "op3db": op3db, "op5db": None}

    return {"op1db": op1db, "op3db": op3db, "op5db": op5db}


def find_pout(
    target_dbm: float,
    sensor_path_loss: float,
    pin_low: float,
    pin_high: float,
    pout_margin: float = 0.05,
    average_count: int = 10,
    timeout: float = 0.5,
    iteration: int = 1,
) -> tuple[float, float]:

    dut_pin = (pin_low + pin_high) / 2
    vsg.set_rf(dut_input_level=dut_pin)
    vsg.set_output("ON")
    time.sleep(timeout)
    pout_now = (
        np.median([sensor.get_power() for _ in range(average_count)]) - sensor_path_loss
    )

    if abs(pout_now - target_dbm) <= pout_margin:
        return dut_pin, pout_now
    elif iteration > 20:
        raise Exception("Unable to find Pout target.")
    elif pout_now > target_dbm:
        return find_pout(
            target_dbm=target_dbm,
            sensor_path_loss=sensor_path_loss,
            pin_low=pin_low,
            pin_high=dut_pin,
            pout_margin=pout_margin,
            average_count=average_count,
            timeout=timeout,
            iteration=iteration + 1,
        )
    else:
        return find_pout(
            target_dbm=target_dbm,
            sensor_path_loss=sensor_path_loss,
            pin_low=dut_pin,
            pin_high=pin_high,
            pout_margin=pout_margin,
            average_count=average_count,
            timeout=timeout,
            iteration=iteration + 1,
        )


def measure_harmonic(
    multiple: list[int],
    fundamental_frequency: float,
    average_count: int = 10,
    sampling_timeout: float = 0.1,
) -> dict[str, float]:

    vsa.set_frequency(center=fundamental_frequency, span=0)
    fundamental = []
    for _ in range(average_count):
        fundamental.append(vsa.measure_peak())
        time.sleep(sampling_timeout)
    fundamental = np.median(fundamental)

    harmonics = {}
    for k in multiple:
        vsa.set_frequency(center=fundamental_frequency * k)
        # vsa.set_reference_level(auto=True)
        tmp = []
        for _ in range(average_count):
            tmp.append(vsa.measure_peak())
            time.sleep(sampling_timeout)
        harmonics[f"harmonic_{k}_dbc"] = np.median(tmp) - fundamental
    return harmonics


def measure_pae(sensor_path_loss: float, pin: float, average_count: int = 10) -> float:

    pout = (
        np.median([sensor.get_power() for _ in range(average_count)]) - sensor_path_loss
    )
    voltage = ps1.get_voltage(1)
    current_ps1 = [ps1.get_current(channel) for channel in [1, 2, 3]]
    current_ps2 = [ps2.get_current(channel) for channel in [1, 2]]
    current = sum(current_ps1 + current_ps2)

    return ps1.power_added_efficiency(pout, pin, voltage, current, power_unit="dbm")


if __name__ == "__main__":

    if (product := cfg["product"]) == "":
        product = input("Enter product: ")
    if (serial := cfg["serial"]) == "":
        serial = input("Enter serial number: ")
    date = time.strftime("%y%m%d-%Hh%Mm")

    # Open instruments
    rm = pyvisa.ResourceManager()
    vsa = FSW43(rm, ip_address=rig["SA"]["FSW43"]["ip"], reset=False)
    vsg = SMW200A(rm, ip_address=rig["SG"]["SMW200A"]["ip"], reset=False)
    ps1 = E36313A(rm, ip_address=rig["PowerSupply"]["E36313A_1"]["ip"])
    ps2 = E36313A(rm, ip_address=rig["PowerSupply"]["E36313A_2"]["ip"])
    sensor = NRPZ86(
        rm,
        device_id=rig["PowerSensor"]["NRP_Z86"]["device_id"],
        serial=rig["PowerSensor"]["NRP_Z86"]["serial_nu"],
        reset=False,
    )

    try:
        main()
    finally:
        vsg.set_output("OFF")
        ps2.turn_off(1, 2, 3)
        ps1.turn_off(1, 2, 3)
