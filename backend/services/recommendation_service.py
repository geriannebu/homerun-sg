import numpy as np
import pandas as pd

from backend.utils.constants import TOWNS
from backend.schemas.inputs import UserInputs


def mock_recommend_towns(inputs: UserInputs) -> pd.DataFrame:
    if inputs.town:
        return pd.DataFrame()

    rows = []
    for town in np.random.choice(TOWNS, 5, replace=False):
        estimated_price = np.random.randint(350000, 850000)
        within_budget = True if inputs.budget is None else estimated_price <= inputs.budget
        match_score = np.random.uniform(72, 96)

        rows.append({
            "town": town,
            "estimated_price": estimated_price,
            "within_budget": within_budget,
            "match_score": round(match_score, 1),
            "why_it_matches": "Strong overall fit based on affordability, amenities, and anchor proximity.",
        })

    return pd.DataFrame(rows).sort_values("match_score", ascending=False).reset_index(drop=True)