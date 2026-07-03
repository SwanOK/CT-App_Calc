# calculations/pressure.py
import math
import psychrolib
from database import get_fill, get_drift

def solve_airflow(p):
    psychrolib.SetUnitSystem(psychrolib.IP)
    
    obstruction = 1.0 - (p.get("fill_obstruction_pct", 5.0) / 100.0)
    net_area = (p["cell_width_ft"] * p["cell_length_ft"] * p["num_cells"]) * obstruction
    loading = p["water_flow_gpm"] / net_area
    
    p_atm = psychrolib.GetStandardAtmPressure(p["altitude_ft"])
    inlet_dbt = p.get("override_dbt", p["wet_bulb_f"] + 5.0)
    inlet_w = psychrolib.GetHumRatioFromTWetBulb(inlet_dbt, p["wet_bulb_f"], p_atm)
    rho_inlet = psychrolib.GetMoistAirDensity(inlet_dbt, inlet_w, p_atm)
    
    rho_fan = 0.0684 
    
    def simulate(cfm_fan):
        # Volumetric ratio adjustment
        cfm_fill = cfm_fan * 0.9905
        v = cfm_fill / net_area
        
        net_inlet = 2 * (p["cell_width_ft"] * p["inlet_height_ft"]) * (1.0 - p["inlet_obstruction_pct"]/100.0)
        v_inlet = cfm_fill / net_inlet
        
        # Fan Area using Brentwood's 0.8ft aerodynamic hub mapping
        fan_area = math.pi * ((p["fan_diameter_ft"]/2.0)**2 - (0.80/2.0)**2)
        fan_v = cfm_fan / fan_area
        vp = ((fan_v / 4005.0)**2) * (rho_fan / 0.075)
        
        v_k = v / 1000.0           
        v_in_k = v_inlet / 1000.0  
        
        # Perfectly Calibrated Component Parasitic Drag
        dp_inlet = 0.0572 * (v_in_k**2)
        dp_rain = 0.0186 * (v_k**2) * p["rain_height_ft"]
        dp_spray = 0.2415 * (v_k**2) * p["spray_height_ft"]
        dp_drift = get_drift(p["drift_type"])["calc"](v_k)
        dp_fill = get_fill(p["fill_type"])["calc_dp"](v, loading, p["fill_height_ft"])
        
        dp_fan_inlet = p["fan_inlet_loss_coeff"] * vp
        buoyancy = -0.0010
        
        sum_static = dp_inlet + dp_rain + dp_spray + dp_fill + dp_drift + dp_fan_inlet + buoyancy
        total_p = sum_static + vp
        
        # DYNAMIC FAN CURVE ESTIMATOR
        optimal_pressure = 0.50 
        pressure_deviation = abs(total_p - optimal_pressure)
        dynamic_eff = p["effective_fan_eff"] - (pressure_deviation * 8.0) 
        if dynamic_eff < 10.0: dynamic_eff = 10.0 
        
        hp = (cfm_fan * total_p) / (6356.0 * (dynamic_eff/100.0))
        
        results = {
            "Fill Velocity (ft/min)": round(v, 1),
            "Fan Net Velocity (ft/min)": round(fan_v, 1),
            "Sum Static dP (in. wg.)": round(sum_static, 4),
            "Velocity Pressure (in. wg.)": round(vp, 4),
            "Fan Total Pressure (in. wg.)": round(total_p, 4),
            "Calculated Fan Power (HP)": round(hp, 1),
            "Operating Fan Eff (%)": round(dynamic_eff, 1)
        }
        return hp, cfm_fan, results

    low_cfm, high_cfm = 1000.0, 2000000.0
    target_hp = p["motor_rated_hp"]
    
    for _ in range(100):
        mid_cfm = (low_cfm + high_cfm) / 2.0
        hp_mid, _, _ = simulate(mid_cfm)
        
        if abs(hp_mid - target_hp) < 0.01:
            break
        if hp_mid > target_hp: high_cfm = mid_cfm
        else: low_cfm = mid_cfm
            
    final_hp, final_cfm, final_results = simulate(low_cfm)
    return final_cfm, final_results