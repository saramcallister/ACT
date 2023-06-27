#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
from pathlib import Path
import statistics
import math

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from dellrexp import get_embodied_carbon
from operational import get_operational_carbon

matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

DEFAULT_LIFETIME = 3 # years
DWPD = 3
DEVICE_WRITES = 3  * DEFAULT_LIFETIME # device writes per day
SCALING = 5
FIGSIZE = (4, 4)
DENSITY_FIGSIZE = (7.5, 3)
# FLASH_LIMIT = 16

TLC = (1, 1)
QLC = (.32, .75) # writes, cost/sustainibility
PLC = (.16, .6) # writes, cost/sustainibility

RESULTS = {
    "FairyWREN": [400, 7.8, 1.90], 
    "Kangaroo": [400, 97.4, 1.44], 
    "Minimum": [400, 4.12, 0]
} # flash cap, mb/s, dram cap
LIFETIMES = [1,2,3,4,5,6,7,8,9,10] # years

def get_flash_cap(min_cap_gb, wr_mbs, lifetime, density_mod):
    lifetime_s = lifetime * 24 * 60 * 60
    dwps = density_mod * DEVICE_WRITES / lifetime_s
    device_size_mb = wr_mbs / dwps
    return max(device_size_mb / 1024, min_cap_gb)

def get_configurations(lifetimes, results, scaling, density):
    all_configs = {}
    for label, params in results.items():
        configs = []
        for life in lifetimes:
            total_flash = get_flash_cap(scaling * params[0], params[1], life, density[0])
            # if total_flash > params[0] * scaling * FLASH_LIMIT:
            #     continue
            total_dram = scaling * params[2]
            configs.append((life, total_dram, total_flash))
        # print(label, configs)
        all_configs[label] = configs
    return all_configs
            
def get_carbon(configs, density): # per year
    # configs format: {label: [(lifetime, total_dram, total_flash)]}
    outputs = {}
    for label, config_list in configs.items():
        carbon = []
        for life, dram, ssd in config_list:

            ssd = ssd * density[1]

            dram_with_ecc = dram + dram/8
            e_ssd, e_dram, e_other = get_embodied_carbon(dram_with_ecc, ssd)
            e = (e_ssd / life, e_dram / life, e_other / life)
            e_total = sum(e)

            o_ssd, o_other, o_dram = get_operational_carbon(dram, ssd)["wind-solar"] # per year
            o = (o_ssd, o_dram, o_other)
            o_total = sum(o)

            carbon.append((dram, ssd, life, e, o))
            # print(label, life, ssd, dram, e, o, sum(e) + sum(o))
        outputs[label] = carbon
    return outputs 

MAX_FLASH_CAP = 768
def get_flash_cost(flash_cap_gb):
    flash_devices = math.ceil(flash_cap_gb / MAX_FLASH_CAP)
    capacity_tb = flash_cap_gb / 1024
    return 163.99 * capacity_tb + 122.78

def get_dram_cost(dram_cap_gb):
    return 5.53 * dram_cap_gb

def get_cost(configs, density): # per year
    outputs = {}
    for label, config_list in configs.items():
        cost = []
        for life, dram, ssd in config_list:
            ssd = ssd * density[1] 
            
            dram_cost = get_dram_cost(dram) / life
            ssd_cost = get_flash_cost(ssd) / life
            # print(label, life, ssd, dram, ssd_cost, dram_cost, ssd_cost + dram_cost)
            cost.append((dram, ssd, life, (ssd_cost, dram_cost)))
        outputs[label] = cost
    return outputs
    

colors = {
    'Kangaroo': '#00AB8E',
    'FairyWREN': '#DAA520',
    'SA': '#FF95CA',
    'LS': '#FF42A1',
    'Minimum': '#D3D3D3',
}

def get_label_color(label):
    return colors[label]

def plot_carbon_lifetimes(carbons, savename, legend=False):
    matplotlib.rcParams.update({'font.size': 16})

    fig, ax = plt.subplots(figsize=FIGSIZE)
    # print(miss_ratio_dict.keys())

    for label, points in list(carbons.items())[::-1]:
        dram, ssd, life, e, o = zip(*points)
        total_carbon = [sum(e[i]) + sum(op) for (i, op) in enumerate(o)] 
        embodied_carbon = [sum(emb) for emb in e]

        ind = total_carbon.index(min(total_carbon))
        best_e = e[ind]
        best_o = o[ind]
        print(f"{label} Min ({life[ind]}): {total_carbon[ind]} {e[ind]} {o[ind]} {best_e[0] + best_o[0]} {best_e[1] + best_o[1]}")

        color = get_label_color(label)
        ax.plot(life, total_carbon, label=label, color=color, linewidth=2, marker="x")
        # ax.plot(life, embodied_carbon, label=f"{label}: Embodied", color=color, linewidth=2, marker="o")


    plt.ylabel('Carbon Emissions\n($CO_{2}$ kg/year)')
    plt.xlabel('Lifetime (years)')
    if legend:
        plt.legend()
    plt.ylim(0, 100)
    plt.xlim(0,11)
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(savename)
    print(f'Saved to {savename}')

def plot_cost_lifetimes(cost, savename, legend=False):
    matplotlib.rcParams.update({'font.size': 16})

    fig, ax = plt.subplots(figsize=FIGSIZE)
    # print(miss_ratio_dict.keys())

    for label, points in list(cost.items())[::-1]:
        dram, ssd, life, c = zip(*points)
        total_cost = [sum(i) for i in c] 

        ind = total_cost.index(min(total_cost))
        print(f"{label} Min ({life[ind]}): {total_cost[ind]} {c[ind]} {dram[ind]} {ssd[ind]}")

        color = get_label_color(label)
        ax.plot(life, total_cost, label=label, color=color, linewidth=2, marker="x")
        # ax.plot(life, embodied_carbon, label=f"{label}: Embodied", color=color, linewidth=2, marker="o")


    plt.ylabel('Cost ($/year)')
    plt.xlabel('Lifetime (years)')
    if legend:
        plt.legend()
    plt.ylim(0,400)
    plt.xlim(0,11)
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(savename)
    print(f'Saved to {savename}')

def plot_carbons_density(carbons, savename):
    matplotlib.rcParams.update({'font.size': 16})

    fig, ax = plt.subplots(figsize=DENSITY_FIGSIZE)
    width = 1/(len(carbons.keys()) + 1)

    for i, label in enumerate(["Kangaroo", "FairyWREN", "Minimum"]):
        emits = carbons[label]
        X = np.arange(len(emits))
        color = get_label_color(label)
        plt.bar(X + i * width, emits, width, label=label, color=color, zorder=10)

    plt.xticks(X + width * (len(carbons.keys()) - 1)/2, ["TLC", "QLC", "PLC"])
    plt.ylabel('Carbon Emissions\n($CO_{2}$ kg/year)')
    plt.xlabel('Flash Density')
    # plt.legend()
    plt.ylim(0, 100)
    # plt.yscale('log')
    plt.grid(True, zorder=0)
    plt.tight_layout()

    plt.savefig(savename)
    print(f'Saved to {savename}')

def plot_costs_density(costs, savename):
    matplotlib.rcParams.update({'font.size': 16})

    fig, ax = plt.subplots(figsize=DENSITY_FIGSIZE)
    width = 1/(len(costs.keys()) + 1)

    for i, label in enumerate(["Kangaroo", "FairyWREN", "Minimum"]):
        c = costs[label]
        X = np.arange(len(c))
        color = get_label_color(label)
        plt.bar(X + i * width, c, width, label=label, color=color, zorder=10)

    plt.xticks(X + width * (len(costs.keys()) - 1)/2, ["TLC", "QLC", "PLC"])
    plt.ylabel('Cost ($/year)')
    plt.xlabel('Flash Density')
    plt.legend()
    plt.ylim(0, 400)
    # plt.yscale('log')
    plt.grid(True, zorder=0)
    plt.tight_layout()

    plt.savefig(savename)
    print(f'Saved to {savename}')

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument('savename')
    # parser.add_argument('filenames', nargs='+')
    # args = parser.parse_args()

    # main(
    #     args.filenames,
    #     args.savename,
    # )
    print("TLC")
    configs_tlc = get_configurations(LIFETIMES, RESULTS, SCALING, TLC)
    print(configs_tlc)
    carbon_tlc = get_carbon(configs_tlc, TLC)
    cost_tlc = get_cost(configs_tlc, TLC)
    plot_carbon_lifetimes(carbon_tlc, "exp-carbon-tlc-lifetimes.png", True)
    plot_cost_lifetimes(cost_tlc, "exp-cost-tlc-lifetimes.png", True)

    print("QLC")
    configs_qlc = get_configurations(LIFETIMES, RESULTS, SCALING, QLC)
    carbon_qlc = get_carbon(configs_qlc, QLC)
    cost_qlc = get_cost(configs_qlc, QLC)
    plot_carbon_lifetimes(carbon_qlc, "exp-carbon-qlc-lifetimes.png")
    plot_cost_lifetimes(cost_qlc, "exp-cost-qlc-lifetimes.png")

    print("PLC")
    configs_plc = get_configurations(LIFETIMES, RESULTS, SCALING, PLC)
    carbon_plc = get_carbon(configs_plc, PLC)
    cost_plc = get_cost(configs_plc, PLC)
    plot_carbon_lifetimes(carbon_plc, "exp-carbon-plc-lifetimes.png")
    plot_cost_lifetimes(cost_plc, "exp-cost-plc-lifetimes.png", True)

    # order: TLC, QLC, PLC
    carbons_density = {
        "Minimum": [35.080898285714284, 31.599693714285713, 31.53664014285714], 
        "Kangaroo": [56.35939934642857, 84.71861445357143, 109.03043129285714], 
        "FairyWREN": [35.77413483035714, 33.80703069866071, 37.737253127232144]
    }
    costs_density = {
        "Minimum": [44.307296875, 36.29997265625, 35.4742173461914], 
        "Kangaroo": [162.49335854492185, 358.9949715896607, 564.636194543457], 
        "FairyWREN": [49.560796875, 44.978480476379396, 61.44666876220703]
    }

    plot_carbons_density(carbons_density, "exp-carbon-density.png")
    plot_costs_density(costs_density, "exp-costs-density.png")