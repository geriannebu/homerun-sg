import numpy as np
import pandas as pd

from backend.utils.constants import TOWNS
from backend.schemas.inputs import UserInputs

from data.load_data import load_all_data

def get_active_listings(inputs):
    df, _ = load_all_data()

    if inputs.town:
        df = df[df["town"] == inputs.town.strip().upper()]

    if getattr(inputs, "flat_types", None):
        df = df[df["flat_type"].isin(inputs.flat_types)]

    if inputs.floor_area_sqm:
        df = df[
            (df["floor_area_sqm"] >= inputs.floor_area_sqm - 10) &
            (df["floor_area_sqm"] <= inputs.floor_area_sqm + 10)
        ]

    return df.copy()