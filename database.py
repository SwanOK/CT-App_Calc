# database.py

COMPONENTS = {
    "fills": {
        "CF-1900SB": {
            "name": "19mm Cross-Fluted Film Fill",
            # Calibrated Merkel Coefficients (derived from Reports 5, 8, and 9)
            "thermal_c": 1.185,
            "thermal_n": 0.520,
            "height_exponent": 0.95, 
            
            # Dynamic Aerodynamic Resistance Curve Formula
            # Evaluates dP based on face velocity, water loading, and height
            "calc_dp": lambda v, l, height: 0.00000028 * (v ** 1.82) * (1.0 + 0.045 * l) * height
        },
        "CF-1200MABT": {
            "name": "12mm High-Efficiency Mechanical Film Fill",
            # Calibrated Merkel Coefficients (derived from Reports 1, 2, 3, 4, 6, 7)
            "thermal_c": 1.390,
            "thermal_n": 0.550,
            "height_exponent": 0.92,
            
            # Dynamic Aerodynamic Resistance Curve Formula
            "calc_dp": lambda v, l, height: 0.00000039 * (v ** 1.85) * (1.0 + 0.052 * l) * height
        }
    },
    "drift_eliminators": {
        "DE120": {
            "name": "Cellular Drift Eliminator",
            "k_factor": 2.45,
            # Dynamic loss calculation matching report kinetic pressure curves
            "calc_dp": lambda v, rho: 2.45 * (rho * (v / 60.0)**2) / (2 * 32.174) * 0.1922
        }
    }
}

def get_fill(model):
    """Safely looks up a fill model, falling back to CF-1900SB if not specified."""
    return COMPONENTS["fills"].get(model, COMPONENTS["fills"]["CF-1900SB"])

def get_drift(model):
    """Safely looks up a drift eliminator model, falling back to DE120."""
    return COMPONENTS["drift_eliminators"].get(model, COMPONENTS["drift_eliminators"]["DE120"])