# Planetary Industry page

Streamlit page (`pages/planetary_industry.py`, registered in `app.py` as "Planetary Industry") that lists all planetary industry (PI) commodities with market prices, recipe structure and production profitability per character.

## Data sources

- **Commodities**: SDE `sde/jsonl/types.jsonl`. Published types in the PI commodity groups:

  | Tier | Group ID | Group                               |
  |------|----------|-------------------------------------|
  | P4   | 1041     | Advanced Commodities - Tier 4       |
  | P3   | 1040     | Specialized Commodities - Tier 3    |
  | P2   | 1034     | Refined Commodities - Tier 2        |
  | P1   | 1042     | Basic Commodities - Tier 1          |

  Name is the English name (`name.en`).
- **Recipes**: SDE `sde/jsonl/planetSchematics.jsonl`. Each schematic has exactly one output type and one or more input types, each with a quantity per cycle, and a `cycleTime` in seconds. Quantities are normalised to units per factory-hour (`quantity * 3600 / cycleTime`).
- **Prices**: ESI `GET /markets/prices`, field `average_price`, joined on type ID. Cached for 1 hour. Commodities without a price show an empty price and empty derived values.

SDE-derived data is cached for the lifetime of the Streamlit process.

## Layout

Title "Planetary Industry", then one section per tier, in the order P4, P3, P2, P1. Each section has a header with the group name (e.g. "Advanced Commodities - Tier 4") and a table of that tier's commodities, without an index column.

Each table is sorted **descending by P/I**. Rows without a price go last.

## Columns

| Column              | Content                                    | Format                                   |
|---------------------|--------------------------------------------|------------------------------------------|
| Commodity           | Commodity name                             | text                                     |
| Recipe              | Recipe structure expression                | text, e.g. `3x2x2`                       |
| Inputs              | Number of P1 input lines in the recipe     | integer                                  |
| Average price (ISK) | ESI average price                          | thousand separators, 2 decimals          |
| P/I                 | Average price / Inputs                     | thousand separators, 2 decimals          |
| Planets/char        | Planets needed to produce 1 unit/hour      | 4 decimals                               |
| kkISK/mo/char       | Monthly output value of one character, in millions of ISK | thousand separators, 2 decimals |

### Recipe

The structure of the blueprint expanded down to P1, with P1 as the leaf `1`.

- A P1 commodity's recipe is `1`.
- For any other commodity, take the recipes of its schematic inputs and group identical ones:
  - a single input contributes its recipe as-is;
  - `n` identical P1 inputs contribute `n` (not `nx1`);
  - `n` identical non-P1 inputs contribute `nx<recipe>`, with the recipe wrapped in parentheses if it contains `+`.
- Groups are joined with `+`, ordered by descending input count (then by expression).

Resulting forms with current SDE data: P2 `2`; P3 `2x2`, `3x2`; P4 `3x2x2`, `3x3x2`, `2x2x2+1`.

### Inputs

The total number of P1 input lines of the recipe, i.e. the Recipe expression evaluated as an integer (`x` is multiplication, `+` is addition). P1 has a value of 1.

Current values: P1 1, P2 2, P3 4 or 6, P4 9, 12 or 18.

### P/I

`Average price / Inputs`: price per P1 input line.

### Planets/char

The number of planets (fractional) needed to produce exactly 1 unit/hour of the commodity, including its whole production chain down to P1. Assumes many characters with perfectly used capacity and no waste.

Standard setup assumptions:

| Tier | Factories per planet | Notes                          |
|------|----------------------|--------------------------------|
| P1   | 8                    | combined with extraction       |
| P2   | 24                   |                                |
| P3   | 24                   |                                |
| P4   | 8                    |                                |

Max skills: 6 planets per character.

Computation, for a commodity at rate `r` units/hour:

1. Factories = `r / output per factory-hour` (from the schematic).
2. Planets for this tier = factories / factories per planet for the commodity's tier.
3. For each input of the schematic (except for P1, whose P0 input comes from extraction on the same planet), add the planets needed to produce `factories * input quantity per factory-hour` of that input, recursively.

Production rates from current SDE data: P1 40/h (3000 P0 -> 20 per 30 min), P2 5/h, P3 3/h, P4 1/h. P1 inputs used directly by a P4 count as P1 planets.

### kkISK/mo/char

The value one character produces per month at perfect throughput, in millions of ISK:

```
average_price * 720 * 6 / Planets/char / 1,000,000
```

where 720 is the hours in a 30-day month and 6 is planets per character.
