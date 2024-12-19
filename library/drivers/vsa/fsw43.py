from library.drivers import Instrument


class FSW43(Instrument):
    def select_channel(self, name: str) -> None:
        """Selects and opens the channel passed in `name`."""
        self.instrument.write(f"INST {name!r}")

    def create_channel(self, kind: str, name: str | None = None) -> None:
        """Creates a new channel.

        kind:
            * `"spectrum"` | `"sanalyzer"`
            * `"amplifier"` | `"ampl"`

        name (optional):
            * Pass a name to give the channel.
        """
        match kind:
            case "spectrum" | "sanalyzer":
                kind = "SANALYZER"
            case "amplifier" | "ampl":
                kind = "AMPL"
        if name is not None:
            self.instrument.write(f"INST:CRE {kind},{name!r}")
        else:
            self.instrument.write(f"INST {kind}")

    def measure_peak(self) -> float:
        """Records the the maximum level in the currently selected frame."""
        self.instrument.write("CALC:MARK:MAX")
        return float(self.instrument.query("CALC:MARK:Y?"))

    def set_reference_level(
        self,
        auto: bool = False,
        value: int | float | None = None,
        offset: float | str | None = None,
    ) -> None:
        """Sets the reference level.

        auto:
            * If true, the instrument adjusts the reference level automatically.
        value:
            * Set the reference level manually.

        offset:
            * Set the referenc level offset.
        """
        if auto:
            self.instrument.write("ADJ:LEV")

        if offset is not None:
            self.instrument.write(f"DISP:TRAC:Y:RLEV:OFFS {offset}")

        if value is not None:
            self.instrument.write(f"DISP:TRAC:Y:RLEV {value}")

    def set_input_attenuation(self, level: str | int) -> None:
        """Sets the input attenuation level.

        level:
        * Pass an `int` to manually define the input attenuation level.
        * Pass `"auto"` to turn on automatic selection of the input attenuation level.
        """
        match str(level).casefold():
            case "auto" | "automatic":
                self.instrument.write("INP:ATT:AUTO ON")
            case _:
                self.instrument.write("INP:ATT:AUTO OFF")
                self.instrument.write(f"INP:ATT {level}")

    def set_frequency(
        self,
        center: int | float | str | None = None,
        span: int | float | str | None = None,
    ):
        """Configures the frequency.

        Parameters
        ----------
            * center: Sets the center frequency.
            * span: Sets the frequency span.

        Examples of accepted args:
            * int: 100000000
            * float: 100e6
            * str: "100 MHz"
        """
        if center is not None:
            self.instrument.write(f"FREQ:CENT {center}")
        if span is not None:
            self.instrument.write(f"FREQ:SPAN {span}")

    def set_sweep(
        self,
        count: int | None = None,
        points: int | None = None,
        time: float | str | None = None,
        mode: str | None = None,
    ) -> None:
        """Configures sweep.

        Parameters
        ----------

        count:
            * Defines the number of sweeps that the application uses to average
        traces.
            * In case of continuous sweep mode, the application calculates the moving average over
        the average count.
            * In case of single sweep mode, the application stops the measurement and calculates
        the average after the average count has been reached.

        points:
            * Defines the number of sweep points to analyze after a sweep.

        time:
            * Defines the sweep time. It automatically decouples the time from any other settings.
            * Pass `"auto"` to couple the sweep time to the span, resolution and video bandwidths.

        mode:
            * Set the instrument to continuous or single sweep.
            * `"continuous"`
            * `"single"`


        """
        if count is not None:
            self.instrument.write(f"SWE:COUN {count}")

        if points is not None:
            self.instrument.write(f"SWE:POIN {points}")

        match time:
            case None:
                pass
            case float() | int():
                self.instrument.write(f"SWE:TIME {time}")
            case "auto" | "AUTO":
                self.instrument.write("SWE:TIME:AUTO ON")

        if mode is not None:
            match mode.casefold():
                case "continuous":
                    self.instrument.query("INIT:CONT ON;*OPC?")
                case "single":
                    self.instrument.query("INIT:CONT OFF;*OPC?")

    def set_trace(self, detector: str) -> None:
        """Defines the trace detector to be used for trace analysis.

        detector:
            * Auto Peak
            * Positive Peak
            * Negative Peak
            * RMS
            * Average
            * Sample (first value detected per trace point)
        """
        match detector.casefold():
            case "auto peak" | "ape":
                command = "APE"
            case "positive peak" | "pos":
                command = "POS"
            case "negative peak" | "neg":
                command = "NEG"
            case "rms":
                command = "RMS"
            case "average" | "aver" | "avg":
                command = "AVER"
            case "sample" | "samp":
                command = "SAMP"
        self.instrument.write(f"DET {command}")

    def set_trigger(self, source: str) -> None:
        """Select the trigger source.

        source:
            * `"immediate"`: Free Run.
            * `"external"`: Trigger signal from the "Trigger Input" connector.
        """
        match source.casefold():
            case "immediate" | "imm":
                command = "IMM"
            case "external" | "ext":
                command = "EXT"
        self.instrument.write(f"TRIG:SOUR {command}")

    def configure_aclr(
        self,
        preset: str | None = None,
        transmission_channels: int | None = None,
        transmission_channel_spacing: float | None = None,
        transmission_channel_bandwidth: float | None = None,
        adjacent_channels: int | None = None,
        adjacent_channel_spacing: float | None = None,
        adjacent_channel_bandwidth: float | None = None,
        automatic_measurement_bandwidth: bool | str | None = None,
    ):
        """Configures channel power and ACLR measurements.

        Arguments:
            * preset: Loads a measurement standard configuration.
                - `"EUTRA"`
            * transmission_channels: Number of transmission channels, from 1 to 18.
            * transmission_channel_spacing: Distance between transmission channels, 14 kHz to 2000 Mhz.
            * transmission_channel_bandwidth: Channel bandwidth of the transmission channels, 100 Hz to 1000 MHz.
            * adjacent_channels: Number of pairs of adjacent and alternate channels, 0 to 12.
            * adjacent_channel_spacing: Distance from transmission channel to adjacent channel, 100 Hz to 2000 MHz.
            * adjacent_channel_bandwidth: Channel bandwidth of the adjacent channels, 100 Hz to 1000 MHz.
        """
        if preset is not None:
            match preset.casefold():
                case "eutra" | "lte":
                    preset_standard = "EUTR"
            self.instrument.write(f"CALC:MARK:FUNC:POW:PRES {preset_standard}")

        if transmission_channels is not None:
            self.instrument.write(f"POW:ACH:TXCH:COUN {transmission_channels}")

        if transmission_channel_spacing is not None:
            self.instrument.write(f"POW:ACH:SPAC:CHAN {transmission_channel_spacing}")

        if transmission_channel_bandwidth is not None:
            self.instrument.write(f"POW:ACH:BAND {transmission_channel_bandwidth}")

        if adjacent_channels is not None:
            self.instrument.write(f"POW:ACH:ACP {adjacent_channels}")

        if adjacent_channel_spacing is not None:
            self.instrument.write(f"POW:ACH:SPAC:ACH {adjacent_channel_spacing}")

        if adjacent_channel_bandwidth is not None:
            self.instrument.write(f"POW:ACH:BAND:ACH {adjacent_channel_bandwidth}")

        if automatic_measurement_bandwidth is not None:
            match str(automatic_measurement_bandwidth).casefold():
                case "on" | "true":
                    self.instrument.write("POW:ACH:AABW ON")
                case "off" | "false":
                    self.instrument.write("POW:ACH:AABW OFF")

    def configure_window(self, replace: str, window_number: int = 1) -> None:
        """Configures the window.

        replace:
            * Replaces the window type.
            * `"adjacent channel power"` | `"acp"`

        window_number:
            * The window to configure. Defaults to Window 1.
        """
        match replace.casefold():
            case "adjacent channel power" | "acp":
                command = "ACP"
        self.instrument.write(f"LAY:REPL '{window_number}',{command}")

    # ------------------------
    # FSW K18 spesific methods

    def set_resolution_bandwidth(
        self,
        rbw: int | float | None = None,
        auto: bool | str | None = None,
    ) -> None:
        """Sets the resolution bandwidth applied to spectrum measurements.

        rbw:
            * Defines the resolution bandwidth.

        auto:
            * Turns automatic selection of the resolution bandwidth (RBW) for spectrum measurements on and off.
            * `"ON"` | `True` <=> `"OFF"` | `False`
        """
        if rbw is not None:
            self.instrument.write("BAND:AUTO OFF")
            self.instrument.write(f"BAND {rbw}")

        if auto is not None:
            match str(auto).casefold():
                case "on" | "true":
                    self.instrument.write("BAND:AUTO ON")
                case "off" | "false":
                    self.instrument.write("BAND:AUTO OFF")

    def set_sample_rate(
        self,
        bandwitdh: int | float | None = None,
        auto: bool | str | None = None,
    ) -> None:
        """Sets the sample rate with which the amplified signal is captured.
        Note that when you change the sample rate, the analysis bandwidth and capture length are adjusted automatically to the new sample rate.

        bandwidth:
            * Sample rate bandwidth in Hz.

        auto:
            * Turns automatic selection of an appropriate (capture) sample rate on and off.
            * `"ON"` | `True` <=> `"OFF"` | `False`
            * When you turn on this feature, the application calculates an appropriate sample rate based on the reference signal and adjusts the other data acquisition settings accordingly.
        """
        if bandwitdh is not None:
            self.instrument.write("TRAC:IQ:SRAT:AUTO OFF")
            self.instrument.write(f"TRAC:IQ:SRAT {bandwitdh}")

        if auto is not None:
            match str(auto).casefold():
                case "on" | "true":
                    self.instrument.write("TRAC:IQ:SRAT:AUTO ON")
                case "off" | "false":
                    self.instrument.write("TRAC:IQ:SRAT:AUTO OFF")

    def set_sweep_statistics(
        self,
        count: int | None = None,
        state: bool | str | None = None,
    ) -> None:
        """
        count:
            * Sets the sweep statistics count (IQ avg).

        state:
            * Enables / disables sweep statistics count.
            * `"ON"` | `True` <=> `"OFF"` | `False`
        """
        if count is not None:
            self.instrument.write("SWE:STAT ON")
            self.instrument.write(f"SWE:STAT:COUN {count}")
        if state is not None:
            match str(state).casefold():
                case "on" | "true":
                    self.instrument.write("SWE:STAT ON")
                case "off" | "false":
                    self.instrument.write("SWE:STAT OFF")

    def set_synchronization(
        self,
        estimation_range: list[float | str, float | str] | None = None,
        evaluation_range: list[float | str, float | str] | None = None,
    ) -> None:
        """Define a synchronization range.

        * `estimation_range`: Turns estimation over the complete reference signal on over the passed interval.
        * `evaluation_range`: Turns result evaluation over the complete capture buffer on over the passed interval.
        """
        if estimation_range is not None:
            self.instrument.write(":CONF:EST:FULL OFF")
            self.instrument.write(f"CONF:EST:STAR {estimation_range[0]}")
            self.instrument.write(f"CONF:EST:STOP {estimation_range[1]}")

        if evaluation_range is not None:
            self.instrument.write(":CONF:EVAL:FULL OFF")
            self.instrument.write(f"CONF:EVAL:STAR {evaluation_range[0]}")
            self.instrument.write(f"CONF:EVAL:STOP {evaluation_range[1]}")

    def configure_ddpd(
        self,
        state: bool = True,
        count: int | None = None,
        gain_expansion_db: int | float | None = None,
        tradeoff: int | None = None,
    ) -> None:
        """Configures direct DPD settings.

        Parameters:
            count: Defines the number of iterations in a direct DPD sequence. Range 1 to 1000.
            gain_expansion_db: Sets the gain expansion for Direct DPD in dB.
            state: Selects the type of DPD. "ON" = direct DPD, "OFF" = polynomial DPD.
            tradeoff: Defines the power / linearity tradeoff for direct DPD calculation as a percentage (0 to 100).
        """
        if state:
            self.instrument.write("CONF:DDPD ON")
        else:
            self.instrument.write("CONF:DDPD OFF")

        if count is not None:
            self.instrument.write(f"CONF:DDPD:COUN {count}")

        if gain_expansion_db is not None:
            self.instrument.write(f"CONF:DDPD:GEXP {gain_expansion_db}")

        if tradeoff is not None:
            self.instrument.write(f"CONF:DDPD:TRAD {tradeoff}")

    def start_ddpd(self) -> None:
        """Initiates a direct DPD sequence with the number of iterations defined."""
        self.instrument.write("CONF:DDPD:STAR")

    def get_ddpd_iteration(self) -> int:
        """Queries the process of the direct DPD sequence (number of current
        iteration).

        Returns:
            int: Current iteration
        """
        return int(self.instrument.query("CONF:DDPD:COUN:CURR?"))

    def get_ddpd_operation_status(self) -> bool:
        """Queries the state of a direct DPD operation."""
        return bool(self.instrument.query("FETC:DDPD:OPER:STAT?")[0])

    def apply_ddpd(self, state: bool | str) -> None:
        """Transfers the waveform file with the correction values to the signal generator and applies them to the input signal.

        state:
            * `"ON"` | `True` to enable the correction values.
            * `"OFF"` | `False` to disable the correction values.
        """
        match str(state).casefold():
            case "on" | "true":
                self.instrument.query("CONF:DDPD:APPL ON;*OPC?")
            case "off" | "false":
                self.instrument.query("CONF:DDPD:APPL OFF;*OPC?")

    def configure_signal_generator(
        self,
        ip_address: str | None = None,
        state: bool | str | None = None,
    ) -> None:
        """Configure control of the signal generator.

        Parameters:
            * ip_address: Pass the IP address of the connected signal generator.
            * state: Turns the generator control on and off.
                - `"ON"` | `True` <=> `"OFF"` | `False`
        """
        if ip_address is not None:
            self.instrument.write(f"CONF:GEN:IPC:ADDR {ip_address!r};*WAI")

        if state is not None:
            match str(state).casefold():
                case "on" | "true":
                    self.instrument.query("CONF:GEN:CONT ON;*OPC?")
                case "off" | "false":
                    self.instrument.query("CONF:GEN:CONT OFF;*OPC?")

    def configure_reference_signal(
        self,
        load_filepath: str | None = None,
        read_from_signal_generator: bool = False,
    ) -> None:
        """Configures the reference signal.

        * load_filepath: Path to select a waveform file containing a reference signal.

        * read_from_signal_generator: Import reference signal data from the generator.
        """
        if load_filepath is not None:
            self.instrument.query(f"CONF:REFS:CWF:FPAT {load_filepath!r};*OPC?")
            self.instrument.write("CONF:REFS:CWF:WRITE;*WAI")

        if read_from_signal_generator:
            self.instrument.query("CONF:REFS:CGW:READ;*OPC?")

    def get_aclr_channel_power(self) -> dict[float]:
        """Returns the power for every active transmission and adjacent channel."""
        switch_back = False
        if int(self.instrument.query("INIT:CONT?")) == 1:
            self.set_sweep(mode="single")
            switch_back = True
        self.instrument.write("INIT;*WAI")
        tmp = self.instrument.query("CALC:MARK:FUNC:POW:RES? MCAC").split(sep=",")
        if switch_back:
            self.set_sweep(mode="continuous")

        carrier_number = int(self.instrument.query("POW:ACH:TXCH:COUN?"))
        data = [float(val) for val in tmp]
        res = {}
        if carrier_number == 1:
            transmission_power = data[:1]
            adjacent_channel_power = data[1:]
        else:
            transmission_power = data[: carrier_number + 1]
            adjacent_channel_power = data[carrier_number + 1 :]

        res["tx_total"] = transmission_power.pop()
        for i, tx in enumerate(transmission_power):
            res[f"tx_{i+1}"] = tx

        alt_channel = 1
        while adjacent_channel_power:
            res[f"aclr_lower_{alt_channel}"] = adjacent_channel_power.pop(0)
            res[f"aclr_upper_{alt_channel}"] = adjacent_channel_power.pop(0)
            alt_channel += 1

        return res

    def get_power_maximum(self) -> float:
        """Returns the maximum signal power at the DUT output as shown in the Result Summary."""
        return float(self.instrument.query("FETC:POW:OUTP:MAX?"))

    def get_power_minimum(self) -> float:
        """Returns the minimum signal power at the DUT output as shown in the Result Summary."""
        return float(self.instrument.query("FETC:POW:OUTP:MIN?"))

    def get_power_current(self) -> float:
        """Returns the current signal power at the DUT output as shown in the Result Summary."""
        return float(self.instrument.query("FETC:POW:OUTP:CURR?"))

    def get_raw_evm_maximum(self) -> float:
        """Returns the maximum raw EVM (in %) as shown in the Result Summary."""
        return float(self.instrument.query("FETC:MACC:REVM:MAX?"))

    def get_raw_evm_minimum(self) -> float:
        """Returns the minimum raw EVM (in %) as shown in the Result Summary."""
        return float(self.instrument.query("FETC:MACC:REVM:MIN?"))

    def get_raw_evm_current(self) -> float:
        """Returns the current raw EVM (in %) as shown in the Result Summary."""
        return float(self.instrument.query("FETC:MACC:REVM:CURR?"))
