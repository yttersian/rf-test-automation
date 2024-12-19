import math

from pyvisa import ResourceManager


class Instrument:
    def __init__(
        self,
        rm: ResourceManager,
        ip_address: str,
        timeout: int = 5000,
        reset: bool = True,
    ):
        self.instrument = rm.open_resource(f"TCPIP::{ip_address}::inst0::INSTR")
        self.ip_address = ip_address
        self.instrument.timeout = timeout

        if reset:
            self.reset(clear_status=True)

    def reset(self, wait: bool = True, clear_status: bool = False) -> None:
        """Resets the instrument to its default state."""
        if wait:
            self.instrument.query("*RST;*OPC?")
        else:
            self.instrument.write("*RST")
        if clear_status:
            self.instrument.write("*CLS")

    @staticmethod
    def watt_to_dbm(watt):
        return 10 * math.log10(watt * 1000)

    @staticmethod
    def dbm_to_watt(dbm):
        return 1e-3 * (10 ** (dbm / 10))

    @staticmethod
    def power_added_efficiency(pout, pin, supply_volts, supply_amps, power_unit: str):
        """Calculates power added efficiency (PAE)

        Args:
            pout (float): Power Out in [W] or [dBm]
            pin (float): Power In in [W] or [dBm]
            supply_volts (float): Supply Voltage in [V]
            supply_amps (float): Supply current in [A]
            power_unit (str): Denotes provided power in/out unit, "dBm" or "Watt"

        Returns:
            float: PAE (range 0 to 1.0)
        """
        match power_unit.casefold():
            case "dbm":
                power_out = Instrument.dbm_to_watt(pout)
                power_in = Instrument.dbm_to_watt(pin)
            case "watt" | "watts" | "w":
                power_out = pout
                power_in = pin
        return (power_out - power_in) / (supply_volts * supply_amps)
