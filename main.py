# main.py
from calculations.thermal import calculate_thermal
from calculations.pressure import calculate_pressure

def main():
    # Defining fully parameterized input variables matching Report 8 baseline configurations
    inputs = {
        # Step 1: Thermal
        "water_flow_gpm": 2200.0,
        "wet_bulb_f": 84.2,
        "rel_humidity_pct": 70.0,
        "range_f": 9.0,
        "altitude_ft": 750.0,
        "cold_water_f": 89.60,
        "override_dbt": 93.0, # Forces DBT to match test report reference points
        
        # Step 2: Footprint
        "num_cells": 1,
        "cell_width_ft": 18.0,
        "cell_length_ft": 18.0,
        "inlet_height_ft": 3.5,
        "inlet_obstruction_pct": 5.0,
        
        # Step 3: Internals Lookups
        "fill_type": "CF-1900SB",
        "drift_type": "DE120",
        "fill_height_ft": 3.0,
        "spray_height_ft": 1.25,
        "rain_height_ft": 3.5,
        "kavl_derate_pct": 0.0, # Zeroed out to check baseline math precision
        "dp_derate_pct": 0.0,
        
        # Step 4: Motor & Plenum Parameters
        "fan_airflow_cfm": 184435.1,
        "fan_diameter_ft": 12.0,
        "seal_disk_diameter_ft": 2.16,
        "fan_inlet_loss_coeff": 0.50,
        "transmission_eff_pct": 100.0,
        "total_fan_eff_pct": 75.0,
        "fan_stack_regain": False
    }
    
    inputs["hot_water_f"] = inputs["cold_water_f"] + inputs["range_f"]

    # Run Modules
    thermal_results, shared_vars = calculate_thermal(inputs)
    pressure_results = calculate_pressure(inputs, shared_vars)

    print("\n" + "="*35)
    print(" THERMAL MATRIX ENGINE OUTPUTS")
    print("="*35)
    for key, value in thermal_results.items():
        print(f"{key}: {value}")

    print("\n" + "="*35)
    print(" PLENUM & PRESSURE DROPS OUTPUTS")
    print("="*35)
    for key, value in pressure_results.items():
        print(f"{key}: {value}")
    print("\n")

if __name__ == "__main__":
    main()