# calculations/pressure.py
import math
from database import get_fill, get_drift

def calculate_pressure(p, shared_vars):
    """Calculates all tower component pressure drops alongside Step 4 fan characteristics."""
    
    gross_fill_area = shared_vars["gross_fill_area"]
    rho = shared_vars["inlet_density"]
    loading = shared_vars["water_loading"]
    
    fill_velocity = p["fan_airflow_cfm"] / gross_fill_area
    
    # 1. Structural Air Inlet Pressure Drop
    net_inlet_area = 2 * (p["cell_width_ft"] * p["inlet_height_ft"]) * (1.0 - p["inlet_obstruction_pct"]/100.0)
    inlet_velocity = p["fan_airflow_cfm"] / net_inlet_area
    dp_inlet = 0.00000015 * (inlet_velocity ** 2) * rho
    
    # 2. Dynamic Rain and Spray Resistances
    dp_rain = 0.00000008 * (fill_velocity ** 1.9) * (p["rain_height_ft"] / 3.5) * (loading / 7.0)
    dp_spray = 0.000012 * (fill_velocity ** 1.5) * p["spray_height_ft"]
    
    # 3. Dynamic Fill Media Resistance Calculation
    fill_data = get_fill(p["fill_type"])
    dp_fill = fill_data["calc_dp"](fill_velocity, loading, p["fill_height_ft"])
    
    # 4. Drift Eliminator Pressure Drop Lookups
    drift_data = get_drift(p["drift_type"])
    dp_drift = drift_data["calc_dp"](fill_velocity, rho)
    
    # 5. STEP 4: PLENUM & MOTOR SYSTEMS
    # Annular Area of the Fan: Area = pi * (R_outer^2 - R_inner^2)
    r_outer = p["fan_diameter_ft"] / 2.0
    r_inner = p["seal_disk_diameter_ft"] / 2.0
    fan_net_area = math.pi * (r_outer**2 - r_inner**2)
    fan_velocity = p["fan_airflow_cfm"] / fan_net_area
    
    # Velocity Pressure (VP) equation: VP = (V / 4005)^2 * (rho / 0.075)
    fan_vp = ((fan_velocity / 4005.0) ** 2) * (rho / 0.075)
    
    # Fan structure mechanical inlet losses
    dp_fan_inlet = p["fan_inlet_loss_coeff"] * fan_vp
    
    # Accumulate all Component Static Resistances
    sum_static_dp = dp_inlet + dp_rain + dp_fill + dp_spray + dp_drift + dp_fan_inlet
    
    # Apply structural degradation safety factor
    sum_static_dp *= (1.0 + (p["dp_derate_pct"] / 100.0))
    
    # Stack Regain Option: Converts exit speed back to static lift if enabled
    if p.get("fan_stack_regain", False):
        regain_factor = 0.35 # Standard industrial stack recovery factor
        sum_static_dp -= (fan_vp * regain_factor)
        
    fan_total_pressure = sum_static_dp + fan_vp
    
    # Motor Power Calculations: Brake Horsepower (BHP)
    air_hp = (p["fan_airflow_cfm"] * fan_total_pressure) / 6356.0
    transmission_factor = p["transmission_eff_pct"] / 100.0
    fan_factor = p["total_fan_eff_pct"] / 100.0
    brake_horsepower = air_hp / (fan_factor * transmission_factor)
    
    return {
        "Fill Velocity (ft/min)": round(fill_velocity, 1),
        "Fan Net Velocity (ft/min)": round(fan_velocity, 1),
        "Sum Static dP (in. wg.)": round(sum_static_dp, 4),
        "Velocity Pressure (in. wg.)": round(fan_vp, 4),
        "Fan Total Pressure (in. wg.)": round(fan_total_pressure, 4),
        "Calculated Fan Power (HP)": round(brake_horsepower, 2)
    }