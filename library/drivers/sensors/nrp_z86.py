import time

from library.drivers import Instrument


class NRPZ86(Instrument):
    def __init__(
        self, rm, device_id: str, serial: str, timeout: int = 5000, reset=True
    ):
        self.instrument = rm.open_resource(f"RSNRP::{device_id}::{serial}::INSTR")
        self.device_id = device_id
        self.serial = serial
        if reset:
            self.reset()
        self.instrument.timeout = timeout

    def reset(self) -> None:
        """Resets the instrument to its default state and parameters."""
        self.instrument.write("*RST")

    def set_frequency(self, center: int | float | str):
        """Set the measurment frequency in Hz."""
        self.instrument.write(f"SENS:FREQ {center}")

    def get_power(
        self,
        time_interval: str | None = None,
        average_count: float | None = 65536,
        unit: str = "dbm",
    ) -> float:
        """Performs a single measurement and returns the measured powered in dBm or Watts.

        Parameters:
        * time_interval (1.0e-6 to 1.0): If specified, defines the length of the time interval used to measure the average
        signal power in the Continuous Average mode (sampling window). Default setting: 10.0e-6 [s].
        * average_count (1 to 2^20): If specified, sets the number of measured values that have to be averaged to form the
        measurement result in the modes Continuous Average, Burst Average, or Timeslot Average. Default setting: 1024.
        * unit: Specifies whether to return the power in [W] or [dBm]. Defaults to [dBm].

        Returns:
            float: Power [W] or [dBm].
        """
        if time_interval is not None:
            self.instrument.write(f"SENS:POW:AVG:APER {time_interval}")
        if average_count is not None:
            self.instrument.write(f"SENS:AVER:COUN {average_count}")

        self.instrument.write("INIT:IMM")
        time.sleep(0.1)
        power_in_watt = float(self.instrument.query("FETCH?").split(",")[0])
        time.sleep(0.1)
        match unit.casefold():
            case "dbm":
                return self.watt_to_dbm(power_in_watt) if power_in_watt > 0 else 0
            case "watt" | "w":
                return power_in_watt if power_in_watt > 0 else 0

    def set_mode(self, mode: str | None = None) -> None:
        """Configures the sensor measurement:

        frequency: RF carrier frequency to be measured to the sensor

        offset:set a fixed offset in dB to correct the measured value

        mode:
        * Continuous Average
        * Burst Average
        * Timeslot Average
        * Trace
        * Statistics (PDF)
        * Statistics (CCDF)
        """

        if mode is not None:
            match mode:
                case "Continuous Average":
                    command = "POW:AVG"
                case "Burst Average":
                    command = "POW:BURS:AVG"
                case "Timeslot Average":
                    command = "POW:TSL:AVG"
                case "Trace":
                    command = "XTIM:POW"
                case "Statistics (PDF)":
                    command = "XPOW:PDF"
                case "Statistics (CCDF)":
                    command = "XPOW:CCFG"
            self.instrument.write(f'SENS:FUNC "{command}"')
