import math
from core.constants import AERO_DYNAMIC_K

def run_aero_rating(geometry_data, fan_hp, water_loading, v_inlet, v_fill, v_fan, trans_eff, fan_eff):
    cells = geometry_data['cells']
    
    # 1. Exact Geometric Areas
    L = geometry_data['cell_length_ft']
    W = geometry_data['cell_width_ft']
    faces = geometry_data.get('air_inlet_faces', 4) 
    
    # If "Both Ends Open" on a 1-cell tower, it draws from all 4 sides. 
    perimeter = (L + W) * 2 if faces == 4 else L * 2
    
    inlet_area_gross = cells * perimeter * geometry_data['inlet_height_ft']
    inlet_area_net = inlet_area_gross * (1.0 - geometry_data['inlet_obstruction_percent'] / 100.0)

    tower_area_gross = cells * L * W
    tower_area_net = tower_area_gross * (1.0 - geometry_data['fill_obstruction_percent'] / 100.0)

    # Use exact Plenum Hole diameter for Fan:Box Ratio
    plenum_hole_dia = geometry_data.get('plenum_hole_diameter_ft', 7.17)
    fan_gross_area = cells * math.pi * (plenum_hole_dia / 2.0)**2
    hub_area = cells * math.pi * (geometry_data['hub_diameter_ft'] / 2.0)**2
    fan_net_area = fan_gross_area - hub_area

    # 2. The Exact CTI System Effect Penalty
    fan_box_ratio = fan_gross_area / tower_area_gross
    mechanical_efficiency = (trans_eff / 100.0) * (fan_eff / 100.0)
    installation_efficiency = 0.65 + (0.35 * min(fan_box_ratio, 1.0))
    effective_efficiency = mechanical_efficiency * installation_efficiency
    available_hp_per_cell = fan_hp * effective_efficiency

    # Local Densities
    rho_in = 1.0 / v_inlet
    rho_fill = 1.0 / v_fill
    rho_out = 1.0 / v_fan

    low_mass, high_mass, tolerance = 100.0, 500000.0 * cells, 1.0
    operating_cfm = 0.0
    final_results = {}

    for _ in range(100):
        test_dry_mass = (low_mass + high_mass) / 2.0
        
        # 3. MASS CONSERVATION (CFM expands as specific volume increases)
        cfm_in = test_dry_mass * v_inlet
        cfm_fill = test_dry_mass * v_fill
        cfm_fan = test_dry_mass * v_fan

        # Local Velocities
        v_in_vel = cfm_in / inlet_area_net
        v_rain = cfm_in / tower_area_net
        v_fill_vel = cfm_fill / tower_area_net
        v_spray = cfm_fan / tower_area_net
        v_de = cfm_fan / tower_area_net
        v_fan_vel = cfm_fan / fan_net_area

        # Local Velocity Pressures
        vp_in = (v_in_vel / 4005.0)**2 * (rho_in / 0.075)
        vp_rain = (v_rain / 4005.0)**2 * (rho_in / 0.075)
        vp_fill = (v_fill_vel / 4005.0)**2 * (rho_fill / 0.075)
        vp_spray = (v_spray / 4005.0)**2 * (rho_out / 0.075)
        vp_de = (v_de / 4005.0)**2 * (rho_out / 0.075)
        vp_fan = (v_fan_vel / 4005.0)**2 * (rho_out / 0.075)

        # Dynamic Constants from Master Regression
        fill_type = geometry_data.get('fill_type', 'CF-1200 MABT')
        fill_key = f"{fill_type}_Per_Foot"
        K_fill = AERO_DYNAMIC_K.get(fill_key, {'a': 6.4}).get('a', 6.4) * (water_loading ** AERO_DYNAMIC_K.get(fill_key, {'b': 0.15}).get('b', 0.15))
        K_rain = AERO_DYNAMIC_K.get('Rain', {'a': 1.71}).get('a', 1.71) * (water_loading ** AERO_DYNAMIC_K.get('Rain', {'b': 0.0}).get('b', 0.0))
        K_spray = AERO_DYNAMIC_K.get('Spray', {'a': 5.0}).get('a', 5.0) * (water_loading ** AERO_DYNAMIC_K.get('Spray', {'b': 0.0}).get('b', 0.0))

        # Static Pressure Drops
        dp_in = geometry_data['louver_coeff'] * vp_in
        dp_rain = K_rain * vp_rain
        dp_fill = K_fill * geometry_data['fill_height_ft'] * vp_fill
        dp_spray = K_spray * vp_spray
        dp_de = 1.88 * vp_de  
        dp_fan_in = geometry_data['fan_inlet_coeff'] * vp_fan

        # Buoyancy (Negative pressure draft)
        tot_ht = geometry_data.get('rain_height_ft', 4.0) + geometry_data['fill_height_ft'] + geometry_data.get('spray_height_ft', 1.0) + geometry_data.get('plenum_height_ft', 2.54)
        dp_buoy = tot_ht * (rho_out - rho_in) / 5.2

        sum_static = dp_in + dp_rain + dp_fill + dp_spray + dp_de + dp_fan_in + dp_buoy
        total_p = sum_static + vp_fan

        # 4. PURE THEORETICAL BHP BALANCE (No corrupted Fan Curves)
        hp_req_per_cell = ((cfm_fan * total_p) / 6356.0) / cells
        
        if hp_req_per_cell > available_hp_per_cell: 
            high_mass = test_dry_mass
        else: 
            low_mass = test_dry_mass

        if (high_mass - low_mass) < tolerance:
            operating_cfm = cfm_fan
            final_results = {
                "Air Inlet": {"vel": v_in_vel, "rho": rho_in, "dp": dp_in, "area": inlet_area_net},
                "Rain Zone": {"vel": v_rain, "rho": rho_in, "dp": dp_rain, "area": tower_area_net},
                "Fill": {"vel": v_fill_vel, "rho": rho_fill, "dp": dp_fill, "area": tower_area_net},
                "Spray Zone": {"vel": v_spray, "rho": rho_out, "dp": dp_spray, "area": tower_area_net},
                "Drift Eliminator": {"vel": v_de, "rho": rho_out, "dp": dp_de, "area": tower_area_net},
                "Fan Inlet": {"vel": v_fan_vel, "rho": rho_out, "dp": dp_fan_in, "area": fan_net_area},
                "Buoyancy": {"vel": 0.0, "rho": 0.0, "dp": dp_buoy, "area": 0.0},
                "Sum Static dP": sum_static,
                "Net Fan VP": {"vel": v_fan_vel, "rho": rho_out, "dp": vp_fan},
                "Fan Total Pressure": total_p,
                "Operating CFM": operating_cfm,
                "fan_box_ratio": fan_box_ratio * 100.0,
                "effective_fan_eff": effective_efficiency * 100.0,
                "dry_air_mass_rate": test_dry_mass
            }
            break

    return final_results