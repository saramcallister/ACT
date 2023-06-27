import math

energy_type_carbon = {
    "coal": 820,
    "gas": 490,
    "biomass": 230,
    "solar": 41,
    "geothermal": 38,
    "hydropower": 24,
    "nuclear": 12,
    "wind": 11,
    "wind-solar": 26,
} # in g/kWh

location_carbon = {
    "World": 301,
    "India": 725,
    "Australia": 597,
    "Taiwan": 583,
    "Singapore": 495,
    "US": 380,
    "Europe": 295,
    "Brazil": 82,
    "Iceland": 28, 
} # in g/kWh

flash_power = 18 # 18 in use, 6 w idle, data sheet of DC SN840
flash_max_cap = 768 # gb
cpu_power = 125
dram_power = 3 # per 8 gb #5.6  per 64 gb ddr5
dram_power_cap_gb = 8
nic = 20
usage_discount = .7

def get_kwh_per_year(powers):
    # take watts and return kwh per year
    return [p / 1000 * 8760 for p in powers]

def get_carbon_emissions(carbon_intensity, kwh):
    # carbon_insity in g, ret in kg
    return [usage_discount * carbon_intensity * p / 1000 for p in kwh]

def get_operational_carbon(dram_cap_gb, flash_cap_gb):
    kwh = get_kwh_per_year([flash_power * math.ceil(flash_cap_gb / flash_max_cap), cpu_power, dram_power * dram_cap_gb / dram_power_cap_gb])
    energy_types = {k: get_carbon_emissions(v, kwh) for k, v in energy_type_carbon.items()}
    locations = {k: get_carbon_emissions(v, kwh) for k, v in location_carbon.items()}
    # print(energy_types["wind-solar"])
    # print(f"\tOperational power (flash, cpu, dram): {energy_types} {locations}")
    ret = {**locations, **energy_types}
    return ret
    # return {k: sum(v) for (k, v) in ret.items()}
