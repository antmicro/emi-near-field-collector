import pandas as pd
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import RectBivariateSpline
from scipy import integrate
import sys
import math


def load_measurement(folder_path: str):
    csv_files = [file for file in os.listdir(folder_path) if file.endswith(".csv")]
    combined_df = pd.DataFrame()
    for file in csv_files:
        floor = file.find("_")
        x_value = file[1:floor]
        y_value = file[floor + 2 : -4]

        df = pd.read_csv(os.path.join(folder_path, file))

        df["x"] = float(x_value)
        df["y"] = float(y_value)
        combined_df = pd.concat([combined_df, df], ignore_index=True)
    combined_df = combined_df.rename(columns={"# f[Hz]": "f", " a[dB]": "a"})
    return combined_df


def define_unit(number: float):
    if number >= 1e9:
        return f"{number / 1e9:.1f} GHz"
    elif number >= 1e6:
        return f"{number / 1e6:.1f} MHz"
    elif number >= 1e3:
        return f"{number / 1e3:.1f} kHz"
    else:
        return f"{number:.1f} Hz"


def define_ranges(range_list: list, step: float):
    start, end = range_list
    end1 = end
    if start % step != 0:
        end1 = math.ceil(start / step) * step * 2
    ranges = [(start, end1)]
    num_ranges = (end - end1) // step
    for i in range(math.floor(num_ranges)):
        ranges.append((end1 + i * step, end1 + (i + 1) * step))
    if end1 + num_ranges * step < end:
        ranges.append((end1 + num_ranges * step, end))
    return ranges


def define_plot_titles(ranges: list):
    titles = []
    for start, end in ranges:
        start_title = define_unit(start)
        end_title = define_unit(end)
        title = f"{start_title} - {end_title}"
        titles.append(title)
    return titles


def get_meas_coords(meas_df: pd.DataFrame):
    x = np.array(sorted(meas_df["x"].unique()))
    y = np.array(sorted(meas_df["y"].unique()))
    return x, y


def round_one_digit(num: float):
    return round(num, 1)


def remove_background(backmeas: pd.DataFrame, mainmeas: pd.DataFrame):
    backmeas["f"] = backmeas["f"].apply(round_one_digit)
    mainmeas["f"] = mainmeas["f"].apply(round_one_digit)
    mainmeas["a"] = mainmeas["a"] - backmeas["a"]
    return mainmeas


def integrate_amplitude_squared(measurement: pd.DataFrame, frequency_ranges: list):
    intervals = []
    for i, (start_freq, end_freq) in enumerate(frequency_ranges):
        df = measurement[
            (measurement["f"] > start_freq) & (measurement["f"] < end_freq)
        ]
        interval_df = (
            df.groupby(["x", "y"])
            .apply(lambda g: integrate.trapezoid(g.a**2, x=g.f), include_groups=False)
            .reset_index()
        )
        intervals.append(interval_df)
        intervals[i].columns = ["x", "y", "a"]
    return intervals


def integrate_amplitude_divide_pi(measurement: pd.DataFrame, frequency_ranges: list):
    intervals = []
    for i, (start_freq, end_freq) in enumerate(frequency_ranges):
        df = measurement[
            (measurement["f"] > start_freq) & (measurement["f"] < end_freq)
        ]
        interval_df = (
            df.groupby(["x", "y"])
            .apply(
                lambda g: integrate.trapezoid(g.a, x=g.f) / np.pi,
                include_groups=False,
            )
            .reset_index()
        )
        intervals.append(interval_df)
        intervals[i].columns = ["x", "y", "a"]
    return intervals


def measurement_interpolation(freq_intervals: list):
    Xs = []
    Ys = []
    Zs = []
    color_max = 0
    color_min = np.inf
    for df in freq_intervals:
        if df["a"].min() < color_min:
            color_min = df["a"].min()
        if df["a"].max() > color_max:
            color_max = df["a"].max()
        x, y = get_meas_coords(df)
        table = df.pivot(index="x", columns="y", values="a")
        vals = table.values
        new_size_x = len(x) * 120
        new_size_y = len(y) * 120
        interp_func = RectBivariateSpline(x, y, vals, kx=3, ky=3)
        new_x = np.linspace(x[0], x[-1], new_size_x)
        new_y = np.linspace(y[0], y[-1], new_size_y)
        interpolated_vals = interp_func(new_x, new_y)
        Y, X = np.meshgrid(new_y, new_x)
        Xs.append(X)
        Ys.append(Y)
        Zs.append(interpolated_vals)
    return Xs, Ys, Zs, color_max, color_min


def show_interval_plots(Xs, Ys, Zs, color_max, color_min, titles, path):
    i = 0
    subs_size = len(titles)
    plt_rows = math.ceil(subs_size / 5)
    fig, axs = plt.subplots(plt_rows, 5, figsize=(20, plt_rows * 4))
    for i in range(0, len(Xs)):
        row = i // 5
        col = i % 5
        if subs_size > 5:
            pmesh = axs[row, col].pcolormesh(
                Xs[i], Ys[i], Zs[i], vmax=color_max, vmin=color_min, shading="nearest"
            )
            axs[row, col].set_title(titles[i])
            axs[row, col].xaxis.tick_bottom()
            axs[row, col].xaxis.set_label_position("bottom")
            axs[row, col].set_aspect("equal")
            plt.gca().spines["bottom"].set_visible(False)
            fig.colorbar(pmesh, ax=axs[row, col])
        if subs_size <= 5:
            pmesh = axs[col].pcolormesh(
                Xs[i], Ys[i], Zs[i], vmax=color_max, vmin=color_min, shading="nearest"
            )
            axs[col].set_title(titles[i])
            axs[col].xaxis.tick_bottom()
            axs[col].xaxis.set_label_position("bottom")
            axs[col].set_aspect("equal")
            plt.gca().spines["bottom"].set_visible(False)
            fig.colorbar(pmesh, ax=axs[col])
        fig.savefig(path + "/out.png", bbox_inches="tight", pad_inches=0)
        plt.title(titles[i])
        plt.axis("off")
        i += 1
    plt.tight_layout()
    plt.show()


def save_heatmaps_color(Xs, Ys, Zs, color_max, color_min, titles, path):
    i = 0
    for i in range(0, len(Xs)):
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.pcolormesh(
            Xs[i], Ys[i], Zs[i], vmax=color_max, vmin=color_min, shading="nearest"
        )
        ax.xaxis.tick_bottom()
        ax.xaxis.set_label_position("bottom")
        ax.set_aspect("equal")
        plt.gca().spines["bottom"].set_visible(False)
        plt.axis("off")
        fig.savefig(
            f"{path}/color/{titles[i]}.png",
            bbox_inches="tight",
            pad_inches=0,
            dpi=700,
        )
        i += 1


def save_heatmaps_grey(Xs, Ys, Zs, color_max, color_min, titles, path):
    i = 0
    for i in range(0, len(Xs)):
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.pcolormesh(
            Xs[i],
            Ys[i],
            Zs[i],
            vmax=color_max,
            vmin=color_min,
            shading="nearest",
            cmap="grey",
        )
        ax.xaxis.tick_bottom()
        ax.xaxis.set_label_position("bottom")
        ax.set_aspect("equal")
        plt.gca().spines["bottom"].set_visible(False)
        plt.axis("off")
        fig.savefig(
            f"{path}/grey/{titles[i]}_grey.png",
            bbox_inches="tight",
            pad_inches=0,
            dpi=700,
        )
        i += 1


def main():

    parser = argparse.ArgumentParser(
        prog="emi collector",
        description="Take measurements with EMI-collector using this script. Make sure your CNC and SA are connected to your PC.",
    )
    parser.add_argument("PATH", type=str, help="Path to measurement files")
    parser.add_argument(
        "-b",
        "--remove-background",
        type=str,
        help="Add a path to measurement of background noise taken in the same frequency range to remove background from displayed heatmap",
    )
    parser.add_argument(
        "--heatmap-path",
        type=str,
        help="Path to save generated heatmaps",
        default=os.getcwd(),
    )
    parser.add_argument(
        "-ag",
        "--aggregation",
        type=str,
        choices=["amplitude", "amplitude-squared"],
        help="Choose a way to aggregate your data, you can integrate amplitude or amplitude squared over frequency interval. Default is amplitude",
        default="amplitude",
    )
    parser.add_argument(
        "-s",
        "--step",
        type=float,
        help="Choose a step of frequency intervals in Hz for heatmap generation. Default is 50000000",
        default=50000000.0,
    )
    args = parser.parse_args()
    if os.path.isdir(args.PATH):
        pass
    else:
        print(f"Path doesn't exist {args.PATH}")
        sys.exit()
    if not os.path.exists(os.path.join(args.heatmap_path, "grey")):
        os.makedirs(os.makedirs(os.path.join(args.heatmap_path, "grey")))
    elif not os.path.exists(os.path.join(args.heatmap_path, "color")):
        os.makedirs(os.path.join(args.heatmap_path, "color"))
    meas = load_measurement(args.PATH)
    freq_top = meas["f"].max()
    freq_bot = meas["f"].min()
    interval_list = define_ranges([freq_bot, freq_top], args.step)
    titles = define_plot_titles(interval_list)
    measurement_intervals = pd.DataFrame()
    if args.remove_background is not None:
        background = load_measurement(args.remove_background)
        meas = remove_background(mainmeas=meas, backmeas=background)
    if args.aggregation == "amplitude":
        measurement_intervals = integrate_amplitude_divide_pi(
            measurement=meas, frequency_ranges=interval_list
        )
    if args.aggregation == "amplitude-squared":
        measurement_intervals = integrate_amplitude_squared(
            measurement=meas, frequency_ranges=interval_list
        )
    XX, YY, ZZ, v_max, v_min = measurement_interpolation(measurement_intervals)
    show_interval_plots(XX, YY, ZZ, v_max, v_min, titles, args.heatmap_path)
    save_heatmaps_grey(XX, YY, ZZ, v_max, v_min, titles, args.heatmap_path)
    save_heatmaps_color(XX, YY, ZZ, v_max, v_min, titles, args.heatmap_path)


if __name__ == "__main__":
    main()
