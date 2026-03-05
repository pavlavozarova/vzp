import numpy as np
import pandas as pd
import streamlit as st

# ----------------------------
# Configuration
# ----------------------------
PULL_MAX_PCT = 10.0  # Max absolute percent a slider can pull toward a bound

# ----------------------------
# Utility functions
# ----------------------------
def round_to_million(x: np.ndarray) -> np.ndarray:
    """Round values to the nearest 1,000,000."""
    return np.round(x / 1_000_000) * 1_000_000

def generate_one_scenario_with_pulls(
    low: float,
    high: float,
    pulls_pct: list[float],
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate one scenario of 5 values with per-position pulls.

    pulls_pct: list of 5 floats in [-PULL_MAX_PCT, +PULL_MAX_PCT]
       - Negative = pull toward lower bound
       - Positive = pull toward upper bound
       - 0 = uniform across the whole interval
       - Magnitude (abs) = proximity band as % of interval near the chosen bound
    """
    if low > high:
        raise ValueError("Lower bound must be <= upper bound.")
    if len(pulls_pct) != 5:
        raise ValueError("Expected 5 pull values (one per Value_1..Value_5).")

    interval = high - low
    # Handle degenerate interval
    if interval == 0:
        return np.array([low] * 5, dtype=float)

    values = []
    for p in pulls_pct:
        if p == 0:
            # No pull: uniform across the whole interval
            val = rng.uniform(low, high)
        else:
            prox = min(abs(p) / 100.0, 1.0)  # convert % to fraction; cap at 100%
            prox = max(prox, 1e-12)          # avoid zero-width band

            if p > 0:
                # Pull to upper: pick within last 'prox' fraction near high
                band_low = high - prox * interval
                val = rng.uniform(band_low, high)
            else:
                # Pull to lower: pick within first 'prox' fraction near low
                band_high = low + prox * interval
                val = rng.uniform(low, band_high)

        values.append(val)

    scenario = np.array(values, dtype=float)

    # Round to nearest million and clip back to [low, high]
    scenario = round_to_million(scenario)
    scenario = np.clip(scenario, low, high)
    return scenario

def generate_scenarios(
    n_scenarios: int,
    low: float,
    high: float,
    pulls_pct: list[float],
    seed: int | None = None,
) -> pd.DataFrame:
    """
    Generate n_scenarios rows; each row has 5 columns (Value_1 .. Value_5).
    """
    rng = np.random.default_rng(seed)
    data = []

    for _ in range(n_scenarios):
        scenario = generate_one_scenario_with_pulls(low, high, pulls_pct, rng)
        data.append(scenario)

    df = pd.DataFrame(data, columns=[f"Cena{i}" for i in range(1, 6)])
    df.insert(0, "Scenario", np.arange(1, n_scenarios + 1))
    return df


# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Generátor nabídek", page_icon="🎲", layout="centered")
st.title("🎲 Generátor nabídek (zaokrouhleno na 1,000,000)")

with st.sidebar:
    st.header("Vstupy")

    col1, col2 = st.columns(2)
    with col1:
        lower = st.number_input("Spodní hranice", value=0.0, step=1_000_000.0, format="%.0f")
    with col2:
        upper = st.number_input("Horní hranice", value=100_000_000.0, step=1_000_000.0, format="%.0f")

    st.markdown("### Určení extrémních hodnot")
    st.caption("Negativní = směrem k dolní hranice • Pozitivní = směrem k horní hranici • 0% = zcela náhodná hodnota")

    pulls = []
    for i in range(1, 6):
        pulls.append(
            st.slider(
                f"Posunutí ceny {i} (%)",
                min_value=-PULL_MAX_PCT,
                max_value= PULL_MAX_PCT,
                value=0.0,
                step=0.1,
            )
        )

    n_scenarios = st.number_input("Počet scénářů", min_value=1, max_value=50_000, value=10, step=1)

    seed_opt = st.checkbox("Zadejte random seed (možnost reprodukovat)?", value=True)
    seed = st.number_input("Seed", min_value=0, max_value=1_000_000_000, value=42, step=1) if seed_opt else None

    st.markdown("---")
    generate_btn = st.button("Generovat scénáře", type="primary", use_container_width=True)

# Validation messages
if lower > upper:
    st.error("Lower bound must be **less than or equal to** upper bound.")
elif (upper - lower) < 1_000_000:
    st.warning(
        "Note: The interval is smaller than 1,000,000. Rounding to the nearest million may cause many values "
        "to collapse to the same rounded values."
    )

# Generate scenarios
if generate_btn and lower <= upper:
    try:
        df = generate_scenarios(
            n_scenarios=int(n_scenarios),
            low=float(lower),
            high=float(upper),
            pulls_pct=[float(p) for p in pulls],
            seed=int(seed) if seed is not None else None,
        )

        # -----------------------
        # PIVOTED + THOUSANDS SEPARATORS
        # -----------------------
        value_cols = [c for c in df.columns if c.startswith("Cena")]

        # Scenarios as columns; Value_1..Value_5 as rows
        pivot_df = df.set_index("Scenario")[value_cols].T
        pivot_df.index.name = "Cena"

        # Thousands separators for display
        styled_pivot = pivot_df.style.format("{:,.0f}")

        st.dataframe(
            styled_pivot,
            use_container_width=True,
            height=min(700, 60 + 35 * len(pivot_df))
        )


        # Download original (not pivoted) as raw numbers
        csv = pivot_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Stáhnout CSV",
            data=csv,
            file_name="scenarios.csv",
            mime="text/csv",
            use_container_width=True
        )


    except Exception as e:
        st.error(f"Generation failed: {e}")

else:
    st.info("Zadejte parametry vlevo a kliněte na **Generovat scénáře**.")
