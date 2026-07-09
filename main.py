import sys
from rich.console import Console
from rich.prompt import Prompt, FloatPrompt, IntPrompt
from rich.table import Table
from rich.panel import Panel
import psychrolib

try:
    from core.aero_engine import run_aero_rating
    from core.thermal_engine import run_thermal_rating 
except ImportError as e:
    print(f"Project Structure Error: {e}")
    sys.exit(1)

psychrolib.SetUnitSystem(psychrolib.IP)
console = Console()

def run_interactive_wizard():
    data = {}
    console.print(Panel.fit("[bold cyan]COOLING TOWER RATING WIZARD[/bold cyan]", border_style="cyan"))

    console.rule("[bold blue]STEP 1: THERMAL CONDITIONS[/bold blue]")
    data['gpm'] = FloatPrompt.ask("Total Water Flow (gpm)", default=1149.9)
    data['hw'] = FloatPrompt.ask("Hot Water Temp (F)", default=97.5)
    data['cw'] = FloatPrompt.ask("Cold Water Temp (F)", default=90.0)
    data['wb'] = FloatPrompt.ask("Wet Bulb Temp (F)", default=83.0)
    data['rh'] = FloatPrompt.ask("Relative Humidity (%)", default=50.0)
    data['altitude'] = FloatPrompt.ask("Site Altitude (ft)", default=0.0)
    data['fan_hp'] = FloatPrompt.ask("Fan Motor Power per cell (HP)", default=10.0)
    print("\n")

    console.rule("[bold blue]STEP 2: TOWER GEOMETRY[/bold blue]")
    data['cells'] = IntPrompt.ask("No. of Cells", default=2)
    data['cell_width_ft'] = FloatPrompt.ask("Cell Width (ft)", default=10.0)
    data['cell_length_ft'] = FloatPrompt.ask("Cell Length (ft)", default=9.0)
    data['inlet_height_ft'] = FloatPrompt.ask("Inlet Height (ft)", default=4.0)
    data['inlet_obstruction_percent'] = FloatPrompt.ask("Inlet Obstruction (%)", default=5.0)
    data['louver_coeff'] = FloatPrompt.ask("Louver Coefficient", default=1.0)
    print("\n")

    console.rule("[bold blue]STEP 3: FILL SECTION[/bold blue]")
    data['fill_type'] = Prompt.ask("Fill Type", choices=["CF-1200", "CF-1900"], default="CF-1200")
    data['fill_height_ft'] = FloatPrompt.ask("Fill Height (ft)", default=1.96)
    data['fill_obstruction_percent'] = FloatPrompt.ask("Fill Obstruction (%)", default=5.0)
    data['kavl_derate'] = FloatPrompt.ask("KaV/L Derate (%)", default=5.0)
    # The manual HWT Correction input has been completely removed.
    print("\n")

    console.rule("[bold blue]STEP 4: PLENUM & FAN[/bold blue]")
    data['fan_diameter_ft'] = FloatPrompt.ask("Fan Diameter (ft)", default=6.0)
    data['hub_diameter_ft'] = FloatPrompt.ask("Seal Disk/Hub Diameter (ft)", default=1.26)
    data['fan_inlet_coeff'] = FloatPrompt.ask("Fan Inlet Loss Coefficient", default=0.50)
    print("\n")

    return data

def print_thermal_results(data, thermal_results, operating_cfm, water_loading, derived_db):
    cap = thermal_results['capability_percent']
    lg_oper = thermal_results['lg_ratio']
    lg_adj = thermal_results['lg_adjusted']
    
    console.print(Panel(f"Capability: [bold green]{cap:.1f} %[/bold green] \t Oper L/G: [bold blue]{lg_oper:.4f}[/bold blue] \t Adj L/G: [bold yellow]{lg_adj:.4f}[/bold yellow] \nCFM: [bold cyan]{operating_cfm:,.1f}[/bold cyan] \t WL: [bold magenta]{water_loading:.2f} gpm/ft²[/bold magenta] \t Derived DB: [bold white]{derived_db:.1f} F[/bold white]", expand=False))
    
    kavl_table = Table(title="KaV/L Data", show_header=True, header_style="bold magenta")
    kavl_table.add_column("Section", style="dim", width=25)
    kavl_table.add_column("Value", justify="right")
    
    kavl_table.add_row("Spray Zone", f"{thermal_results['spray_kavl']:.4f}")
    kavl_table.add_row(f"{data['fill_type']} - {data['fill_height_ft']} ft", f"{thermal_results['fill_kavl']:.4f}", style="blue")
    kavl_table.add_row("Rain Zone", f"{thermal_results['rain_kavl']:.4f}")
    kavl_table.add_row("Total Available KaV/L", f"{thermal_results['total_available_kavl']:.4f}")
    kavl_table.add_row("KaV/L Derate (%)", f"{data['kavl_derate']:.1f}")
    
    # Dynamically fetch the applied correction from the physics engine
    hwt_applied = thermal_results.get('hwt_corr_applied', 0.0)
    if hwt_applied > 0:
        kavl_table.add_row("HWT Correction (%)", f"{hwt_applied:.2f}", style="red")
        
    kavl_table.add_row("KaV/L Adjusted", f"{thermal_results.get('kavl_adjusted', thermal_results['total_available_kavl']):.4f}", style="bold white")
    
    console.print(kavl_table)

def print_airflow_results(aero_results):
    console.print("\n") 
    dp_table = Table(title="System Pressure Drop", show_header=True, header_style="bold cyan")
    dp_table.add_column("Tower Section", style="dim")
    dp_table.add_column("Net Area (ft²)", justify="right")
    dp_table.add_column("Velocity (ft/min)", justify="right", style="green")
    dp_table.add_column("Pres. Drop (in. wg)", justify="right", style="bold")

    for section, metrics in aero_results.items():
        if section in ["Total Static dP", "Operating CFM"]: continue 
        dp_table.add_row(section, f"{metrics['area']:.1f}", f"{metrics['vel']:.1f}", f"{metrics['dp']:.4f}")
    
    total_dp = aero_results.get("Total Static dP", 0.0)
    dp_table.add_row("Sum Static dP", "", "", f"{total_dp:.4f}", style="bold white")
    console.print(dp_table)

def main():
    try:
        user_data = run_interactive_wizard()
        console.rule("[bold yellow]CALCULATING DATA-DRIVEN PHYSICS...[/bold yellow]")
        print("\n")
        
        patm = psychrolib.GetStandardAtmPressure(user_data['altitude'])
        
        # --- THE REVERSE PSYCHROMETRIC SOLVER ---
        target_rh = user_data['rh'] / 100.0
        low_db = user_data['wb'] 
        high_db = 150.0 
        derived_db = user_data['wb']
        
        for _ in range(100):
            mid_db = (low_db + high_db) / 2.0
            
            calc_hum_ratio = psychrolib.GetHumRatioFromTWetBulb(mid_db, user_data['wb'], patm)
            calc_rh = psychrolib.GetRelHumFromHumRatio(mid_db, calc_hum_ratio, patm)
            
            if calc_rh < target_rh:
                high_db = mid_db 
            else:
                low_db = mid_db 
                
            if (high_db - low_db) < 0.001:
                derived_db = mid_db
                break
        # -----------------------------------------

        # 1. Exact Psychrometrics based on derived Dry Bulb
        inlet_w = psychrolib.GetHumRatioFromTWetBulb(derived_db, user_data['wb'], patm)
        v_moist_inlet = psychrolib.GetMoistAirVolume(derived_db, inlet_w, patm)
        inlet_mixture_density = (1.0 + inlet_w) / v_moist_inlet
        
        # 2. Exit properties
        exit_temp_est = ((user_data['hw'] + user_data['cw']) / 2.0) + 2.0
        fan_w = psychrolib.GetSatHumRatio(exit_temp_est, patm)
        v_moist_fan = psychrolib.GetMoistAirVolume(exit_temp_est, fan_w, patm)
        fan_mixture_density = (1.0 + fan_w) / v_moist_fan

        # 3. Water Loading
        gpm_per_cell = user_data['gpm'] / user_data['cells']
        cell_area_gross = user_data['cell_width_ft'] * user_data['cell_length_ft']
        fill_obstruction_decimal = user_data['fill_obstruction_percent'] / 100.0
        cell_area_net = cell_area_gross * (1.0 - fill_obstruction_decimal)
        water_loading = gpm_per_cell / cell_area_net

        # 4. Aerodynamic Engine
        aero_results = run_aero_rating(
            geometry_data=user_data,
            fan_hp=user_data['fan_hp'],
            water_loading=water_loading,
            air_density_inlet=inlet_mixture_density,
            air_density_fan=fan_mixture_density
        )

        operating_cfm = aero_results["Operating CFM"]
        dry_air_lbs_min = operating_cfm / v_moist_fan

        # 5. Thermodynamic Engine (Notice hwt_corr is missing from the arguments!)
        thermal_results = run_thermal_rating(
            fill_type=user_data['fill_type'],
            fill_height=user_data['fill_height_ft'],
            water_flow_gpm=gpm_per_cell, 
            dry_air_lbs_min=dry_air_lbs_min,
            hw=user_data['hw'],
            cw=user_data['cw'],
            wb=user_data['wb'],
            altitude_ft=user_data['altitude'],
            derate_percent=user_data['kavl_derate']
        )
        
        print_thermal_results(user_data, thermal_results, operating_cfm, water_loading, derived_db)
        print_airflow_results(aero_results)
        
    except KeyboardInterrupt:
        console.print("\n[bold red]Wizard cancelled.[/bold red]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Simulation Error:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
    