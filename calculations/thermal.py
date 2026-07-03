# calculations/thermal.py
import psychrolib
from database import get_fill

def calculate_thermal(p):
    """Calculates thermal capability using iterative CTI ATC-105 standards."""
    psychrolib.SetUnitSystem(psychrolib.IP)
    
    # 1. Structural Geometry
    gross_area = p["cell_width_ft"] * p["cell_length_ft"] * p["num_cells"]
    obstruction_factor = 1.0 - (p["fill_obstruction_pct"] / 100.0)
    net_area = gross_area * obstruction_factor
    loading = p["water_flow_gpm"] / net_area
    
    # 2. Base Mass Properties
    L_mass = p["water_flow_gpm"] * 8.33 
    
    # CRITICAL FIX: The Legacy CTI Table Hardcode
    # S.T.A.R. uses actual altitude density for the fan aerodynamics, 
    # but evaluates the Merkel Enthalpy integral using Sea Level Standard Tables.
    p_atm_sea_level = 14.696 
    
    inlet_dbt = p.get("override_dbt", p["wet_bulb_f"] + 5.0)
    
    # Evaluate inlet air properties at standard sea-level pressure
    inlet_w = psychrolib.GetHumRatioFromTWetBulb(inlet_dbt, p["wet_bulb_f"], p_atm_sea_level)
    inlet_h = psychrolib.GetMoistAirEnthalpy(inlet_dbt, inlet_w)
    
    # Brentwood's standardized reference density for L/G 
    dry_air_mass_rate = p["fan_airflow_cfm"] * 0.0716 
    lg_ratio = L_mass / dry_air_mass_rate
    
    # 3. Design Point Requirements
    cw = p["cold_water_f"]
    hw = p["hot_water_f"]
    ran = p["range_f"]
    
    t_w = [cw + 0.10 * ran, cw + 0.40 * ran, cw + 0.60 * ran, cw + 0.90 * ran]
    
    sum_inverse_delta_h = 0.0
    for tw in t_w:
        # Evaluate saturation curve at standard sea-level pressure
        w_sat = psychrolib.GetSatHumRatio(tw, p_atm_sea_level)
        h_sat_w = psychrolib.GetMoistAirEnthalpy(tw, w_sat)
        h_air = inlet_h + lg_ratio * (tw - cw)
        sum_inverse_delta_h += (1.0 / (h_sat_w - h_air))
        
    req_kavl_raw = (ran / 4.0) * sum_inverse_delta_h
    
    # 4. Total Available Performance & Derate
    fill = get_fill(p["fill_type"])
    fill_kavl = fill["thermal_c"] * (lg_ratio ** -fill["thermal_n"]) * (p["fill_height_ft"] ** fill["height_exp"])
    spray_kavl = 0.118 * p["spray_height_ft"]
    rain_kavl = 0.019 * p["rain_height_ft"]
    
    total_kavl = spray_kavl + fill_kavl + rain_kavl
    derate_factor = 1.0 - (p["kavl_derate_pct"] / 100.0)
    total_kavl_adj = total_kavl * derate_factor
    
    # 5. CTI Iterative Capability Solver
    def evaluate_capability(cap_pct):
        test_lg = lg_ratio * (cap_pct / 100.0)
        
        test_sum_inv = 0.0
        for tw in t_w:
            w_sat = psychrolib.GetSatHumRatio(tw, p_atm_sea_level)
            h_sat_w = psychrolib.GetMoistAirEnthalpy(tw, w_sat)
            h_air = inlet_h + test_lg * (tw - cw)
            
            # If air enthalpy exceeds water enthalpy, tower is choked
            if h_sat_w <= h_air: 
                return -99999.0 
                
            test_sum_inv += (1.0 / (h_sat_w - h_air))
            
        test_req = (ran / 4.0) * test_sum_inv
        test_fill = fill["thermal_c"] * (test_lg ** -fill["thermal_n"]) * (p["fill_height_ft"] ** fill["height_exp"])
        test_total_adj = (spray_kavl + test_fill + rain_kavl) * derate_factor
        
        return test_total_adj - test_req

    # Bisection search to find exact water capacity limit
    low_cap, high_cap = 10.0, 150.0
    for _ in range(50):
        mid_cap = (low_cap + high_cap) / 2.0
        diff = evaluate_capability(mid_cap)
        if diff > 0:
            low_cap = mid_cap
        else:
            high_cap = mid_cap
            
    capability = low_cap
    
    evap_pct = 0.0008 * p["range_f"] * 100.0
    evap_gpm = (evap_pct / 100.0) * p["water_flow_gpm"]
    
    return {
        "Tower Capability (%)": round(capability, 1),
        "Total KaV/L (CTI)": round(total_kavl, 3),
        "Total KaV/L (Adj)": round(total_kavl_adj, 3),
        "Required KaV/L": round(req_kavl_raw, 3),
        "L/G Ratio": round(lg_ratio, 3),
        "Evaporation Rate (gpm)": round(evap_gpm, 1)
    }