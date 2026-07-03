import psychrolib
from scipy.integrate import quad

# Set Imperial units for PsychroLib globally for this module
psychrolib.SetUnitSystem(psychrolib.IP)

def calculate_thermal(p):
    """Calculates thermal capability and required KaV/L."""
    
    # 1. Geometry & Water Loading
    gross_fill_area = p["cell_width_ft"] * p["cell_length_ft"] * p["num_cells"]
    water_loading = p["water_flow_gpm"] / gross_fill_area
    L_mass = p["water_flow_gpm"] * 8.34 # Water mass flow (lb/min)
    
    # 2. Psychrometrics
    p_atm = psychrolib.GetStandardAtmPressure(p["altitude_ft"])
    # FIXED: GetSatHumRatio instead of GetSatAirHumRatio
    inlet_w = psychrolib.GetSatHumRatio(p["wet_bulb_f"], p_atm) 
    inlet_dbt = 93.0 # Standard design DBT for this specific rating
    inlet_h = psychrolib.GetMoistAirEnthalpy(inlet_dbt, inlet_w)
    inlet_density = 1.0 / psychrolib.GetMoistAirVolume(inlet_dbt, inlet_w, p_atm)
    
    G_mass = p["fan_airflow_cfm"] * inlet_density # Dry air mass flow (lb/min)
    lg_ratio = L_mass / G_mass
    
    # 3. Merkel Integration
    def merkel_integrand(tw):
        # FIXED: GetSatHumRatio instead of GetSatAirHumRatio
        w_sat = psychrolib.GetSatHumRatio(tw, p_atm)
        h_sat_w = psychrolib.GetMoistAirEnthalpy(tw, w_sat)
        h_air = inlet_h + lg_ratio * (tw - p["cold_water_f"])
        return 1.0 / (h_sat_w - h_air)
    
    required_kavl_raw, _ = quad(merkel_integrand, p["cold_water_f"], p["hot_water_f"])
    
    # 4. Derates & Capability
    derate_factor = 1 - (p["kavl_derate_pct"] / 100.0)
    adjusted_kavl = required_kavl_raw / derate_factor
    
    total_kavl_cti = 0.148 + p["fill_characteristic_k"] + 0.067 # Spray + Fill + Rain
    tower_capability = (total_kavl_cti / adjusted_kavl) * 100
    
    results = {
        "Tower Capability (%)": round(tower_capability, 1),
        "Total KaV/L (CTI)": round(total_kavl_cti, 3),
        "KaV/L Adjusted": round(adjusted_kavl, 3),
        "L/G Ratio": round(lg_ratio, 3),
        "Water Loading (gpm/ft2)": round(water_loading, 2)
    }
    
    # Return results plus variables needed by the pressure module
    shared_vars = {
        "gross_fill_area": gross_fill_area
    }
    
    return results, shared_vars