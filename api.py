from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psychrolib
import traceback

from core.aero_engine import run_aero_rating
from core.thermal_engine import run_thermal_rating
from core.constants import FILL_THERMAL, ZONE_THERMAL

psychrolib.SetUnitSystem(psychrolib.IP)
app = FastAPI(title="Delta Engine API")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
    air_inlet_faces: int
    louver_coeff: float
    fill_type: str
    fill_height_ft: float
    fill_obstruction_percent: float
    kavl_derate: float
    spray_height_ft: float
    rain_height_ft: float
    fan_diameter_ft: float
    hub_diameter_ft: float
    fan_inlet_coeff: float
    trans_eff: float 
    fan_eff: float   
    fan_tip_clearance_in: float
    plenum_hole_diameter_ft: float
    plenum_height_ft: float
    fan_stack_height_ft: float

@app.post("/simulate")
def run_simulation(data: TowerInput):
    try:
        user_data = data.model_dump() if hasattr(data, 'model_dump') else data.dict()
        patm = psychrolib.GetStandardAtmPressure(user_data['altitude'])
        
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

        # Calculate exact specific volume at the 3 nodes (Inlet, Middle, Exit)
        inlet_w = psychrolib.GetHumRatioFromTWetBulb(derived_db, user_data['wb'], patm)
        v_moist_inlet = psychrolib.GetMoistAirVolume(derived_db, inlet_w, patm)
        
        exit_wbt = ((user_data['hw'] + user_data['cw']) / 2.0) + 2.0
        fan_w = psychrolib.GetSatHumRatio(exit_wbt, patm)
        v_moist_fan = psychrolib.GetMoistAirVolume(exit_wbt, fan_w, patm)

        mid_db_fill = (derived_db + exit_wbt) / 2.0
        mid_w_fill = (inlet_w + fan_w) / 2.0
        v_moist_fill = psychrolib.GetMoistAirVolume(mid_db_fill, mid_w_fill, patm)

        # Exact water density based on operating temperature
        avg_water_temp = (user_data['hw'] + user_data['cw']) / 2.0
        water_density_lbs_gal = 8.34 - (0.0012 * (avg_water_temp - 60.0))
        gpm_per_cell = user_data['gpm'] / user_data['cells']
        water_lbs_min = gpm_per_cell * water_density_lbs_gal

        cell_area_gross = user_data['cell_width_ft'] * user_data['cell_length_ft']
        water_loading = gpm_per_cell / (cell_area_gross * (1.0 - user_data['fill_obstruction_percent'] / 100.0))

        # Run Aero Engine with Mass Conservation
        aero_results = run_aero_rating(
            geometry_data=user_data, fan_hp=user_data['fan_hp'],
            water_loading=water_loading, 
            v_inlet=v_moist_inlet, v_fill=v_moist_fill, v_fan=v_moist_fan,
            trans_eff=user_data['trans_eff'], fan_eff=user_data['fan_eff']
        )

        operating_cfm = aero_results["Operating CFM"]
        dry_air_lbs_min = aero_results["dry_air_mass_rate"]
        
        # The TRUE Operating L/G Ratio
        true_oper_lg = water_lbs_min / dry_air_lbs_min
        
        # Evaporation Psychrometrics
        evap_lbs_min = dry_air_lbs_min * (fan_w - inlet_w)
        evap_gpm = evap_lbs_min / 8.33
        evap_pct = (evap_gpm / user_data['gpm']) * 100.0

        thermal_results = run_thermal_rating(
            fill_type=user_data['fill_type'], fill_height=user_data['fill_height_ft'],
            water_flow_gpm=gpm_per_cell, dry_air_lbs_min=dry_air_lbs_min,
            hw=user_data['hw'], cw=user_data['cw'], wb=user_data['wb'],
            altitude_ft=user_data['altitude'], derate_percent=user_data['kavl_derate']
        )
        
        new_lg_adjusted = thermal_results['lg_adjusted']
        f_const = FILL_THERMAL.get(user_data['fill_type'], FILL_THERMAL.get("CF-1200 MABT"))
        
        thermal_results['fill_kavl'] = f_const['c'] * (new_lg_adjusted ** -f_const['n']) * (user_data['fill_height_ft'] ** f_const['m'])
        thermal_results['spray_kavl'] = ZONE_THERMAL['Spray']['a'] * (new_lg_adjusted ** ZONE_THERMAL['Spray']['b'])
        thermal_results['rain_kavl'] = ZONE_THERMAL['Rain']['a'] * (new_lg_adjusted ** ZONE_THERMAL['Rain']['b'])
        
        thermal_results['total_available_kavl'] = thermal_results['fill_kavl'] + thermal_results['spray_kavl'] + thermal_results['rain_kavl']
        thermal_results['kavl_adjusted'] = thermal_results['total_available_kavl'] * (1.0 - (user_data['kavl_derate']/100.0) - (thermal_results['hwt_corr_applied']/100.0))
        
        return {
            "status": "success",
            "metrics": {
                "capability": thermal_results['capability_percent'],
                "oper_lg": true_oper_lg,
                "adj_lg": new_lg_adjusted,
                "cfm": operating_cfm,
                "water_loading": water_loading,
                "derived_db": derived_db,
                "exit_wbt": exit_wbt,
                "dry_air_rate": dry_air_lbs_min,
                "evap_gpm": evap_gpm,
                "evap_pct": evap_pct,
                "fan_box_ratio": aero_results['fan_box_ratio'],
                "effective_fan_eff": aero_results['effective_fan_eff']
            },
            "thermal": thermal_results,
            "aero": aero_results
        }
    except Exception as e:
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=str(e))