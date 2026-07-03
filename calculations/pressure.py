# calculations/pressure.py
import math
import psychrolib
from database import get_fill, get_drift

def solve_airflow(p):
    """Iteratively solves for true operating CFM based on Rated Motor HP."""
    psychrolib.SetUnitSystem(psychrolib.IP)
    
    gross_area = p["cell_width_ft"] * p["cell_length_ft"] * p["num_cells"]
    obstruction_factor = 1.0 - (p["fill_obstruction_pct"] / 100.0)
    net_area = gross_area * obstruction_factor
    loading = p["water_flow_gpm"] / net_area
    
    p_atm = psychrolib.GetStandardAtmPressure(p["altitude_ft"])
    inlet_dbt = p.get("override_dbt", p["wet_bulb_f"] + 5.0)
    inlet_w = psychrolib.GetSatHumRatio(p["wet_bulb_f"], p_atm)
    rho = 1.0 / psychrolib.GetMoistAirVolume(inlet_dbt, inlet_w, p_atm)
    
    def simulate(cfm):
        v = cfm / net_area
        
        net_inlet = 2 * (p["cell_width_ft"] * p["inlet_height_ft"] * p["num_cells"]) * (1.0 - p["inlet_obstruction_pct"]/100.0)
        v_inlet = cfm / net_inlet
        
        r_outer = p["fan_diameter_ft"] / 2.0
        r_inner = p["seal_disk_diameter_ft"] / 2.0
        fan_area = math.pi * (r_outer**2 - r_inner**2) * p["num_cells"]
        fan_v = cfm / fan_area
        vp = ((fan_v / 4005.0)**2) * (rho / 0.075)
        
        # Stable Structural Polynomial Resistance
        dp_inlet = 0.057 * (v_inlet/1000)**2
        dp_rain = 0.018 * (v/1000)**2 * p["rain_height_ft"]
        dp_spray = 0.24 * (v/1000)**2 * p["spray_height_ft"]
        dp_drift = 0.109 * (v/1000)**2
        dp_fill = get_fill(p["fill_type"])["calc_dp"](v, loading, p["fill_height_ft"])
        dp_fan_inlet = p["fan_inlet_loss_coeff"] * vp
        
        sum_static = (dp_inlet + dp_rain + dp_spray + dp_fill + dp_drift + dp_fan_inlet)
        sum_static *= (1.0 + (p["dp_derate_pct"]/100.0))
        
        if p.get("fan_stack_regain", False):
            sum_static -= (vp * 0.35)
            
        total_p = sum_static + vp
        
        fan_eff = p["total_fan_eff_pct"] / 100.0
        trans_eff = p["transmission_eff_pct"] / 100.0
        hp = (cfm * total_p) / (6356.0 * fan_eff * trans_eff)
        
        results = {
            "Fill Velocity (ft/min)": round(v, 1),
            "Fan Net Velocity (ft/min)": round(fan_v, 1),
            "Sum Static dP (in. wg.)": round(sum_static, 4),
            "Velocity Pressure (in. wg.)": round(vp, 4),
            "Fan Total Pressure (in. wg.)": round(total_p, 4),
            "Calculated Fan Power (HP)": round(hp, 1)
        }
        return hp, cfm, results

    low_cfm, high_cfm = 1000.0, 2000000.0
    target_hp = p["motor_rated_hp"] * p["num_cells"]
    
    for _ in range(100):
        mid_cfm = (low_cfm + high_cfm) / 2.0
        hp_mid, _, _ = simulate(mid_cfm)
        
        if abs(hp_mid - target_hp) < 0.001:
            break
        if hp_mid > target_hp:
            high_cfm = mid_cfm
        else:
            low_cfm = mid_cfm
            
    final_hp, final_cfm, final_results = simulate(low_cfm)
    return final_cfm, final_results