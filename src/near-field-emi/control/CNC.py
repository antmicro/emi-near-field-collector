import time
import serial.tools.list_ports
import logging
import vector
import re


logging.basicConfig()
logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)


def init_plotter(device: str) -> serial.Serial:
    plotter = serial.Serial(device, baudrate=115200)
    time.sleep(3)
    plotter.read_all()
    send_to_plotter(plotter, "M420 S0", wait=False)  # Disable autoleveld
    send_to_plotter(plotter, "G21")
    send_to_plotter(plotter, "G92 X0")
    send_to_plotter(plotter, "G92 Y0")
    send_to_plotter(plotter, "G92 Z0")
    time.sleep(3)
    return plotter


def send_to_plotter(
    plotter: serial.Serial, command: str, wait: bool = True, timeout=10
) -> None:
    plotter.read_all()
    plotter.timeout = timeout
    logger.debug("Sending to plotter: %s", command)
    plotter.write((command + "\r\n").encode("ASCII"))
    if wait:
        plotter.write("M400\r\n".encode("ASCII"))
        p = plotter.readline()
        plotter.readline()
        plotter.readline()
        logger.debug(f"{p}")


def moveAbs_plotter_to(plotter: serial.Serial, position: vector.Vector3D) -> None:
    send_to_plotter(
        plotter, f"G90 X{position.x:.2f} Y{position.y:.2f} Z{position.z:.2f}"
    )


def moveRel_plotter_to(plotter: serial.Serial, position: vector.Vector3D) -> None:
    send_to_plotter(
        plotter, f"G91 X{position.x:.2f} Y{position.y:.2f} Z{position.z:.2f}"
    )


def get_plotter_position(plotter: serial.Serial) -> vector.Vector3D:
    send_to_plotter(plotter, "?", wait=False)
    ret = plotter.readline()
    ret = ret.decode("ASCII")
    ret = ret[10:]

    def get_coordinate(ret):
        match = re.findall(f"(-?[0-9]+.[0-9]+)", ret)
        if match is not None:
            return float(match[0]), float(match[1]), float(match[2])

    x, y, z = get_coordinate(ret)
    logger.info(f"Printer pos \n x:{x}, y:{y}, z:{z}")
    return vector.obj(x=x, y=y, z=z)
