#!/usr/bin/env python3
import argparse

import matplotlib.pyplot as plt
import numpy
import matplotlib

from dellrexp import get_embodied_carbon
from operational import get_operational_carbon

# write rate multiple, cost multiple
# write rate multiples from https://blocksandfiles.com/2019/08/07/penta-level-cell-flash/ at 5xnm
# cost is estimate based on more bits (relative to TLC)
FLASH_TYPES = {
    "SLC": (4.4, 3),
    "MLC": (4, 1.5),
    "TLC": (1, 1),
    "QLC": (.32, .75),
    "PLC": (.16, .6),
}

WRITE_RATES = range(1, 100, 1) # in mb/s
CAPACITY = 2 # 2 tb
WRITE_RATES_DWPD = [(wr * 86400) / (CAPACITY * 1024 * 1024) for wr in WRITE_RATES]

DEVICE_WRITES = 3 * 3 * CAPACITY # per day times rated lifetime

FIGSIZE = (4.5,3.5)

# FIGSIZE = (10, 4) # for legend

# TBPD = DEVICE_WRITES / LIFETIME #tb per day

def get_cost(capacity_tb, multiple=1):
    # lower overprovisioned micron 7300 NVMe U.2
    # r^2 = .9997
    return 163.99 * capacity_tb * multiple + 122.78

def get_wr_cost(wr_mbs, flash_type, lifetime, limit_flash=True):
    wr_tbpd = wr_mbs * (60 * 60 * 24) / (1024 * 1024)
    tbpd = DEVICE_WRITES / lifetime
    min_flash = wr_tbpd / (tbpd * flash_type[0]) * CAPACITY
    if limit_flash:
        min_flash = max(min_flash, CAPACITY)
    return get_cost(min_flash, flash_type[1]), min_flash

def get_carbon(ssd_cap_gb, discount): # per year
    ssd = ssd_cap_gb * discount
    e_total = get_embodied_carbon(0, ssd)[0]
    o_total = get_operational_carbon(0, ssd)["wind-solar"][0] # per year
    return e_total + o_total

COLORS = ["r", "b", "g", "c", "m", "y", "k", "tab:orange", "tab:blue"]
def get_color(offset):
    return COLORS[offset]

def get_linestyle(label):
    if 'TLC' in label:
        return 'dotted'
    elif 'QLC' in label:
        return 'dashed'
    elif 'PLC' in label:
        return 'dashdot'
    else:
        return (0, (1, 10))

def graph_wr_vs_costs(savename, lines, sublines):
    matplotlib.rcParams.update({'font.size': 16})
    fig, ax = plt.subplots(figsize=FIGSIZE)

    for i, (label, points) in enumerate(lines.items()):
        plt.plot(
            list(WRITE_RATES_DWPD),
            [p/CAPACITY for p in points],
            # label=f'{label} years',
            color=get_color(i),
        )
        # for j, subpoints in enumerate(sublines[label]):
        #     ftype = list(FLASH_TYPES.keys())[j]
        #     plt.plot(
        #         list(WRITE_RATES),
        #         subpoints,
        #         # label=f"{label} - {ftype}",
        #         color=get_color(i),
        #         linestyle=get_linestyle(ftype),
        #         alpha=.5,
        #     )   


    plt.xlabel('Write Rate (DWPD)')
    plt.ylabel('Cost ($/TB-year)')
    plt.xlim(0)
    plt.ylim(0, 100)
    # plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.5),
    #       fancybox=True, shadow=True, ncol=5)
    plt.grid()
    plt.tight_layout()
    plt.savefig(savename)
    print(f"Saved figure to {savename}")

def graph_wr_vs_emissions(savename, lines, sublines):
    

    plt.close()
    plt.figure()
    matplotlib.rcParams.update({'font.size': 16})

    fig, ax = plt.subplots(figsize=FIGSIZE)

    for i, (label, points) in enumerate(lines.items()):
        plt.plot(
            list(WRITE_RATES_DWPD),
            [p/CAPACITY for p in points],
            label=f'{label} years',
            color=get_color(i),
        )
        # for j, subpoints in enumerate(sublines[label]):
        #     ftype = list(FLASH_TYPES.keys())[j]
        #     plt.plot(
        #         list(WRITE_RATES_DWPD),
        #         subpoints,
        #         # label=f"{label} - {ftype}",
        #         color=get_color(i),
        #         linestyle=get_linestyle(ftype),
        #         alpha=.5,
        #     )   



    plt.xlabel('Write Rate (DWPD)')
    plt.ylabel('Carbon Emissions \n($CO_{2}$ kg/TB-year)')
    plt.xlim(0)#, WRITE_RATES[-1] + 20)
    plt.ylim(0, 12)
    # plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.savefig(savename)
    print(f"Saved figure to {savename}")

def main(savename, limit_flash):
    lifetimes = [3,5,7,10]
    emission_lines = {}
    emissions_sublines = {}
    cost_lines = {}
    cost_sublines = {}
    for lifetime in lifetimes:
        cost_possibilities = []
        carbon_possibilites = []
        for label, flash_type in FLASH_TYPES.items():
            costs = []
            emissions = []
            for wr in WRITE_RATES:
                cost, cap = get_wr_cost(wr, flash_type, lifetime, limit_flash)
                costs.append(cost / lifetime)
                emissions.append(get_carbon(cap * 1024, flash_type[1]) / lifetime)
            cost_possibilities.append(costs)
            carbon_possibilites.append(emissions)
        min_costs = [min([el[i] for el in cost_possibilities]) for i in range(len(WRITE_RATES))]
        min_emissions = [min([el[i] for el in carbon_possibilites]) for i in range(len(WRITE_RATES))]
        argmin = [numpy.argmin([el[i] for el in cost_possibilities]) for i in range(len(WRITE_RATES))]
        seen = set()
        writes = list(WRITE_RATES)
        for i, val in enumerate(argmin[::-1]):
            if val not in seen:
                print(f"Lifetime {lifetime}:", val, WRITE_RATES_DWPD[len(writes) - i - 1])
                seen.add(val)

        cost_lines[lifetime] = min_costs
        cost_sublines[lifetime] = cost_possibilities
        emission_lines[lifetime] = min_emissions
        emissions_sublines[lifetime] = carbon_possibilites
    graph_wr_vs_costs(f"{savename}-costs.pdf", cost_lines, cost_sublines)
    graph_wr_vs_emissions(f"{savename}-emissions.pdf", emission_lines, emissions_sublines)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('savename')
    parser.add_argument('--limit_flash', '-l', action='store_true') # limit curves by capacity
    args = parser.parse_args()
    main(args.savename, args.limit_flash)
