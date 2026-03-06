import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------
# Konfigurace
# ---------------------------------
PULL_MAX_PCT = 10.0  # maximální posun k hranici (%)

# ---------------------------------
# Funkce
# ---------------------------------
def generate_one_value(low: float, high: float, pull_pct: float, rng: np.random.Generator) -> float:
    """Generate one value in the given range, optionally pulled toward one bound."""
    if low > high:
        raise ValueError("Lower bound must be <= upper bound.")
    interval = high - low

    if interval == 0:
        return int(low)

    if pull_pct == 0:
        val = rng.uniform(low, high)
    else:
        prox = min(abs(pull_pct) / 100.0, 1.0)
        prox = max(prox, 1e-12)

        if pull_pct > 0:
            band_low = high - prox * interval
            val = rng.uniform(band_low, high)
        else:
            band_high = low + prox * interval
            val = rng.uniform(low, band_high)

    # clip to range
    val = float(np.clip(val, low, high))

    # NEW — round to integer
    return int(round(val))


def generate_scenarios(n_scenarios: int, items: list, seed: int | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    data = []

    for _ in range(n_scenarios):
        row = []
        for item in items:
            val = generate_one_value(item["low"], item["high"], item["pull"], rng)
            row.append(val)
        data.append(row)

    df = pd.DataFrame(data, columns=[item["name"] for item in items])
    df.insert(0, "Scenario", np.arange(1, n_scenarios + 1))
    return df


# ---------------------------------
# Položky
# ---------------------------------
MAIN_ITEMS = [
    "Analytický projekt implementace a migrace dat",
    "Implementace",
    "Licence",
    "Migrace všech stávajících dat",
    "Školení",
]

SUPPORT_ITEMS = [
    "Služba uživatelské a aplikační podpory v rámci pilotního provozu",
    "Služba uživatelské a aplikační podpory",
    "Služba provozu maintenance",
]

DEV_ITEMS = [
    "Služba rozvoje dle objednávek Objednatele",
    "Služba rozvoje dle objednávek Objednatele nad rámec avizovaných 320 MD",
]

ALL_ITEMS = MAIN_ITEMS + SUPPORT_ITEMS + DEV_ITEMS

# ---------------------------------
# Streamlit UI
# ---------------------------------
st.set_page_config(page_title="Generátor nabídek", page_icon="🎲", layout="wide")
st.title("🎲 Generátor nabídek — ceny uvedné v Kč")

with st.sidebar:
    st.header("Vstupní parametry")
    st.caption("0 % = náhodně • záporné = ke spodní hranici • kladné = k horní hranici")

    config_items = []

    for name in ALL_ITEMS:
        st.markdown(f"### {name}")
        col1, col2 = st.columns(2)

        low = col1.number_input(f"{name} – spodní hranice", value=0.0, step=100_000.0, format="%.0f")
        high = col2.number_input(f"{name} – horní hranice", value=100_000_000.0, step=100_000.0, format="%.0f")

        pull = st.slider(
            f"{name} – extrémní hodnota (%)",
            min_value=-PULL_MAX_PCT,
            max_value=PULL_MAX_PCT,
            value=0.0,
            step=0.1,
        )

        config_items.append({"name": name, "low": float(low), "high": float(high), "pull": float(pull)})
        st.markdown("---")

    n_scenarios = st.number_input("Počet scénářů", min_value=1, max_value=50_000, value=10, step=1)

    seed_opt = st.checkbox("Použít seed (opakovatelný výstup)", value=True)
    seed = st.number_input("Seed", min_value=0, max_value=1_000_000_000, value=42) if seed_opt else None

    generate_btn = st.button("Generovat scénáře", type="primary", use_container_width=True)


# ---------------------------------
# Výpočet a zobrazení
# ---------------------------------
if generate_btn:
    try:
        for item in config_items:
            if item["low"] > item["high"]:
                st.error(f"U položky **{item['name']}** je spodní hranice větší než horní.")
                st.stop()

        df = generate_scenarios(
            n_scenarios=int(n_scenarios),
            items=config_items,
            seed=int(seed) if seed is not None else None,
        )

        value_cols = [c for c in df.columns if c != "Scenario"]
        pivot_df = df.set_index("Scenario")[value_cols].T
        pivot_df.index.name = "Položka"

        # -------------------------
        # Barevné odlišení bloků
        # -------------------------
        def row_highlighter(row):
            idx = row.name
            if idx in MAIN_ITEMS:
                return ["background-color: #E6F2FF"] * len(row)
            elif idx in SUPPORT_ITEMS:
                return ["background-color: #E9FBE6"] * len(row)
            else:
                return ["background-color: #FFF9D6"] * len(row)

        styled = pivot_df.style.format("{:,.0f}").apply(row_highlighter, axis=1)

        # Dynamická výška
        row_height = 38
        header_height = 45
        total_height = header_height + row_height * len(pivot_df)

        st.dataframe(
            styled,
            use_container_width=True,
            height=total_height
        )

        # CSV export
        csv = pivot_df.to_csv(index=True).encode("utf-8")
        st.download_button(
            label="⬇️ Stáhnout CSV",
            data=csv,
            file_name="scenarios.csv",
            mime="text/csv",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Chyba při generování: {e}")

else:
    st.info("Nastav parametry vlevo a klikni na **Generovat scénáře**.")
