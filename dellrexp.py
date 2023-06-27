
# Copyright (c) Meta Platforms, Inc. and affiliates.

# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json
import itertools
import math
import sys

from collections import defaultdict
from operator import add
import matplotlib.pyplot as plt
import numpy as np

from dram_model import Fab_DRAM
from hdd_model  import Fab_HDD
from ssd_model  import Fab_SSD
from logic_model  import Fab_Logic

from operational import get_operational_carbon

debug = False

dellr740_large_ssd = 957 # GB (1.92 TB)
dellr740_dram      = 32 + (32 / 8) #36 # GB (32 + 4 ECC GB x 12)

def get_embodied_carbon(dellr740_dram, dellr740_large_ssd):
    dellr740_ssd_dram  = 68 # GB (64 + 4GB ECC)
    ic_yield           = 0.875

    cpu_area = 6.98 #cm^2

    ##############################
    # Estimated process technology node to mimic fairphone LCA process node
    ##############################
    CPU_Logic = Fab_Logic(gpa  = "95",
                        carbon_intensity = "src_coal",
                        process_node = 7,
                        fab_yield=ic_yield)

    SSD_main           = Fab_SSD(config  = "western_digital_2019", fab_yield = ic_yield)
    # SSD_secondary      = Fab_SSD(config  = "nand_30nm", fab_yield = ic_yield)
    DRAM_SSD_main      = Fab_DRAM(config = "ddr3_30nm", fab_yield = ic_yield)
    DRAM_SSD_secondary = Fab_DRAM(config = "ddr4_10nm", fab_yield = ic_yield)
    DRAM               = Fab_DRAM(config = "ddr4_10nm", fab_yield = ic_yield)

    ##############################
    # Computing carbon footprint of IC's
    ##############################
    CPU_Logic.set_area(cpu_area)
    DRAM.set_capacity(dellr740_dram)

    DRAM_SSD_main.set_capacity(dellr740_ssd_dram)
    SSD_main.set_capacity(dellr740_large_ssd)

    DRAM_SSD_secondary.set_capacity(dellr740_ssd_dram)
    # SSD_secondary.set_capacity(dellr740_ssd)

    ##################################
    # Computing the packaging footprint
    ##################################
    # number of packages
    ssd_main_nr         = 12 + 1
    # ssd_secondary_nr    = 12 + 1
    dram_nr             = 18 + 1
    cpu_nr              = 2
    packaging_intensity = 150 # gram CO2

    SSD_main_packaging      = packaging_intensity * ssd_main_nr
    # SSD_secondary_packaging = packaging_intensity * ssd_secondary_nr
    DRAM_packging           = packaging_intensity * dram_nr
    CPU_packaging           = packaging_intensity * cpu_nr

    total_packaging = SSD_main_packaging +  \
                    DRAM_packging + \
                    CPU_packaging
    total_packaging = total_packaging / 1000.

    ##################################
    # Compute end-to-end carbon footprints
    ##################################
    SSD_main_count = 1 # There are 8x3.84TB SSD's
    SSD_main_co2 = (SSD_main.get_carbon() + \
                    DRAM_SSD_main.get_carbon() + \
                    SSD_main_packaging) / 1000.
    # print(SSD_main.get_carbon(), DRAM_SSD_main.get_carbon(), SSD_main_packaging)
    SSD_main_co2 = SSD_main_co2 * SSD_main_count

    # SSD_secondary_count = 1 # There are 1x400GB SSD's
    # SSD_secondary_co2 = (SSD_secondary.get_carbon() + \
    #                      DRAM_SSD_secondary.get_carbon() +  \
    #                      SSD_secondary_packaging) / 1000.
    # SSD_secondary_co2 = SSD_secondary_co2 * SSD_secondary_count

    DRAM_count = math.ceil(dellr740_dram) / 32 # There are 12 x (32GB+4GB ECC DRAM modules)
    DRAM_co2 = (DRAM.get_carbon() + DRAM_packging) / 1000. * DRAM_count
    if (not dellr740_dram): 
        DRAM_co2 = 0
    if (not dellr740_large_ssd):
        SSD_main_co2 = 0

    CPU_count = 1
    CPU_co2   = (CPU_Logic.get_carbon() + CPU_packaging) * CPU_count / 1000.

    # print(f"\tEmbodied power (flash, cpu, dram): {SSD_main_co2, CPU_co2, DRAM_co2}")
    return (SSD_main_co2, DRAM_co2, CPU_co2)

# if debug:
#     print("ACT SSD main", SSD_main_co2, "kg CO2")
#     # print("ACT SSD secondary", SSD_secondary_co2, "kg CO2")
#     print("ACT DRAM", DRAM_co2, "kg CO2")
#     print("ACT CPU", CPU_co2, "kg CO2")
#     print("ACT Packaging", total_packaging, "kg CO2")

# print("--------------------------------")
# print("ACT SSD main", SSD_main_co2, "kg CO2 ")
# # print("ACT SSD secondary", SSD_secondary_co2, "kg CO2 vs. LCA 64.1 kg CO2")
# print("ACT DRAM", DRAM_co2, "kg CO2 ")
# print("ACT CPU", CPU_co2, "kg CO2 ")
# print(f"Total: {SSD_main_co2 + DRAM_co2 + CPU_co2} kg")

def graph_by_location_and_flash_cap(inputs):
    by_location = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for (dram, ssd, life, location), (e_carbon, i_carbon) in inputs.items():
        by_location[location][ssd][life].append((dram, e_carbon, i_carbon))

    o_colors = ["pink", "lightblue", "moccasin", "gray"]
    e_colors = ["red", "blue", "orange", "black"]

    for location, by_flash in by_location.items():
        for flash_cap, by_lifetime in  by_flash.items():

            fig, ax = plt.subplots(figsize=(10, 5))
            width = .15
            spacing = .2

            for i, (lifetime, points) in enumerate(by_lifetime.items()):
                drams, e_carbons, o_carbons = zip(*points)
                x = np.arange(0, len(drams))
                # print(drams, e_carbons, o_carbons)

                this_x = x + (i - 1) * spacing
                p2 = plt.bar(this_x, e_carbons, width, color=e_colors[i], label=f"{lifetime} years: Embodied")
                p1 = plt.bar(this_x, o_carbons, width, color=o_colors[i], bottom=e_carbons, label=f"{lifetime} years: Operational")
                # p.label()
                plt.bar_label(p1, label_type='center', color='w', fmt="%d")
                plt.bar_label(p2, label_type='center', color='w', fmt="%d")
                # plt.bar(x, o_carbons , label=f"Operational Carbon ({lifetime} years)")
        
            plt.xticks(x, [str(d) for d in drams])
            plt.xlabel('DRAM capacity')
            plt.ylabel('Carbon Emissions (kg/year)')
            plt.legend()
            plt.tight_layout()

            savename = f"graphs/cpu125watts-dram3watts/{location}_{flash_cap}flash.pdf"
            plt.savefig(savename)
            plt.clf()
            plt.close()
            print(f"Saved figure to {savename}")

if __name__ == '__main__':
    dram_caps = [32, 64, 128, 192, 1024]
    # dram_caps_plus_ecc = 
    ssd_caps = [1820, 3840, 7680] #[0, 980, 1820, 3840, 7680]
    lifetimes = [3, 6, 9]
    # print(dram_caps_plus_ecc)
    carbon = {}
    for dram, ssd in itertools.product(dram_caps, ssd_caps):
        print(f"DRAM: {dram}, SSD: {ssd}")
        dram_with_ecc = dram + dram/8
        e_carbon = sum(get_embodied_carbon(dram_with_ecc, ssd)) # over lifetime
        print(f"\tret {e_carbon}")
        o_carbons = get_operational_carbon(dram, ssd) # per year
        o_carbons = {k: sum(v) for (k, v) in o_carbons.items()}
        for life in lifetimes:
            for location, op in o_carbons.items():
                carbon[(dram, ssd, life, location)] = (e_carbon / life, op)

    # print(len(carbon.items()))

    graph_by_location_and_flash_cap(carbon)

