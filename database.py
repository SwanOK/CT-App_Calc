# database.py

COMPONENTS = {
    "fills": {
        "CF-1900SB": {
            "name": "19mm Cross-Fluted Film Fill",
            "thermal_c": 0.5367,
            "thermal_n": 0.702,
            "height_exp": 0.800,
            "calc_dp": lambda v, l, h: 0.000000629 * (v**1.80) * (1.0 + 0.045 * l) * h
        },
        "CF-1200MABT": {
            "name": "12mm High-Efficiency Mechanical Film Fill",
            "thermal_c": 0.7932,
            "thermal_n": 0.740,
            "height_exp": 0.700,
            "calc_dp": lambda v, l, h: 0.000000895 * (v**1.85) * (1.0 + 0.048 * l) * h
        }
    },
    "drift": {
        "DE120": {
            "name": "Cellular Drift Eliminator",
            "calc": lambda v_k: 0.1089 * (v_k**2)
        }
    }
}

def get_fill(model):
    return COMPONENTS["fills"].get(model, COMPONENTS["fills"]["CF-1900SB"])

def get_drift(model):
    return COMPONENTS["drift"].get(model, COMPONENTS["drift"]["DE120"])