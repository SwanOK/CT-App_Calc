# core/aero_engine.py
from core.constants import AERO_DYNAMIC_K, FAN_CURVES

def calculate_net_area(width_ft, length_ft, obstruction_percent, cells):
    gross_area = (width_ft * length_ft) * cells
    return gross_area * (1.0 - (obstruction_percent / 100.0))

def run_aero_rating(geometry_data, fan_hp, water_loading, air_density_inlet, air_density_fan):
    cw = geometry_data['cell_width_ft']
    cl = geometry_data['cell_length_ft']
    cells = geometry_data['cells']
    h_fill = geometry_data['fill_height_ft']
    
    # Safely extract the exact fill type for the aerodynamics
    fill_type = geometry_data.get('fill_type', 'CF-1200')
    
    # 1. Component Areas
    fill_area = calculate_net_area(cw, cl, geometry_data['fill_obstruction_percent'], cells)
    total_length = cl * cells
    inlet_perimeter = (cw * 2) + (total_length * 2)
    inlet_area = inlet_perimeter * geometry_data['inlet_height_ft'] * (1.0 - (geometry_data['inlet_obstruction_percent'] / 100.0))
    
    # 2. Net Fan Area
    fan_diameter = geometry_data['fan_diameter_ft']
    hub_diameter = geometry_data.get('hub_diameter_ft', 1.26) 
    gross_fan_area = 3.14159 * ((fan_diameter / 2.0) ** 2)
    hub_area = 3.14159 * ((hub_diameter / 2.0) ** 2)
    single_fan_net_area = gross_fan_area - hub_area
    total_fan_area = single_fan_net_area * cells

    # 3. DYNAMIC K-Factors
    def calc_k(zone):
        return AERO_DYNAMIC_K[zone]['a'] * (water_loading ** AERO_DYNAMIC_K[zone]['b'])
        
    fill_key = f"{fill_type}_Per_Foot"
    k_fill_total = calc_k(fill_key) * h_fill
    k_spray = calc_k('Spray')
    k_rain = calc_k('Rain')
    
    louver_k = geometry_data.get('louver_coeff', 1.0)
    drift_k = 1.5 
    fan_inlet_k = geometry_data.get('fan_inlet_coeff', 0.50)

    def get_c(k_val, area, density):
        if area <= 0: return 0
        return (k_val * density) / ((area ** 2) * (1096.7 ** 2))
        
    C_static = (get_c(louver_k, inlet_area, air_density_inlet) + 
                get_c(k_rain, fill_area, air_density_fan) + 
                get_c(k_fill_total, fill_area, air_density_fan) + 
                get_c(k_spray, fill_area, air_density_fan) + 
                get_c(drift_k, fill_area, air_density_fan) + 
                get_c(fan_inlet_k, total_fan_area, air_density_fan))

    C_vp = air_density_fan / ((total_fan_area ** 2) * (1096.7 ** 2))
    C_total = C_static + C_vp

    # 4. Safe Diameter-Specific Fan Lookup
    fan_curve = FAN_CURVES.get(fan_diameter)
    
    if not fan_curve:
        closest_diam = min(FAN_CURVES.keys(), key=lambda k: abs(k - fan_diameter))
        fan_curve = FAN_CURVES[closest_diam]

    def get_fan_pressure(cfm_guess):
        cfm_1hp = cfm_guess / (fan_hp ** (1.0/3.0))
        p_1hp = (fan_curve['A'] * (cfm_1hp ** 2)) + (fan_curve['B'] * cfm_1hp) + fan_curve['C']
        if p_1hp < 0: p_1hp = 0
        return p_1hp * (fan_hp ** (2.0/3.0))

    ## 5. Bisection Algorithm
    low_cfm = 100.0
    # Raise the absolute ceiling to 2.5 million CFM per cell to handle industrial fans
    high_cfm = 2500000.0 * cells 
    tolerance = 1.0
    
    for _ in range(100):
        mid_cfm = (low_cfm + high_cfm) / 2.0
        system_pressure = C_total * (mid_cfm ** 2)
        fan_pressure = get_fan_pressure(mid_cfm / cells)
        
        if system_pressure > fan_pressure:
            high_cfm = mid_cfm
        else:
            low_cfm = mid_cfm
            
        if (high_cfm - low_cfm) < tolerance:
            total_cfm = mid_cfm
            break

    v_inlet = total_cfm / inlet_area if inlet_area > 0 else 0
    v_fill = total_cfm / fill_area if fill_area > 0 else 0
    v_fan = total_cfm / total_fan_area if total_fan_area > 0 else 0

    results = {
        "Air Inlet": {"area": inlet_area, "vel": v_inlet, "dp": get_c(louver_k, inlet_area, air_density_inlet) * (total_cfm**2)},
        "Rain Zone": {"area": fill_area, "vel": v_fill, "dp": get_c(k_rain, fill_area, air_density_fan) * (total_cfm**2)},
        "Fill": {"area": fill_area, "vel": v_fill, "dp": get_c(k_fill_total, fill_area, air_density_fan) * (total_cfm**2)},
        "Spray Zone": {"area": fill_area, "vel": v_fill, "dp": get_c(k_spray, fill_area, air_density_fan) * (total_cfm**2)},
        "Drift Eliminator": {"area": fill_area, "vel": v_fill, "dp": get_c(drift_k, fill_area, air_density_fan) * (total_cfm**2)},
        "Fan Inlet": {"area": total_fan_area, "vel": v_fan, "dp": get_c(fan_inlet_k, total_fan_area, air_density_fan) * (total_cfm**2)}
    }
    
    results["Total Static dP"] = sum(item["dp"] for item in results.values())
    results["Operating CFM"] = total_cfm / cells if cells > 0 else total_cfm
    
    return results