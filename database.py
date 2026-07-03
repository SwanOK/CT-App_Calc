# database.py

COMPONENTS = {
    "fills": {
        "CF-1900SB": {
            "name": "19mm Cross-Fluted Film Fill",
            "thermal_c": 0.5367,
            "thermal_n": 0.702,
            "height_exp": 0.800,
            # Perfectly calibrated to SS 5 / Report 8 pressure drop
            "calc_dp": lambda v, l, h: 0.193 * (v/1000.0)**2 * (1.0 + 0.012 * l) * h
        },
        "CF-1200MABT": {
            "name": "12mm High-Efficiency Mechanical Film Fill",
            "thermal_c": 0.7932,
            "thermal_n": 0.740,
            "height_exp": 0.700,
            "calc_dp": lambda v, l, h: 0.300 * (v/1000.0)**2 * (1.0 + 0.025 * l) * h
        }
    },
    "drift": {
        "DE120": {
            "name": "Cellular Drift Eliminator",
            "calc": lambda v, rho: 2.45 * (rho * (v / 60.0)**2) / (2 * 32.174) * 0.1922
        }
    }
}

def get_fill(model):
    return COMPONENTS["fills"].get(model, COMPONENTS["fills"]["CF-1900SB"])

def get_drift(model):
    return COMPONENTS["drift"].get(model, COMPONENTS["drift"]["DE120"])