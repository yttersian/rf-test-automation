from library.drivers import Instrument


class SMW200A(Instrument):
    def set_output(
        self, state: bool | str | None = None, attenuation: int = None
    ) -> None:
        """
        state:
            * Enables/disables the the output port.
            * `"ON"` | `True` <=> `"OFF"` | `False`

        attenuation:
            * Set the output attenuation level in dB.
        """
        if state is not None:
            match str(state).casefold():
                case "on" | "true":
                    self.instrument.write("OUTP ON;*WAI")
                case "off" | "false":
                    self.instrument.write("OUTP OFF;*WAI")

        if attenuation is not None:
            self.instrument.write("OUTP:AMOD MAN;*WAI")
            self.instrument.write(f"POW:ATT {attenuation};*WAI")

    def set_rf(
        self,
        frequency: int | float | None = None,
        dut_input_level: int | float | None = None,
        compensation_offset: int | float | None = None,
        source_power: int | float | None = None,
    ) -> None:
        """
        frequency:
            * Set the output frequency in Hz.

        dut_input_level:
            * Set the output level, after output compensation has been applied.

        compensation_offset:
            * Output power offset in dB. If set, SG will compensate the power level by increasing the output power by this offset.

        source_power:
            * Sets the output power to this level, ignoring any offset compensation.
        """
        if frequency is not None:
            self.instrument.write(f"FREQ:CW {frequency};*WAI")
        if compensation_offset is not None:
            self.instrument.write(f"POW:OFFS {compensation_offset};*WAI")
        if dut_input_level is not None:
            self.instrument.write(f"POW {dut_input_level};*WAI")
        if source_power is not None:
            self.instrument.write(f"POW:POW {source_power};*WAI")

    def set_arb(
        self, waveform_pathname: str | None = None, state: bool | str | None = None
    ):
        """Arbitrary waveform.

        waveform_pathname:
            * Selects an existing waveform file, i.e. file with extension *.wv.

        state:
            * Enables the ARB generator. A waveform must be selected before the ARB generator is activated.
            * `"ON"` | `True` <=> `"OFF"` | `False`
        """
        if waveform_pathname is not None:
            self.instrument.write(f"BB:ARB:WAV:SEL {waveform_pathname};*WAI")

        if state is not None:
            match str(state).casefold():
                case "on" | "true":
                    self.instrument.write("BB:ARB:STAT ON;*WAI")
                case "off" | "false":
                    self.instrument.write("BB:ARB:STAT OFF;*WAI")

    def set_baseband(
        self,
        digital_modulation: bool | str | None = None,
        optimization_mode: str | None = None,
    ) -> None:
        """Baseband configuration.

        digital_modulation:
            * Enables/disables digital modulation.
            * `"ON"` | `True` <=> `"OFF"` | `False`

        optimization_mode:
            * Fast
            * High Quality Table
            * High Quality
        """

        if digital_modulation is not None:
            match str(digital_modulation).casefold():
                case "on" | "true":
                    self.instrument.write("BB:DM:STAT ON; *WAI")
                case "off" | "false":
                    self.instrument.write("BB:DM:STAT OFF; *WAI")

        if optimization_mode is not None:
            match optimization_mode.casefold():
                case "fast":
                    command = "FAST"
                case "high quality table" | "qht":
                    command = "QHT"
                case "high quality" | "qhig":
                    command = "QHIG"
            self.instrument.write(f"BB:IMP:OPT:MODE {command};*WAI")
