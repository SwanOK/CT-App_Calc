from calculations.thermal import calculate_thermal
from calculations.pressure import calculate_pressure

def main():
    # Define Inputs
    inputs = {
        "water_flow_gpm": 2200.0,
        "wet_bulb_f": 84.2,
        "rel_humidity_pct": 70.0,
        "range_f": 9.0,
        "altitude_ft": 750.0,
        
        "num_cells": 1,
        "cell_width_ft": 18.0,
        "cell_length_ft": 18.0,
        "inlet_height_ft": 3.5,
        "inlet_obstruction_pct": 5.0,
        
        "fill_height_ft": 3.0,
        "spray_height_ft": 1.25,
        "rain_height_ft": 3.5,
        "kavl_derate_pct": 5.0,
        "dp_derate_pct": 5.0,
        
        "fill_characteristic_k": 1.028, 
        "fan_airflow_cfm": 184435.1,
        
        "cold_water_f": 89.60,
    }
    
    # Calculated Inputs
    inputs["hot_water_f"] = inputs["cold_water_f"] + inputs["range_f"]

    # Run Calculations
    thermal_results, shared_vars = calculate_thermal(inputs)
    pressure_results = calculate_pressure(inputs, shared_vars)

    # Display Results
    print("\n" + "="*30)
    print(" THERMAL RESULTS")
    print("="*30)
    for key, value in thermal_results.items():
        print(f"{key}: {value}")

    print("\n" + "="*30)
    print(" PRESSURE DROP RESULTS")
    print("="*30)
    for key, value in pressure_results.items():
        print(f"{key}: {value}")
    print("\n")

if __name__ == "__main__":
    main()