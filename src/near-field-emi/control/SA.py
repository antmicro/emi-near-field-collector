from typing import Literal, Tuple
import vxi11
import logging
import numpy as np
from pathlib import Path
import sys


logging.basicConfig()
logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)


def init_instrument(address: str) -> vxi11.Instrument:
    instr = vxi11.Instrument(address)
    instr.write("FORMAT REAL,32")
    return instr


def query_spectrum(
    instr: vxi11.Instrument,
) -> np.ndarray[Literal["N"], np.dtype[np.float32]]:
    data = instr.ask_raw("TRACe:DATA? TRACE1".encode("ASCII"))
    if data[0] != b"#"[0]:
        logger.error("Response from SA didn't begin with '#'")
        sys.exit()
    len_of_count = int(data[1:2].decode("ASCII"))
    count = int(data[2 : 2 + len_of_count])
    logger.debug("Received data from SA. Count: %d", count)
    return np.frombuffer(data[2 + len_of_count : -1], dtype=np.dtype(np.float32))


def query_frequency_span(
    instr: vxi11.Instrument,
) -> Tuple[float, float]:
    start = float(instr.ask("FREQuency:STARt?"))
    stop = float(instr.ask("FREQuency:STOP?"))
    logger.debug("Received frequency span from SA. Start: %f, stop: %f", start, stop)
    return start, stop


def set_frequency_span(instr: vxi11.Instrument, start: float, stop: float):
    instr.write(f"FREQuency:STARt {start}; STOP {stop};")


def set_RBW(instr: vxi11.Instrument, value: float):
    instr.write({f"[:SENSe]:BANDwidth[:RESolution] {value}"})


def calculate_frequencies(
    start: float, stop: float, count: int
) -> np.ndarray[Literal["N"], np.dtype[np.float32]]:
    return np.linspace(start, stop, count, dtype=np.float32)


def setPosPeakDet(instr: vxi11.Instrument):
    instr.write(f":SENSe:DETector:FUNCtion POSitive")


def setRMSDet(instr: vxi11.Instrument):
    instr.write(f":SENSe:DETector:FUNCtion RMS")


def setQPeakDet(instr: vxi11.Instrument):
    instr.write(f":SENSe:DETector:FUNCtion QPEak")


def getDet(instr: vxi11.Instrument):
    det = str(instr.ask(":SENSe:DETector:FUNCtion?"))
    logger.info(f"Detector: {det}")
    return det


def setY_dBm(instr: vxi11.Instrument):
    instr.write(":UNIT:POWer DBM")


def setY_dBmV(instr: vxi11.Instrument):
    instr.write(":UNIT:POWer DBMV")


def setY_dBuV(instr: vxi11.Instrument):
    instr.write(":UNIT:POWer DBUV")


def setY_V(instr: vxi11.Instrument):
    instr.write(":UNIT:POWer V")


def setY_W(instr: vxi11.Instrument):
    instr.write(":UNIT:POWer W")


def save_data(
    data: np.ndarray[Literal["N"], np.dtype[np.float32]],
    start: float,
    stop: float,
    path: Path,
) -> None:
    freqs = calculate_frequencies(start, stop, len(data))
    data_with_freqs = np.stack((freqs, data), axis=1)
    if path.parent.exists():
        np.savetxt(
            path, data_with_freqs, delimiter=",", newline="\n", header="f[Hz], a[dB]"
        )
    else:
        logger.error("Directory %s doesn't exist", path.parent)
