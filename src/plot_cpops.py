import matplotlib.pyplot as plt
import warnings

import numpy as np
from astropy.utils.exceptions import AstropyWarning

from src.cpop import getOC, align_data
from src.eclipses import get_eclipses
from src.noise_filtering import complete_filter

import statsmodels.api as sm

from utils.set_dir_to_root import set_dir_to_root

if __name__ == "__main__":
    set_dir_to_root()

    with open("data/all_systems.txt") as f:
        all_systems = f.read().split(",")

    with open("data/cpop_diagnostics.txt", "w") as out:
        out.write("noise,outliers,doubles,density\n")

    start = 0
    end = 2864

    # TODO if something breaks, remove this bit and see what it is
    warnings.filterwarnings('ignore', category=AstropyWarning, append=True)

    for i in range(start, end+1):
        if i % 10 == 0:
            print("\nProcessing Number " + str(i))
            plt.close("all")
        eclipses = get_eclipses(all_systems[i], "data/combined")

        eclipses, period, diagnostics = getOC(eclipses, return_diagnostics=True)

        fig, ax = plt.subplots(figsize=(19.2, 10.8))
        ax.scatter(x=eclipses["time"], y=eclipses["culled_residuals"] * 1440)  # Conversion to minutes
        fig.savefig(f"generated/cpop/{i}_cpop", dpi=fig.dpi, bbox_inches="tight")

        with open("data/cpop_diagnostics.txt", "a") as out:
            out.write(f"{diagnostics[0]},{diagnostics[1]},{diagnostics[2]},{diagnostics[3]}\n")
