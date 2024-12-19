from library.drivers import Instrument


class E36313A(Instrument):
    def set_channel(self, channel: int, voltage: float, current: float) -> None:
        """Sets the voltage and current of the selected channel."""
        self.instrument.write(f"APPL CH{channel}, {voltage}, {current}")

    def turn_on(self, *channels: int) -> None:
        """Turns on the selected channel(s)."""
        self.instrument.write(f"OUTP ON,(@{','.join([str(i) for i in channels])})")

    def turn_off(self, *channels: int) -> None:
        """Turns off the selected channel(s)."""
        self.instrument.write(f"OUTP OFF,(@{','.join([str(i) for i in channels])})")

    def get_voltage(self, channel: int) -> float:
        """Returns the measured voltage from the given channel."""
        return float(self.instrument.query(f"MEAS:VOLT? CH{channel}"))

    def get_current(self, channel: int) -> float:
        """Returns the measured current from the given channel."""
        return float(self.instrument.query(f"MEAS:CURR? CH{channel}"))
