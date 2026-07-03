# main.py
import sys
from calculations.thermal import calculate_thermal
from calculations.pressure import solve_airflow

# Prevent Python from writing __pycache__ files programmatically
sys.dont_write_bytecode = True 

def get_float_input(prompt_text, default_value):
    while True:
        user_in = input(f"{prompt_text} [{default_value}]: ").strip()
        if user_in == "": return default_value
        try: return float(user_in)
        except ValueError: print("  -> Invalid numeric input.")

def get_string_input(prompt_text, default_value, allowed_choices=None):
    while True:
        user_in = input(f"{prompt_text} [{default_value}]: ").strip()
        if user_in == "": return default_value
        if allowed_choices and user_in not in allowed_choices:
            print(f"  -> Choice not recognized. Allowed options: {allowed_choices}")
            continue
        return user_in

def get_bool_input(prompt_text, default_value):
    default_str = "Y" if default_value else "N"
    while True:
        user_in = input(f"{prompt_text} (Y/N) [{default_str}]: ").strip().upper()
        if user_in == "": return default_value
        if user_in in ["Y", "YES"]: return True
        if user_in in ["N", "NO"]: return False
        print("  -> Please enter Y or N.")

def main():
    print("\n" + "="*80)
    print(" BRENTWOOD S.T.A.R. CALIBRATED RATING ENGINE")
    print(" Press ENTER to accept the default parameter bracket")
    print("="*80 + "\n")

    inputs = {}

    print("--- STEP 1: Thermal & Atmospheric Conditions ---")
    inputs["water_flow_gpm"]   = get_float_input("Water Flow Rate (GPM)", 2200.0)
    inputs["wet_bulb_f"]       = get_float_input("Entering Air Wet Bulb (°F)", 84.2)
    inputs["range_f"]          = get_float_input("Thermal Range (°F)", 9.0)
    inputs["altitude_ft"]      = get_float_input("Site Altitude (ft)", 750.0)
    inputs["cold_water_f"]     = get_float_input("Target Cold Water Temp (°F)", 89.60)
    
    use_override = get_bool_input("Apply explicit fixed Inlet DBT override?", True)
    if use_override:
        inputs["override_dbt"] = get_float_input("  -> Explicit Inlet DBT (°F)", 93.0)
    print()

    print("--- STEP 2: Structural Footprint Geometry ---")
    inputs["num_cells"]             = int(get_float_input("Number of Cells", 1.0))
    inputs["cell_width_ft"]         = get_float_input("Individual Cell Width (ft)", 18.0)
    inputs["cell_length_ft"]        = get_float_input("Individual Cell Length (ft)", 18.0)
    inputs["inlet_height_ft"]       = get_float_input("Air Inlet Height (ft)", 3.5)
    inputs["inlet_obstruction_pct"] = get_float_input("Air Inlet Structural Obstruction (%)", 5.0)
    print()

    print("--- STEP 3: Internal Components Selection ---")
    inputs["fill_type"]            = get_string_input("Fill Media Model", "CF-1900SB", ["CF-1900SB", "CF-1200MABT"])
    inputs["drift_type"]           = get_string_input("Drift Eliminator Model", "DE120", ["DE120"])
    inputs["fill_height_ft"]       = get_float_input("Total Structural Fill Height (ft)", 3.0)
    inputs["spray_height_ft"]      = get_float_input("Spray Zone Fall Distance (ft)", 1.25)
    inputs["rain_height_ft"]       = get_float_input("Rain Zone Fall Distance (ft)", 3.5)
    inputs["kavl_derate_pct"]      = get_float_input("Thermal KaV/L Margin Derate (%)", 5.0)
    inputs["dp_derate_pct"]        = get_float_input("Pressure Drop Fouling Derate (%)", 5.0)
    inputs["fill_obstruction_pct"] = get_float_input("Fill Structural Obstruction (%)", 5.0)
    print()

    print("--- STEP 4: Plenum Mechanics & Fan Stack ---")
    inputs["motor_rated_hp"]        = get_float_input("Rated Motor Power (HP)", 30.0)
    inputs["fan_diameter_ft"]       = get_float_input("Fan Blade Diameter (ft)", 12.0)
    inputs["seal_disk_diameter_ft"] = get_float_input("Hub / Seal Disk Diameter (ft)", 2.16)
    inputs["fan_inlet_loss_coeff"]  = get_float_input("Fan Structure Inlet Loss Coefficient", 0.50)
    inputs["total_fan_eff_pct"]     = get_float_input("Total Mechanical Fan Efficiency (%)", 75.0)
    inputs["transmission_eff_pct"]  = get_float_input("Drive Transmission Efficiency (%)", 100.0)
    inputs["fan_stack_regain"]      = get_bool_input("Enable Aerodynamic Fan Stack Regain?", False)
    
    inputs["hot_water_f"] = inputs["cold_water_f"] + inputs["range_f"]

    print("\nProcessing Iterative System Curve Solver...")

    operating_cfm, pressure_results = solve_airflow(inputs)
    inputs["fan_airflow_cfm"] = operating_cfm
    thermal_results = calculate_thermal(inputs)

    print("\n" + "="*80)
    print(f" {'THERMAL RESULTS':<38} | {'PRESSURE DROP / AIR FLOW RESULTS':<38}")
    print("="*80)
    
    t_keys = list(thermal_results.keys())
    p_keys = list(pressure_results.keys())
    max_len = max(len(t_keys), len(p_keys))
    
    for i in range(max_len):
        t_str = f"{t_keys[i][:24]:<24}: {thermal_results[t_keys[i]]}" if i < len(t_keys) else ""
        p_str = f"{p_keys[i][:24]:<24}: {pressure_results[p_keys[i]]}" if i < len(p_keys) else ""
        print(f" {t_str:<38} | {p_str:<38}")
        
    print("="*80 + "\n")

if __name__ == "__main__":
    main()


