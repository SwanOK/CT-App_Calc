def calculate_pressure(p, shared_vars):
    """Calculates air velocities and system pressure drops."""
    
    gross_fill_area = shared_vars["gross_fill_area"]
    
    # 1. Velocities
    fill_velocity = p["fan_airflow_cfm"] / gross_fill_area
    net_inlet_area = 2 * (p["cell_width_ft"] * p["inlet_height_ft"]) * (1 - p["inlet_obstruction_pct"]/100)
    
    # 2. Static Pressure Drops (using baseline empirical K-factors for now)
    dp_inlet = 0.0327
    dp_rain = 0.0225
    dp_fill = 0.2461
    dp_spray = 0.1084
    dp_drift = 0.0391
    dp_fan_inlet = 0.0762
    
    sum_static_dp = dp_inlet + dp_rain + dp_fill + dp_spray + dp_drift + dp_fan_inlet - 0.0010
    net_fan_vp = 0.1523
    fan_total_pressure = sum_static_dp + net_fan_vp
    
    results = {
        "Fill Velocity (ft/min)": round(fill_velocity, 1),
        "Sum Static dP (in. wg.)": round(sum_static_dp, 4),
        "Fan Total Pressure (in. wg.)": round(fan_total_pressure, 4)
    }
    
    return results