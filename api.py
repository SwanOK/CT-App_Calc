# api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psychrolib

# Import your existing engine functions!
from core.aero_engine import run_aero_rating
from core.thermal_engine import run_thermal_rating

psychrolib.SetUnitSystem(psychrolib.IP)
app = FastAPI(title="Cooling Tower API")

# Allow the frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the exact inputs the browser will send us
class TowerInput(BaseModel):
    gpm: float
    hw: float
    cw: float
    wb: float
    rh: float
    altitude: float
    fan_hp: float
    cells: int
    cell_width_ft: float
    cell_length_ft: float
    inlet_height_ft: float
    inlet_obstruction_percent: float
    louver_coeff: float
    fill_type: str
    fill_height_ft: float
    fill_obstruction_percent: float
    kavl_derate: float
    fan_diameter_ft: float
    hub_diameter_ft: float
    fan_inlet_coeff: float

@app.post("/simulate")
def run_simulation(data: TowerInput):
    try:
        user_data = data.dict()
        patm = psychrolib.GetStandardAtmPressure(user_data['altitude'])
        
        # 1. Reverse Psychrometric Solver (From your main.py)
        target_rh = user_data['rh'] / 100.0
        low_db, high_db, derived_db = user_data['wb'], 150.0, user_data['wb']
        for _ in range(100):
            mid_db = (low_db + high_db) / 2.0
            calc_hum_ratio = psychrolib.GetHumRatioFromTWetBulb(mid_db, user_data['wb'], patm)
            calc_rh = psychrolib.GetRelHumFromHumRatio(mid_db, calc_hum_ratio, patm)
            if calc_rh < target_rh: high_db = mid_db 
            else: low_db = mid_db 
            if (high_db - low_db) < 0.001:
                derived_db = mid_db
                break

        inlet_w = psychrolib.GetHumRatioFromTWetBulb(derived_db, user_data['wb'], patm)
        v_moist_inlet = psychrolib.GetMoistAirVolume(derived_db, inlet_w, patm)
        inlet_mixture_density = (1.0 + inlet_w) / v_moist_inlet
        
        exit_temp_est = ((user_data['hw'] + user_data['cw']) / 2.0) + 2.0
        fan_w = psychrolib.GetSatHumRatio(exit_temp_est, patm)
        v_moist_fan = psychrolib.GetMoistAirVolume(exit_temp_est, fan_w, patm)
        fan_mixture_density = (1.0 + fan_w) / v_moist_fan

        gpm_per_cell = user_data['gpm'] / user_data['cells']
        cell_area_gross = user_data['cell_width_ft'] * user_data['cell_length_ft']
        cell_area_net = cell_area_gross * (1.0 - (user_data['fill_obstruction_percent'] / 100.0))
        water_loading = gpm_per_cell / cell_area_net

        # 2. Run Aero Engine
        aero_results = run_aero_rating(
            geometry_data=user_data, fan_hp=user_data['fan_hp'],
            water_loading=water_loading, air_density_inlet=inlet_mixture_density,
            air_density_fan=fan_mixture_density
        )

        operating_cfm = aero_results["Operating CFM"]
        dry_air_lbs_min = operating_cfm / v_moist_fan

        # 3. Run Thermal Engine
        thermal_results = run_thermal_rating(
            fill_type=user_data['fill_type'], fill_height=user_data['fill_height_ft'],
            water_flow_gpm=gpm_per_cell, dry_air_lbs_min=dry_air_lbs_min,
            hw=user_data['hw'], cw=user_data['cw'], wb=user_data['wb'],
            altitude_ft=user_data['altitude'], derate_percent=user_data['kavl_derate']
        )
        
        # Send everything back to the browser as JSON!
        return {
            "status": "success",
            "metrics": {
                "capability": thermal_results['capability_percent'],
                "oper_lg": thermal_results['lg_ratio'],
                "adj_lg": thermal_results['lg_adjusted'],
                "cfm": operating_cfm,
                "water_loading": water_loading,
                "derived_db": derived_db
            },
            "thermal": thermal_results,
            "aero": aero_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))