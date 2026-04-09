# ---------------------------------------------------------------------------
# Towns & Flat Types
# ---------------------------------------------------------------------------
TOWNS = [
    "ANG MO KIO", "BEDOK", "BISHAN", "BUKIT BATOK", "BUKIT MERAH",
    "BUKIT PANJANG", "BUKIT TIMAH", "CHOA CHU KANG",
    "CLEMENTI", "GEYLANG", "HOUGANG", "JURONG EAST", "JURONG WEST",
    "KALLANG", "MARINE PARADE", "NOVENA", "OUTRAM", "PASIR RIS", "PUNGGOL",
    "QUEENSTOWN", "ROCHOR", "SEMBAWANG", "SENGKANG", "SERANGOON", "TAMPINES",
    "TOA PAYOH", "WOODLANDS", "YISHUN",
]

FLAT_TYPES = ["1 ROOM", "2 ROOM", "3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE", "MULTI-GENERATION"]

# ---------------------------------------------------------------------------
# School Options
# ---------------------------------------------------------------------------
SCHOOL_OPTIONS = ["Any", "Primary schools", "Secondary schools", "Both"]

# ---------------------------------------------------------------------------
# Amenity Labels
# ---------------------------------------------------------------------------
AMENITY_LABELS = {
    "train": "MRT stations",
    "bus": "Bus stops",
    "polyclinic": "Hospitals / polyclinics",
    "primary_school": "Schools",
    "hawker": "Hawker centres",
    "mall": "Shopping malls",
    "supermarket": "Supermarkets",
}

# ---------------------------------------------------------------------------
# Amenity Colors (RGBA)
# ---------------------------------------------------------------------------
AMENITY_COLORS = {
    "town": [31, 119, 180, 180],
    "anchor": [148, 103, 189, 220],
    "train": [214, 39, 40, 160],
    "bus": [255, 127, 14, 140],
    "healthcare": [44, 160, 44, 150],      # polyclinics
    "schools": [23, 190, 207, 150],        # primary schools
    "hawker": [140, 86, 75, 150],
    "retail": [227, 119, 194, 150],        # malls
    "supermarket": [255, 215, 0, 150],     # supermarkets
}

# ---------------------------------------------------------------------------
# Amenity Keys (for scoring / iteration)
# ---------------------------------------------------------------------------
AMENITY_KEYS = [
    "train",
    "bus",
    "primary_school",
    "hawker",
    "mall",
    "polyclinic",
    "supermarket",
]

# ---------------------------------------------------------------------------
# Town Coordinates
# ---------------------------------------------------------------------------
TOWN_COORDS = {
    "ANG MO KIO":     (1.3691, 103.8454),
    "BEDOK":          (1.3236, 103.9273),
    "BISHAN":         (1.3500, 103.8485),
    "BUKIT BATOK":    (1.3496, 103.7528),
    "BUKIT MERAH":    (1.2773, 103.8195),
    "BUKIT PANJANG":  (1.3774, 103.7719),
    "BUKIT TIMAH":    (1.3294, 103.8021),
    "CHOA CHU KANG":  (1.3854, 103.7443),
    "CLEMENTI":       (1.3151, 103.7651),
    "GEYLANG":        (1.3201, 103.8831),
    "HOUGANG":        (1.3612, 103.8863),
    "JURONG EAST":    (1.3329, 103.7436),
    "JURONG WEST":    (1.3404, 103.7068),
    "KALLANG":        (1.3123, 103.8660),
    "MARINE PARADE":  (1.3023, 103.9063),
    "NOVENA":         (1.3200, 103.8441),
    "OUTRAM":         (1.2797, 103.8395),
    "PASIR RIS":      (1.3731, 103.9493),
    "PUNGGOL":        (1.4043, 103.9021),
    "QUEENSTOWN":     (1.2942, 103.7860),
    "ROCHOR":         (1.3040, 103.8573),
    "SEMBAWANG":      (1.4491, 103.8201),
    "SENGKANG":       (1.3909, 103.8952),
    "SERANGOON":      (1.3554, 103.8679),
    "TAMPINES":       (1.3496, 103.9568),
    "TOA PAYOH":      (1.3343, 103.8563),
    "WOODLANDS":      (1.4360, 103.7865),
    "YISHUN":         (1.4294, 103.8354),
}

# ---------------------------------------------------------------------------
# Amenity Mapping (to column prefixes / scoring)
# ---------------------------------------------------------------------------
AMENITY_MAPPING = {
    "train":          "train",          # walk_train_min1, walk_train_avg_mins
    "bus":            "bus",            # walk_bus_min1, walk_bus_avg_mins
    "polyclinic":     "polyclinic",     # walk_polyclinic_min1, walk_polyclinic_avg_mins
    "primary_school": "primary_school", # walk_primary_school_min1, walk_primary_school_avg_mins
    "hawker":         "hawker",         # walk_hawker_min1, walk_hawker_avg_mins
    "mall":           "mall",           # walk_mall_min1, walk_mall_avg_mins
    "supermarket":    "supermarket",    # walk_supermarket_min1, walk_supermarket_avg_mins
}