import sys
import time
import vector
import logging
import argparse
import os
from control.SA import *
from control.CNC import *


def main():

    logging.basicConfig()
    logger = logging.getLogger("main")
    logger.setLevel(logging.DEBUG)

    ## define script arguments and hardware variables
    parser = argparse.ArgumentParser(
        prog="emi collector",
        description="Take measurements with EMI-collector using this script. Make sure your CNC and SA are connected to your PC.",
    )
    parser.add_argument("x", type=int, help="X dimension of the board in mm")
    parser.add_argument("y", type=int, help="Y dimension of the board in mm")
    parser.add_argument(
        "SAaddr", type=str, help="Spectrum Analyser IP addres for connection"
    )
    parser.add_argument(
        "CNC", type=str, help="Serial port on which a plotter is connected to the PC"
    )
    parser.add_argument("PATH", type=str, help="Path to keep the measurements in")
    parser.add_argument(
        "-s",
        "--step",
        type=int,
        nargs=2,
        help="Set a measurement step in mm, x, y. Default is 5 5",
        default=[5, 5],
    )
    parser.add_argument(
        "-o",
        "--offset",
        type=int,
        nargs=3,
        help="Start measurements with offset from home position, x y z. Default is 0 0 0.",
        default=[0, 0, 0],
    )
    parser.add_argument(
        "-f",
        "--frequency_range",
        type=int,
        nargs=2,
        help="Pass a measurement frequency range in Hz as two floats. Default is 30000000 1000000000.",
        default=[30000000, 1000000000],
    )
    parser.add_argument(
        "-u",
        "--units",
        type=str,
        choices=["dBuV", "dBm", "dBmV", "V", "W"],
        help="Choose a unit for the measurement.",
        default="dBuV",
    )
    parser.add_argument(
        "-d",
        "--detectors",
        type=str,
        choices=["POS", "RMS", "QUASI"],
        help="Choose a spectrum analyser's peak detector type for the measurement.",
        default="POS",
    )
    args = parser.parse_args()
    path_dir = args.PATH

    # check for path
    if os.path.exists(path_dir):
        pass
    else:
        print("Path not found, creating one...")
        try:
            os.makedirs(path_dir)
        except:
            logger.error(f"Couldn't create {path_dir}")
            sys.exit()

    ## get the offset from arg
    offsets = args.offset
    unit_functions = {
        "dBuV": setY_dBuV,
        "dBm": setY_dBm,
        "dBmV": setY_dBmV,
        "V": setY_V,
        "W": setY_W,
    }
    detector_functions = {
        "POS": setPosPeakDet,
        "RMS": setRMSDet,
        "QUASI": setQPeakDet,
    }
    # initiate measurement procedure

    SA_ADDRESS = args.SAaddr
    PRINTER_DEVICE = ""
    STEP_X = args.step[0]
    STEP_Y = args.step[1]

    freq_min = args.frequency_range[0]
    freq_max = args.frequency_range[1]

    COUNT_X = int(args.x / STEP_X)
    COUNT_Y = int(args.y / STEP_Y)

    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        print(port, args.CNC)
        if args.CNC in port:
            PRINTER_DEVICE = port
        print("{}: {} [{}]".format(port, desc, hwid))
    if PRINTER_DEVICE == "":
        print("CNC not found, exiting")
        sys.exit()

    instr = init_instrument(SA_ADDRESS)
    plotter = init_plotter(PRINTER_DEVICE)

    ## measurement settings
    selected_det = detector_functions.get(args.detectors)
    if selected_det:
        selected_det(instr)
    else:
        print("Invalid detector specified")
    selected_unit = unit_functions.get(args.units)
    if selected_unit:
        selected_unit(instr)
    else:
        print("Invalid unit specified")
    set_frequency_span(instr, freq_min, freq_max)
    start_pos = get_plotter_position(plotter)
    offset_pos = vector.obj(
        x=start_pos.x + offsets[0],
        y=start_pos.y + offsets[1],
        z=start_pos.z + offsets[2],
    )

    # taking the measurements
    start, stop = query_frequency_span(instr)
    moveAbs_plotter_to(plotter, offset_pos)

    # equally distributed points accros the board with a STEP
    for x in range(COUNT_X):
        for y in range(COUNT_Y):
            x_pos = STEP_X * x + offset_pos.x
            y_pos = STEP_Y * y + offset_pos.y
            moveAbs_plotter_to(plotter, vector.obj(x=x_pos, y=y_pos, z=offset_pos.z))
            time.sleep(3)
            # saving measurement data
            data = query_spectrum(instr)
            save_data(
                data,
                start,
                stop,
                Path(os.path.join(path_dir, f"x{x_pos}_y{y_pos}.csv")),
            )
    # going back to home
    moveAbs_plotter_to(plotter, start_pos)


if __name__ == "__main__":
    main()
