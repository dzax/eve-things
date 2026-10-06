import json
from collections import Counter

import pandas as pd
import streamlit as st

import esi

TIER_GROUPS = {
    "P4": 1041,  # Advanced Commodities - Tier 4
    "P3": 1040,  # Specialized Commodities - Tier 3
    "P2": 1034,  # Refined Commodities - Tier 2
    "P1": 1042,  # Basic Commodities - Tier 1
}


@st.cache_data
def pi_commodities():
    group_ids = set(TIER_GROUPS.values())
    rows = []
    with open("sde/jsonl/types.jsonl") as f:
        for line in f:
            if '"groupID"' not in line:
                continue
            t = json.loads(line)
            if t.get("groupID") in group_ids and t.get("published"):
                rows.append({"type_id": t["_key"], "group_id": t["groupID"], "name": t["name"]["en"]})
    return pd.DataFrame(rows)


@st.cache_data
def schematic_inputs():
    """Map each schematic output type ID to its input type IDs."""
    inputs = {}
    with open("sde/jsonl/planetSchematics.jsonl") as f:
        for line in f:
            s = json.loads(line)
            output = next(t["_key"] for t in s["types"] if not t["isInput"])
            inputs[output] = [t["_key"] for t in s["types"] if t["isInput"]]
    return inputs


def recipe(type_id, p1_ids, inputs):
    """Return (recipe expression, P1 input count) for a commodity, with P1 as the leaf "1"."""
    if type_id in p1_ids:
        return "1", 1
    groups = Counter(recipe(i, p1_ids, inputs) for i in inputs[type_id])
    terms = []
    for (expr, value), count in sorted(groups.items(), key=lambda g: (-g[0][1], g[0][0])):
        if count == 1:
            terms.append(expr)
        elif expr == "1":
            terms.append(str(count))
        else:
            terms.append(f"{count}x({expr})" if "+" in expr else f"{count}x{expr}")
    return "+".join(terms), sum(value * count for (_, value), count in groups.items())


@st.cache_data(ttl=3600)
def prices():
    return esi.markets_prices()


st.title("Planetary Industry")

commodities = pi_commodities().join(prices()["average_price"], on="type_id")
p1_ids = set(commodities.loc[commodities["group_id"] == TIER_GROUPS["P1"], "type_id"])
commodities[["recipe", "inputs"]] = [
    recipe(t, p1_ids, schematic_inputs()) for t in commodities["type_id"]
]
commodities["price_per_input"] = commodities["average_price"] / commodities["inputs"]

for tier, group_id in TIER_GROUPS.items():
    st.header(tier)
    df = commodities[commodities["group_id"] == group_id].sort_values("price_per_input", ascending=False)
    st.dataframe(
        df[["name", "recipe", "inputs", "average_price", "price_per_input"]],
        hide_index=True,
        column_config={
            "name": "Commodity",
            "recipe": "Recipe",
            "inputs": st.column_config.NumberColumn("Inputs"),
            "average_price": st.column_config.NumberColumn("Average price (ISK)", format="accounting"),
            "price_per_input": st.column_config.NumberColumn("P/I", format="accounting"),
        },
    )
