import math

def run_aero_rating(geometry_data, fan_hp, water_loading, air_density_inlet, air_density_fan, trans_eff=95.0, fan_eff=75.0):
    cells = geometry_data['cells']

    # --- 1. Calculate Cross-Sectional Areas ---
    inlet_area_gross = cells * ((geometry_data['cell_length_ft'] + geometry_data['cell_width_ft']) * 2.0 * geometry_data['inlet_height_ft'])
    inlet_area_net = inlet_area_gross * (1.0 - (geometry_data['inlet_obstruction_percent'] / 100.0))

    tower_area_gross = cells * (geometry_data['cell_width_ft'] * geometry_data['cell_length_ft'])
    tower_area_net = tower_area_gross * (1.0 - (geometry_data['fill_obstruction_percent'] / 100.0))

    fan_radius = geometry_data['fan_diameter_ft'] / 2.0
    hub_radius = geometry_data['hub_diameter_ft'] / 2.0
    fan_net_area = cells * (math.pi * (fan_radius**2) - math.pi * (hub_radius**2))

    # --- 2. Base Mechanical Power & Installation Penalty ---
    mechanical_efficiency = (trans_eff / 100.0) * (fan_eff / 100.0)
    fan_to_box_ratio = fan_net_area / tower_area_net
    installation_efficiency = 0.70 + (0.30 * fan_to_box_ratio)
    
    effective_efficiency = mechanical_efficiency * installation_efficiency
    available_hp_per_cell = fan_hp * effective_efficiency

    # --- 3. Dynamic Aerodynamic Bisection Algorithm ---
    low_cfm = 100.0
    high_cfm = 2500000.0 * cells
    tolerance = 1.0
    operating_cfm = 0.0
    final_results = {}

    for _ in range(100):
        test_cfm = (low_cfm + high_cfm) / 2.0

        v_inlet = test_cfm / inlet_area_net
        v_tower = test_cfm / tower_area_net
        v_fan = test_cfm / fan_net_area

        vp_inlet = ((v_inlet / 4005.0) ** 2) * (air_density_inlet / 0.075)
        vp_tower = ((v_tower / 4005.0) ** 2) * (((air_density_inlet + air_density_fan) / 2.0) / 0.075)
        vp_fan = ((v_fan / 4005.0) ** 2) * (air_density_fan / 0.075)

        # --- THE FIX: Highly accurate component resistance factors ---
        
        # Calculate dynamic fill resistance per foot of depth
        if geometry_data.get('fill_type') == 'CF-1200':
            k_fill_per_ft = 6.4 + (0.15 * water_loading)
        else: # CF-1900
            k_fill_per_ft = 4.0 + (0.10 * water_loading)
            
        dp_inlet = (1.0 * geometry_data['louver_coeff']) * vp_inlet
        dp_rain = 1.71 * vp_tower
        
        # Multiply the specific fill drag by the exact height of the fill block
        dp_fill = (k_fill_per_ft * geometry_data.get('fill_height_ft', 1.0)) * vp_tower 
        
        dp_spray = 5.0 * vp_tower
        dp_de = 1.92 * vp_tower
        dp_fan_inlet = geometry_data['fan_inlet_coeff'] * vp_fan

        sum_static_dp = dp_inlet + dp_rain + dp_fill + dp_spray + dp_de + dp_fan_inlet
        total_system_pressure = sum_static_dp + vp_fan

        hp_required_total = (test_cfm * total_system_pressure) / 6356.0
        hp_required_per_cell = hp_required_total / cells

        if hp_required_per_cell > available_hp_per_cell:
            high_cfm = test_cfm  
        else:
            low_cfm = test_cfm   

        if (high_cfm - low_cfm) < tolerance:
            operating_cfm = test_cfm
            final_results = {
                "Air Inlet": {"vel": v_inlet, "dp": dp_inlet, "area": inlet_area_net},
                "Rain Zone": {"vel": v_tower, "dp": dp_rain, "area": tower_area_net},
                "Fill": {"vel": v_tower, "dp": dp_fill, "area": tower_area_net},
                "Spray Zone": {"vel": v_tower, "dp": dp_spray, "area": tower_area_net},
                "Drift Eliminator": {"vel": v_tower, "dp": dp_de, "area": tower_area_net},
                "Fan Inlet": {"vel": v_fan, "dp": dp_fan_inlet, "area": fan_net_area},
                "Total Static dP": sum_static_dp,
                "Operating CFM": operating_cfm
            }
            break

    return final_results