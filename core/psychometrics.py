# core/psychrometrics.py
import psychrolib

# Set unit system to Imperial (IP) to match your screenshots (Fahrenheit, feet, gpm)
psychrolib.SetUnitSystem(psychrolib.IP)

def get_air_properties(dry_bulb, wet_bulb, altitude_ft):
    """
    Calculates air density and specific volume based on altitude and temperatures.
    """
    # Standard atmospheric pressure at a given altitude
    pressure = psychrolib.GetStandardAtmPressure(altitude_ft)
    
    # Calculate humidity ratio and density
    hum_ratio = psychrolib.GetHumRatioFromTwetBulb(dry_bulb, wet_bulb, pressure)
    density = psychrolib.GetMoistAirDensity(dry_bulb, hum_ratio, pressure)
    specific_volume = psychrolib.GetMoistAirVolume(dry_bulb, hum_ratio, pressure)
    
    return {
        "pressure": pressure,
        "density": density,
        "specific_volume": specific_volume
    }