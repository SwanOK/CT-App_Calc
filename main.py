from calculations.thermal import calculate_thermal
from calculations.pressure import calculate_pressure

def get_input(prompt_text, default_value):
    """
    Helper function to ask for input but fall back to a default if the user just presses Enter.
    Also includes basic error handling so typos don't crash the program.
    """
    while True:
        user_in = input(f"{prompt_text} [{default_value}]: ").strip()
        if user_in == "":
            return default_value
        try:
            return float(user_in)
        except ValueError:
            print("  -> Invalid input. Please enter a valid number.")

def main():
    print("\n=== COOLING TOWER PERFORMANCE CALCULATOR ===")
    print("Press ENTER to accept the default value, or type a new number.\n")

    inputs = {}

    # 1. Thermal Conditions
    print("--- Thermal Conditions ---")
    inputs["water_flow_gpm"] = get_input("Water Flow (GPM)", 2200.0)
    inputs["wet_bulb_f"]     = get_input("Wet Bulb (°F)", 84.2)
    inputs["rel_humidity_pct"]= get_input("Relative Humidity (%)", 70.0)
    inputs["range_f"]        = get_input("Range (°F)", 9.0)
    inputs["altitude_ft"]    = get_input("Altitude (ft)", 750.0)
    inputs["cold_water_f"]   = get_input("Cold Water Target (°F)", 89.60)
    print()

    # 2. Tower Geometry
    print("--- Tower Geometry ---")
    inputs["num_cells"]             = get_input("Number of Cells", 1.0)
    inputs["cell_width_ft"]         = get_input("Cell Width (ft)", 18.0)
    inputs["cell_length_ft"]        = get_input("Cell Length (ft)", 18.0)
    inputs["inlet_height_ft"]       = get_input("Inlet Height (ft)", 3.5)
    inputs["inlet_obstruction_pct"] = get_input("Inlet Obstruction (%)", 5.0)
    print()

    # 3. Fill & Internal Specifications
    print("--- Internal Specifications ---")
    inputs["fill_height_ft"]        = get_input("Fill Height (ft)", 3.0)
    inputs["spray_height_ft"]       = get_input("Spray Height (ft)", 1.25)
    inputs["rain_height_ft"]        = get_input("Rain Height (ft)", 3.5)
    inputs["kavl_derate_pct"]       = get_input("KaV/L Derate (%)", 5.0)
    inputs["dp_derate_pct"]         = get_input("Pressure Drop Derate (%)", 5.0)
    inputs["fill_characteristic_k"] = get_input("Fill Characteristic (K)", 1.028)
    inputs["fan_airflow_cfm"]       = get_input("Fan Airflow (CFM)", 184435.1)
    
    # Calculated Inputs
    inputs["hot_water_f"] = inputs["cold_water_f"] + inputs["range_f"]

    print("\nCalculating...")

    # Run Calculations
    thermal_results, shared_vars = calculate_thermal(inputs)
    pressure_results = calculate_pressure(inputs, shared_vars)

    # Display Results
    print("\n" + "="*35)
    print(" THERMAL RESULTS")
    print("="*35)
    for key, value in thermal_results.items():
        print(f"{key}: {value}")

    print("\n" + "="*35)
    print(" PRESSURE DROP RESULTS")
    print("="*35)
    for key, value in pressure_results.items():
        print(f"{key}: {value}")
    print("\n")

if __name__ == "__main__":
    main()