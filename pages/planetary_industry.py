import json
from collections import Counter

import pandas as pd
import streamlit as st

import esi

TIER_GROUPS = {"P4": 1041, "P3": 1040, "P2": 1034, "P1": 1042}
TIER_NAMES = {
    "P4": "Advanced Commodities - Tier 4",
    "P3": "Specialized Commodities - Tier 3",
    "P2": "Refined Commodities - Tier 2",
    "P1": "Basic Commodities - Tier 1",
}

# Factories per planet in a standard setup for each tier (P1 includes extraction).
FACTORIES_PER_PLANET = {"P4": 8, "P3": 24, "P2": 24, "P1": 8}
PLANETS_PER_CHARACTER = 6
HOURS_PER_MONTH = 24 * 30


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
def schematics():
    """Map each schematic output type ID to its output and input quantities per factory-hour."""
    result = {}
    with open("sde/jsonl/planetSchematics.jsonl") as f:
        for line in f:
            s = json.loads(line)
            cycles_per_hour = 3600 / s["cycleTime"]
            output = next(t for t in s["types"] if not t["isInput"])
            result[output["_key"]] = {
                "rate": output["quantity"] * cycles_per_hour,
                "inputs": {t["_key"]: t["quantity"] * cycles_per_hour for t in s["types"] if t["isInput"]},
            }
    return result


def recipe(type_id, p1_ids, recipes):
    """Return (recipe expression, P1 input count) for a commodity, with P1 as the leaf "1"."""
    if type_id in p1_ids:
        return "1", 1
    groups = Counter(recipe(i, p1_ids, recipes) for i in recipes[type_id]["inputs"])
    terms = []
    for (expr, value), count in sorted(groups.items(), key=lambda g: (-g[0][1], g[0][0])):
        if count == 1:
            terms.append(expr)
        elif expr == "1":
            terms.append(str(count))
        else:
            terms.append(f"{count}x({expr})" if "+" in expr else f"{count}x{expr}")
    return "+".join(terms), sum(value * count for (_, value), count in groups.items())


def planets(type_id, rate, tiers, recipes):
    """Planets needed to produce `rate` units/hour of a commodity, including its whole input chain."""
    schematic = recipes[type_id]
    factories = rate / schematic["rate"]
    total = factories / FACTORIES_PER_PLANET[tiers[type_id]]
    if tiers[type_id] != "P1":
        for input_id, quantity in schematic["inputs"].items():
            total += planets(input_id, factories * quantity, tiers, recipes)
    return total


@st.cache_data(ttl=3600)
def prices():
    return esi.markets_prices()


st.title("Planetary Industry")

commodities = pi_commodities().join(prices()["average_price"], on="type_id")
p1_ids = set(commodities.loc[commodities["group_id"] == TIER_GROUPS["P1"], "type_id"])
tiers = dict(zip(commodities["type_id"], commodities["group_id"].map({g: t for t, g in TIER_GROUPS.items()})))
recipes = schematics()
commodities[["recipe", "inputs"]] = pd.DataFrame(
    [recipe(t, p1_ids, recipes) for t in commodities["type_id"]], index=commodities.index
).astype({1: int})
commodities["price_per_input"] = commodities["average_price"] / commodities["inputs"]
commodities["planets"] = [planets(t, 1, tiers, recipes) for t in commodities["type_id"]]
commodities["isk_per_month"] = (
    commodities["average_price"] * HOURS_PER_MONTH * PLANETS_PER_CHARACTER / commodities["planets"] / 1e6
)

for tier, group_id in TIER_GROUPS.items():
    st.header(TIER_NAMES[tier])
    df = commodities[commodities["group_id"] == group_id].sort_values("price_per_input", ascending=False)
    st.dataframe(
        df[["name", "recipe", "inputs", "average_price", "price_per_input", "planets", "isk_per_month"]],
        hide_index=True,
        column_config={
            "name": "Commodity",
            "recipe": "Recipe",
            "inputs": st.column_config.NumberColumn("Inputs"),
            "average_price": st.column_config.NumberColumn("Average price (ISK)", format="accounting"),
            "price_per_input": st.column_config.NumberColumn("P/I", format="accounting"),
            "planets": st.column_config.NumberColumn("Planets/char", format="%.4f"),
            "isk_per_month": st.column_config.NumberColumn("kkISK/mo/char", format="accounting"),
        },
    )
