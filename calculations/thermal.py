# calculations/thermal.py
import psychrolib
from database import get_fill

def calculate_thermal(p):
    psychrolib.SetUnitSystem(psychrolib.IP)
    
    obstruction = 1.0 - (p.get("fill_obstruction_pct", 5.0) / 100.0)
    net_area = (p["cell_width_ft"] * p["cell_length_ft"] * p["num_cells"]) * obstruction
    loading = p["water_flow_gpm"] / net_area
    L_mass = p["water_flow_gpm"] * 8.33 
    
    p_atm = psychrolib.GetStandardAtmPressure(p["altitude_ft"])
    inlet_dbt = p.get("override_dbt", p["wet_bulb_f"] + 5.0)
    inlet_w = psychrolib.GetHumRatioFromTWetBulb(inlet_dbt, p["wet_bulb_f"], p_atm)
    inlet_h = psychrolib.GetMoistAirEnthalpy(inlet_dbt, inlet_w)
    
    lg_density_factor = 0.0716 
    G_mass = p["fan_airflow_cfm"] * lg_density_factor
    lg_ratio = L_mass / G_mass
    
    multipliers = [0.1, 0.4, 0.6, 0.9]
    sum_val = 0.0
    for m in multipliers:
        t_w = p["cold_water_f"] + (m * p["range_f"])
        w_sat = psychrolib.GetSatHumRatio(t_w, p_atm)
        h_sat_w = psychrolib.GetMoistAirEnthalpy(t_w, w_sat)
        h_air = inlet_h + lg_ratio * (t_w - p["cold_water_f"])
        sum_val += 1.0 / (h_sat_w - h_air)
        
    req_kavl_raw = (p["range_f"] / 4.0) * sum_val
    
    derate = 1.0 - (p.get("kavl_derate_pct", 5.0)/100.0)
    if derate <= 0: derate = 1.0
    req_kavl_adj = req_kavl_raw / derate
    
    fill = get_fill(p["fill_type"])
    fill_kavl = fill["thermal_c"] * (lg_ratio ** -fill["thermal_n"]) * (p["fill_height_ft"] ** fill["height_exp"])
    
    spray_kavl = 0.1184 * p["spray_height_ft"]
    rain_kavl = 0.00267 * p["rain_height_ft"] * loading
    
    total_kavl = spray_kavl + fill_kavl + rain_kavl
    capability = (total_kavl / req_kavl_adj) * 100.0
    
    evap_pct = 0.0008 * p["range_f"] * 100.0
    evap_gpm = (evap_pct / 100.0) * p["water_flow_gpm"]
    
    return {
        "Tower Capability (%)": round(capability, 1),
        "Total KaV/L (CTI)": round(total_kavl, 3),
        "Required KaV/L (Adj)": round(req_kavl_adj, 3),
        "L/G Ratio": round(lg_ratio, 3),
        "Water Loading (gpm/ft2)": round(loading, 2),
        "Evaporation Rate (gpm)": round(evap_gpm, 1)
    }