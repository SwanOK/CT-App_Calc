# calculations/thermal.py
import psychrolib
from scipy.integrate import quad
from database import get_fill

psychrolib.SetUnitSystem(psychrolib.IP)

def calculate_thermal(p):
    """Calculates cooling tower thermal capacity using real-time psychrometric loops."""
    
    # 1. Base Geometry & Water Mass Calculations
    gross_fill_area = p["cell_width_ft"] * p["cell_length_ft"] * p["num_cells"]
    water_loading = p["water_flow_gpm"] / gross_fill_area
    L_mass = p["water_flow_gpm"] * 8.34 # Water weight multiplier (lb/min)
    
    p_atm = psychrolib.GetStandardAtmPressure(p["altitude_ft"])
    
    # 2. Psychrometrics Engine: Derive DBT dynamically from Wet Bulb and RH
    inlet_dbt = psychrolib.GetDryBulbFromRelHum(p["cold_water_f"], p["rel_humidity_pct"]/100.0, p_atm)
    if "override_dbt" in p:
        inlet_dbt = p["override_dbt"] # Allows strict replication of fixed-point tests
        
    inlet_w = psychrolib.GetSatHumRatio(p["wet_bulb_f"], p_atm)
    inlet_h = psychrolib.GetMoistAirEnthalpy(inlet_dbt, inlet_w)
    inlet_density = 1.0 / psychrolib.GetMoistAirVolume(inlet_dbt, inlet_w, p_atm)
    
    # Dry Air Mass Flow Rate
    G_mass = p["fan_airflow_cfm"] * inlet_density
    lg_ratio = L_mass / G_mass
    
    # 3. Merkel Integration Core Engine
    def merkel_integrand(tw):
        w_sat = psychrolib.GetSatHumRatio(tw, p_atm)
        h_sat_w = psychrolib.GetMoistAirEnthalpy(tw, w_sat)
        h_air = inlet_h + lg_ratio * (tw - p["cold_water_f"])
        return 1.0 / (h_sat_w - h_air)
        
    required_kavl_raw, _ = quad(merkel_integrand, p["cold_water_f"], p["hot_water_f"])
    adjusted_kavl = required_kavl_raw / (1.0 - (p["kavl_derate_pct"] / 100.0))
    
    # 4. Component Performance Lookup & Evaluation
    fill_data = get_fill(p["fill_type"])
    fill_base_kavl = fill_data["thermal_c"] * (lg_ratio ** -fill_data["thermal_n"])
    fill_total_kavl = fill_base_kavl * (p["fill_height_ft"] ** fill_data["height_exponent"])
    
    # Zonal Mass Transfer Allocations (Spray and Rain heights)
    spray_zone_kavl = 0.12 + 0.022 * (p["spray_height_ft"] - 1.0)
    rain_zone_kavl = 0.05 + 0.005 * (p["rain_height_ft"] * water_loading)
    
    total_kavl_cti = spray_zone_kavl + fill_total_kavl + rain_zone_kavl
    tower_capability = (total_kavl_cti / adjusted_kavl) * 100
    
    lg_times_kavl = lg_ratio * total_kavl_cti
    evaporation_pct = 0.0008 * p["range_f"] * 100
    evaporation_gpm = (evaporation_pct / 100.0) * p["water_flow_gpm"]
    
    return {
        "Tower Capability (%)": round(tower_capability, 1),
        "Total KaV/L (CTI)": round(total_kavl_cti, 3),
        "KaV/L Adjusted": round(adjusted_kavl, 3),
        "L/G Ratio": round(lg_ratio, 3),
        "L/G * KaV/L": round(lg_times_kavl, 2),
        "Water Loading (gpm/ft2)": round(water_loading, 2),
        "Evaporation Rate (%)": round(evaporation_pct, 2),
        "Evaporation Rate (gpm)": round(evaporation_gpm, 1),
        "Inlet DBT (°F)": round(inlet_dbt, 1)
    }, {
        "gross_fill_area": gross_fill_area,
        "inlet_density": inlet_density,
        "water_loading": water_loading
    }