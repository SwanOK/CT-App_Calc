# core/thermal_engine.py
import psychrolib
from core.constants import FILL_THERMAL, ZONE_THERMAL, HWT_CORRECTION

psychrolib.SetUnitSystem(psychrolib.IP)

def get_required_kavl_tchebycheff(hw, cw, wb, lg_ratio, altitude_ft):
    if lg_ratio <= 0: return 0.1
    patm = psychrolib.GetStandardAtmPressure(altitude_ft)
    hum_ratio_in = psychrolib.GetSatHumRatio(wb, patm)
    ha_in = psychrolib.GetMoistAirEnthalpy(wb, hum_ratio_in)
    
    cooling_range = hw - cw
    t1 = cw + (0.1 * cooling_range)
    t2 = cw + (0.4 * cooling_range)
    t3 = cw + (0.6 * cooling_range)
    t4 = cw + (0.9 * cooling_range)
    
    def get_driving_force(t_water):
        # DYNAMIC EVAPORATIVE SHRINKAGE:
        # Water mass shrinks by approx 0.1% for every 1 degree F of cooling.
        # At HW (top), evap_fraction is 0. At CW (bottom), evap_fraction is max.
        evap_fraction = (hw - t_water) / 1000.0
        local_lg = lg_ratio * (1.0 - evap_fraction)
        
        # Calculate the operating air enthalpy using the shrunken L/G mass
        ha_operating = ha_in + (local_lg * (t_water - cw))
        
        hw_sat = psychrolib.GetMoistAirEnthalpy(t_water, psychrolib.GetSatHumRatio(t_water, patm))
        dh = hw_sat - ha_operating
        if dh <= 0: dh = 0.001 
        return 1.0 / dh

    sum_inverse_dh = get_driving_force(t1) + get_driving_force(t2) + get_driving_force(t3) + get_driving_force(t4)
    return (cooling_range / 4.0) * sum_inverse_dh

def run_thermal_rating(fill_type, fill_height, water_flow_gpm, dry_air_lbs_min, hw, cw, wb, altitude_ft, derate_percent):
    
    # 1. Operating Point
    avg_water_temp = (hw + cw) / 2.0
    water_density_lbs_gal = 8.34 - (0.0012 * (avg_water_temp - 60.0))
    water_lbs_min = water_flow_gpm * water_density_lbs_gal 
    
    lg_ratio_operating = water_lbs_min / dry_air_lbs_min if dry_air_lbs_min > 0 else 0
    
    f_const = FILL_THERMAL.get(fill_type, FILL_THERMAL.get("CF-1900"))
    fill_kavl_op = f_const['c'] * (lg_ratio_operating ** -f_const['n']) * (fill_height ** f_const['m'])
    spray_kavl_op = ZONE_THERMAL['Spray']['a'] * (lg_ratio_operating ** ZONE_THERMAL['Spray']['b'])
    rain_kavl_op = ZONE_THERMAL['Rain']['a'] * (lg_ratio_operating ** ZONE_THERMAL['Rain']['b'])
    
    total_available_kavl_op = fill_kavl_op + spray_kavl_op + rain_kavl_op
    
    # DYNAMIC HWT CORRECTION
    hwt_curve = HWT_CORRECTION.get(fill_type, {'A': 0.0, 'B': 0.0, 'C': 0.0})
    calc_hwt_corr = (hwt_curve['A'] * (hw**2)) + (hwt_curve['B'] * hw) + hwt_curve['C']
    # CTI penalties only apply when water is hot; they never give "bonus" capability for cold water
    if calc_hwt_corr < 0 or hw < 95.0: 
        calc_hwt_corr = 0.0
        
    kavl_adjusted_op = total_available_kavl_op * (1.0 - (derate_percent / 100.0) - (calc_hwt_corr / 100.0))
    
    required_kavl_op = get_required_kavl_tchebycheff(hw, cw, wb, lg_ratio_operating, altitude_ft)
    
    # 2. PROPER CTI CAPABILITY BISECTION
    low_m = 0.1
    high_m = 5.0
    tolerance = 0.001
    cap_multiplier = 1.0
    
    for _ in range(100):
        mid_m = (low_m + high_m) / 2.0
        test_lg = mid_m * lg_ratio_operating
        
        req_test = get_required_kavl_tchebycheff(hw, cw, wb, test_lg, altitude_ft)
        
        fill_test = f_const['c'] * (test_lg ** -f_const['n']) * (fill_height ** f_const['m'])
        spray_test = ZONE_THERMAL['Spray']['a'] * (test_lg ** ZONE_THERMAL['Spray']['b'])
        rain_test = ZONE_THERMAL['Rain']['a'] * (test_lg ** ZONE_THERMAL['Rain']['b'])
        
        avail_test = (fill_test + spray_test + rain_test) * (1.0 - (derate_percent / 100.0) - (calc_hwt_corr / 100.0))
        
        if avail_test > req_test:
            low_m = mid_m
        else:
            high_m = mid_m
            
        if (high_m - low_m) < tolerance:
            cap_multiplier = mid_m
            break

    capability_percent = cap_multiplier * 100.0
    lg_adjusted = cap_multiplier * lg_ratio_operating

    return {
        "lg_ratio": round(lg_ratio_operating, 4),
        "lg_adjusted": round(lg_adjusted, 4),
        "fill_kavl": round(fill_kavl_op, 4),
        "spray_kavl": round(spray_kavl_op, 4),
        "rain_kavl": round(rain_kavl_op, 4),
        "total_available_kavl": round(total_available_kavl_op, 4),
        "kavl_adjusted": round(kavl_adjusted_op, 4),
        "required_kavl": round(required_kavl_op, 4),
        "capability_percent": round(capability_percent, 1),
        "hwt_corr_applied": round(calc_hwt_corr, 2)
    }