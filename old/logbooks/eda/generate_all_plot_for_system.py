import warnings

import matplotlib.pyplot as plt
import numpy as np
import wotan
import wquantiles
from astropy.table import Table
from astropy.utils.exceptions import AstropyWarning
from scipy import stats
from scipy.fftpack import rfft, irfft, fftfreq

from old.src.cpoc import align_data, period_stupid_search
from old.src.eclipses import get_eclipses, get_threshold
from old.src.handle_double_eclipses import remove_doubles
from old.src.noise_filtering import remove_low_noise, remove_high_noise, remove_outliers
from old.utils.set_dir_to_root import set_dir_to_root


def basic_plot(x, y, xlabel, ylabel, title, path, scatter=True):
    fig, ax = plt.subplots(figsize=(12.8, 7.2))

    if scatter:
        ax.scatter(x, y)
    else:
        ax.plot(x, y)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.savefig(path, dpi=fig.dpi, bbox_inches="tight")


if __name__ == "__main__":
    set_dir_to_root()

    with open("data/all_systems.txt") as f:
        all_systems = f.read().split(",")

    # with open("data/cpop_diagnostics.txt", "w") as out:
    #    out.write("noise,outliers,doubles,density\n")

    file = 181

    # TODO if something breaks, remove this bit and see what it is
    warnings.filterwarnings('ignore', category=AstropyWarning, append=True)

    eclipses = []
    curr = get_eclipses(all_systems[file], "data/combined")
    eclipses.append(curr.reset_index(drop=True))

    if wquantiles.quantile(eclipses[0]["delta"], eclipses[0]["delta"], 0.75) > 1 and stats.mstats.trimmed_std(
            eclipses[0]["delta"]) > 0.7:
        curr = remove_low_noise(eclipses[0], "delta", return_dropped=False)
    elif wquantiles.quantile(eclipses[0]["delta"], eclipses[0]["delta"], 0.75) > 1:
        curr = remove_high_noise(eclipses[0], "delta", return_dropped=False)

    eclipses.append(curr.reset_index(drop=True))

    backup = curr.copy()
    curr = remove_outliers(curr, "delta", return_dropped=False)
    if curr.empty:
        curr = backup

    eclipses.append(curr.reset_index(drop=True))

    curr = remove_doubles(curr, "delta", return_handling_happened=False)
    eclipses.append(curr.reset_index(drop=True))

    period = period_stupid_search(curr['time'], curr['delta'])
    period = period * round(curr["delta"].median() / period, 0)
    curr["residuals"] = align_data(curr["time"], period / 2) % period - period / 2
    eclipses.append(curr)

    y = curr["residuals"].values - curr["residuals"].mean()

    N = len(y)
    T = curr["time"].max() / N

    f_signal = rfft(y)
    W = fftfreq(y.size, d=T)
    xf = np.linspace(0.0, 1.0 / (2.0 * T), N // 2)

    culled_f_signal = f_signal.copy()
    culled_f_signal[((abs(W) > 0.0025) & (abs(W) < 0.003))] = 0
    culled_f_signal[(abs(W) > 0.05)] = 0
    culled_f_signal[(W < 0)] = 0

    culled_signal = irfft(culled_f_signal)
    curr["culled_residuals"] = culled_signal

    eclipses.append(curr.reset_index(drop=True))

    SMALL_SIZE = 15
    MEDIUM_SIZE = 20
    BIGGER_SIZE = 25
    TITLE_PADDING = 23

    plt.rc('font', size=SMALL_SIZE)
    plt.rc('axes', titlesize=SMALL_SIZE)
    plt.rc('axes', labelsize=MEDIUM_SIZE)
    plt.rc('axes', titlepad=TITLE_PADDING)
    plt.rc('xtick', labelsize=SMALL_SIZE)
    plt.rc('ytick', labelsize=SMALL_SIZE)
    plt.rc('legend', fontsize=SMALL_SIZE)
    plt.rc('figure', titlesize=BIGGER_SIZE)

    indexes = ["delta", "delta", "delta", "delta", "residuals", "culled_residuals"]
    time_scale_factor = [1, 1, 1, 1, 1440, 1440]
    ylabels = ["Eclipse Timings / day", "Eclipse Timings / day", "Eclipse Timings / day", "Eclipse Timings / day",
               "Observed - Calculated / min", "Observed - Calculated / min"]
    titles = ["Plot of Eclipse Timings / day against Time / day", "Plot of Eclipse Timings / day against Time / day",
              "Plot of Eclipse Timings / day against Time / day", "Plot of Eclipse Timings / day against Time / day",
              "Plot of Eclipse Timing Variation / min against Time / day",
              "Plot of Eclipse Timing Variation / min against Time / day"]

    for i in range(len(eclipses)):
        basic_plot(eclipses[i]["time"], eclipses[i][indexes[i]] * time_scale_factor[i],
                   "Time / days", ylabels[i], titles[i], f"generated/set_for_system/plot_{i}")

    basic_plot(xf * 1000, 2.0 / N * np.abs(f_signal[:N // 2]), "Frequency / mHz", "Relative amplitude",
               "Frequency spectrum of Eclipse Timings", "generated/set_for_system/unculled_fft", scatter=False)

    basic_plot(xf * 1000, 2.0 / N * np.abs(culled_f_signal[:N // 2]), "Frequency / mHz", "Relative amplitude",
               "Culled frequency spectrum of Eclipse Timings", "generated/set_for_system/culled_fft", scatter=False)

    table = Table.read("data/combined/" + all_systems[file], format="fits")

    times = table["TIME"]
    sap_fluxes = table["SAP_FLUX"]

    flattened_lc = wotan.flatten(times, sap_fluxes, window_length=0.5, method='biweight')

    times = times - times.min()
    median = np.nanmedian(flattened_lc)
    std = np.nanstd(flattened_lc)
    threshold = get_threshold(median, std)

    fig, ax = plt.subplots(figsize=(12.8, 7.2))

    ax.plot(times, sap_fluxes, '-k', label='Detrended Flux')
    ax.set_title('Raw Light Curve')
    ax.set_xlabel('Time (days)')
    ax.set_ylabel('Flux (electrons/second)')
    fig.savefig("generated/set_for_system/raw_light_curve", dpi=fig.dpi, bbox_inches="tight")

    fig, ax = plt.subplots(figsize=(12.8, 7.2))

    ax.plot(times, flattened_lc, '-k', label='Detrended Flux')
    ax.plot(plt.axis()[:2], [threshold, threshold], "-b", linewidth=3)
    ax.set_title('Detrended Light Curve')
    ax.set_xlabel('Time (days)')
    ax.set_ylabel('Detrended Flux (electrons/second)')
    fig.savefig("generated/set_for_system/detrended_light_curve", dpi=fig.dpi, bbox_inches="tight")
