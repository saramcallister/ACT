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

DEVICE_WRITES = 3 * 3 * CAPACITY # per day times rated lifetime

FIGSIZE = (8, 3)

# TBPD = DEVICE_WRITES / LIFETIME #tb per day

def get_cost(capacity_tb, multiple=1):
    # lower overprovisioned micron 7300 NVMe U.2
    # r^2 = .9997
    return 163.99 * capacity_tb * multiple + 122.78

def get_wr_cost(wr_mbs, flash_type, lifetime):
    wr_tbpd = wr_mbs * (60 * 60 * 24) / (1024 * 1024)
    tbpd = DEVICE_WRITES / lifetime
    min_flash = max(wr_tbpd / (tbpd * flash_type[0]) * CAPACITY, CAPACITY)
    return get_cost(min_flash) * flash_type[1], min_flash

def get_carbon(ssd_cap_gb, discount): # per year
    ssd = ssd_cap_gb * discount
    e_total = sum(get_embodied_carbon(0, ssd))
    o_total = sum(get_operational_carbon(0, ssd)["wind-solar"]) # per year
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

def graph_wr_vs_costs(savename, lines):
    matplotlib.rcParams.update({'font.size': 16})
    fig, ax = plt.subplots(figsize=FIGSIZE)

    for i, (label, points) in enumerate(lines.items()):
        plt.plot(
            list(WRITE_RATES),
            points,
            label=f'{label} years',
            color=get_color(i),
        )


    plt.xlabel('Write Rate (MB/s)')
    plt.ylabel('Cost ($/year)')
    plt.xlim(0)
    plt.ylim(0)
    plt.legend()
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
            list(WRITE_RATES),
            points,
            label=f'{label} years',
            color=get_color(i),
        )
        # for j, subpoints in enumerate(sublines[label]):
        #     ftype = list(FLASH_TYPES.keys())[j]
        #     plt.plot(
        #         list(WRITE_RATES),
        #         subpoints,
        #         label=f"{label} - {ftype}",
        #         color=get_color(i),
        #         linestyle=get_linestyle(ftype),
        #         alpha=.5,
        #     )   



    plt.xlabel('Write Rate (MB/s)')
    plt.ylabel('Carbon Emissions \n($CO_{2}$ kg/year)')
    plt.xlim(0)#, WRITE_RATES[-1] + 20)
    plt.ylim(0, 35)
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.savefig(savename)
    print(f"Saved figure to {savename}")

def main(savename):
    lifetimes = [3,5,7,10]
    emission_lines = {}
    emissions_sublines = {}
    cost_lines = {}
    for lifetime in lifetimes:
        cost_possibilities = []
        carbon_possibilites = []
        for label, flash_type in FLASH_TYPES.items():
            costs = []
            emissions = []
            for wr in WRITE_RATES:
                cost, cap = get_wr_cost(wr, flash_type, lifetime)
                costs.append(cost / lifetime)
                emissions.append(get_carbon(cap * 1024, flash_type[1]) / lifetime)
            cost_possibilities.append(costs)
            carbon_possibilites.append(emissions)
        min_costs = [min([el[i] for el in cost_possibilities]) for i in range(len(WRITE_RATES))]
        min_emissions = [min([el[i] for el in carbon_possibilites]) for i in range(len(WRITE_RATES))]
        argmin = [numpy.argmin([el[i] for el in carbon_possibilites]) for i in range(len(WRITE_RATES))]
        seen = set()
        writes = list(WRITE_RATES)
        for i, val in enumerate(argmin[::-1]):
            if val not in seen:
                print(f"Lifetime {lifetime}:", val, writes[len(writes) - i - 1])
                seen.add(val)

        cost_lines[lifetime] = min_costs
        emission_lines[lifetime] = min_emissions
        emissions_sublines[lifetime] = carbon_possibilites
    graph_wr_vs_costs(f"{savename}-costs.pdf", cost_lines)
    graph_wr_vs_emissions(f"{savename}-emissions.pdf", emission_lines, emissions_sublines)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('savename')
    args = parser.parse_args()
    main(args.savename)
