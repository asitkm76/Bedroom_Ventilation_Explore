"""Steady-state CO2 model for rooms in a home (bedroom and living room).

CO2_steady (ppm) = outdoor_ppm + (y / x) * 1e6
    y = total occupant CO2 generation (L/s)
    x = total ventilation rate (L/s) = people-based + area-based (EN 16798)

CO2 generation sources: Persily & de Jonge style age/sex tables
(sleep: https://doi.org/10.1111/ina.12383); ventilation: EN 16798 Tables B.6 / B.7.
"""

import pandas as pd

OUTDOOR_CO2_PPM = 420
DEFAULT_CEILING_HEIGHT_M = 2.6

# ---------------------------------------------------------------------------
# CO2 generation rates (L/s per person) by age band and sex
# ---------------------------------------------------------------------------
AGE_GROUPS = ["16–<21", "21–<30", "30–<40", "40–<50", "50–<60", "60–<70", "70–<80", "≥80"]

MALE_SLEEP_LPS = {
    "16–<21": 0.0037, "21–<30": 0.0039, "30–<40": 0.0037, "40–<50": 0.0038,
    "50–<60": 0.0038, "60–<70": 0.0033, "70–<80": 0.0031, "≥80": 0.0030,
}
FEMALE_SLEEP_LPS = {
    "16–<21": 0.0029, "21–<30": 0.0031, "30–<40": 0.0029, "40–<50": 0.0029,
    "50–<60": 0.0030, "60–<70": 0.0027, "70–<80": 0.0026, "≥80": 0.0025,
}
MALE_SITTING_LPS = {
    "16–<21": 0.0045, "21–<30": 0.0048, "30–<40": 0.0046, "40–<50": 0.0046,
    "50–<60": 0.0046, "60–<70": 0.0040, "70–<80": 0.0038, "≥80": 0.0036,
}
FEMALE_SITTING_LPS = {
    "16–<21": 0.0036, "21–<30": 0.0038, "30–<40": 0.0035, "40–<50": 0.0036,
    "50–<60": 0.0036, "60–<70": 0.0033, "70–<80": 0.0032, "≥80": 0.0030,
}

# ---------------------------------------------------------------------------
# Rooms: which generation table applies and which floor areas to offer.
# Living-room areas are an assumption - edit freely.
# ---------------------------------------------------------------------------
ROOMS = {
    "Bedroom": {
        "activity": "sleeping",
        "male": MALE_SLEEP_LPS,
        "female": FEMALE_SLEEP_LPS,
        "areas": [8, 10, 12],
    },
    "Living room": {
        "activity": "sitting",
        "male": MALE_SITTING_LPS,
        "female": FEMALE_SITTING_LPS,
        "areas": [15, 20, 25, 30],
    },
}

# Occupancy scenarios: (number of males, number of females)
SCENARIOS = {
    "1 male": (1, 0),
    "1 female": (0, 1),
    "2 male": (2, 0),
    "2 female": (0, 2),
    "1 male + 1 female": (1, 1),
}

# ---------------------------------------------------------------------------
# EN 16798 ventilation requirements
# ---------------------------------------------------------------------------
CATEGORIES = ["I", "II", "III", "IV", "Adapted occupant"]
BUILDING_TYPES = ["Very low polluting", "Low polluting", "Non low-polluting", "Residential"]

VENT_PER_PERSON_LPS = {"I": 10.0, "II": 7.0, "III": 4.0, "IV": 2.5, "Adapted occupant": 2.5}

VENT_PER_M2_LPS = {
    "I":   {"Very low polluting": 0.50, "Low polluting": 1.0, "Non low-polluting": 1.0, "Residential": 0.15},
    "II":  {"Very low polluting": 0.35, "Low polluting": 0.7, "Non low-polluting": 1.4, "Residential": 0.15},
    "III": {"Very low polluting": 0.20, "Low polluting": 0.4, "Non low-polluting": 0.8, "Residential": 0.15},
    "IV":  {"Very low polluting": 0.15, "Low polluting": 0.3, "Non low-polluting": 0.6, "Residential": 0.15},
    "Adapted occupant": {b: 0.15 for b in BUILDING_TYPES},
}


def build_table(ceiling_height_m: float = DEFAULT_CEILING_HEIGHT_M,
                outdoor_co2_ppm: float = OUTDOOR_CO2_PPM) -> pd.DataFrame:
    """Return every combination of room, age, scenario, area, category, building type."""
    rows = []
    for room, cfg in ROOMS.items():
        for age in AGE_GROUPS:
            for scenario, (n_m, n_f) in SCENARIOS.items():
                n = n_m + n_f
                co2_gen = n_m * cfg["male"][age] + n_f * cfg["female"][age]
                for area in cfg["areas"]:
                    volume = area * ceiling_height_m
                    for category in CATEGORIES:
                        for building in BUILDING_TYPES:
                            people_vent = n * VENT_PER_PERSON_LPS[category]
                            area_vent = area * VENT_PER_M2_LPS[category][building]
                            total_vent = people_vent + area_vent
                            rows.append({
                                "room": room,
                                "age_group": age,
                                "scenario": scenario,
                                "occupants": n,
                                "floor_area_m2": area,
                                "volume_m3": volume,
                                "category": category,
                                "building_type": building,
                                "people_ventilation_Lps": people_vent,
                                "area_ventilation_Lps": area_vent,
                                "total_ventilation_Lps": total_vent,
                                "co2_generation_Lps": co2_gen,
                                "ACH": total_vent * 3.6 / volume,
                                "steady_state_CO2_ppm": outdoor_co2_ppm + co2_gen / total_vent * 1e6,
                            })
    return pd.DataFrame(rows)
