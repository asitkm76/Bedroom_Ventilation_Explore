import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

import co2_model as m

st.set_page_config(page_title="Home ventilation & CO₂ explorer", page_icon="🌬️", layout="wide")

METRICS = {
    "Steady-state CO₂ (ppm)": ("steady_state_CO2_ppm", "ppm", ".0f", "YlOrRd"),
    "Total ventilation (L/s)": ("total_ventilation_Lps", "L/s", ".1f", "viridis"),
    "Air changes per hour (ACH)": ("ACH", "ACH", ".1f", "crest"),
    "People-based ventilation (L/s)": ("people_ventilation_Lps", "L/s", ".1f", "magma"),
    "Area-based ventilation (L/s)": ("area_ventilation_Lps", "L/s", ".1f", "flare"),
}


@st.cache_data
def get_table(ceiling_height: float, outdoor_ppm: float):
    return m.build_table(ceiling_height, outdoor_ppm)


# ------------------------------------------------------------------ sidebar
st.sidebar.header("Choose a scenario")

room = st.sidebar.radio("Room type", list(m.ROOMS.keys()), horizontal=True)
cfg = m.ROOMS[room]

age = st.sidebar.selectbox("Age group of occupants", m.AGE_GROUPS, index=1)

scenarios = st.sidebar.multiselect(
    "Who is in the room?", list(m.SCENARIOS.keys()), default=list(m.SCENARIOS.keys()),
    help="Each selected scenario gets its own heat map column.",
)
areas = st.sidebar.multiselect(
    "Floor area (m²)", cfg["areas"], default=cfg["areas"],
    help="Each selected area gets its own heat map row.",
)
metric_label = st.sidebar.selectbox("What to show", list(METRICS.keys()))

with st.sidebar.expander("Advanced assumptions"):
    ceiling = st.number_input("Ceiling height (m)", 2.0, 4.0, m.DEFAULT_CEILING_HEIGHT_M, 0.1)
    outdoor = st.number_input("Outdoor CO₂ (ppm)", 380, 500, m.OUTDOOR_CO2_PPM, 5)
    show_values = st.checkbox("Show numbers in cells", value=True)
    shared_scale = st.checkbox("Same colour scale on all charts", value=True)

df = get_table(ceiling, outdoor)
col, unit, fmt, cmap = METRICS[metric_label]

# ------------------------------------------------------------------ header
st.title("🌬️ Home ventilation & CO₂ explorer")
st.markdown(
    f"How high does CO₂ get in a **{room.lower()}** (occupants {cfg['activity']}) "
    "when it is ventilated at the rates recommended by EN 16798? "
    "Pick a room, who is in it and how big it is on the left."
)

if not scenarios or not areas:
    st.info("Select at least one scenario and one floor area in the sidebar.")
    st.stop()

sub = df[
    (df["room"] == room) & (df["age_group"] == age)
    & (df["scenario"].isin(scenarios)) & (df["floor_area_m2"].isin(areas))
]

tab_map, tab_table, tab_about = st.tabs(["Heat maps", "Data table", "How it works"])

# ------------------------------------------------------------------ heat maps
with tab_map:
    areas_sorted = sorted(areas)
    scen_sorted = [s for s in m.SCENARIOS if s in scenarios]
    nrows, ncols = len(areas_sorted), len(scen_sorted)

    vmin = sub[col].min() if shared_scale else None
    vmax = sub[col].max() if shared_scale else None

    fig, axes = plt.subplots(nrows, ncols, figsize=(5.6 * ncols, 3.9 * nrows), squeeze=False)
    for r, ar in enumerate(areas_sorted):
        for c, sc in enumerate(scen_sorted):
            ax = axes[r][c]
            chunk = sub[(sub["scenario"] == sc) & (sub["floor_area_m2"] == ar)]
            pivot = (chunk.pivot(index="building_type", columns="category", values=col)
                     .reindex(index=m.BUILDING_TYPES, columns=m.CATEGORIES))
            sns.heatmap(
                pivot, annot=show_values, fmt=fmt, annot_kws={"size": 9}, cmap=cmap,
                vmin=vmin, vmax=vmax, linewidths=0.5, ax=ax,
                cbar_kws={"label": unit, "shrink": 0.8},
            )
            ax.set_title(f"{sc} | {ar} m²", fontsize=11)
            ax.set_xlabel("EN 16798 category" if r == nrows - 1 else "")
            ax.set_ylabel("Building type" if c == 0 else "")
            ax.tick_params(axis="x", labelrotation=30, labelsize=8)
            ax.tick_params(axis="y", labelrotation=0, labelsize=8)
    fig.suptitle(f"{metric_label} – {room.lower()}, age group {age}", fontsize=14)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)

    if col == "steady_state_CO2_ppm":
        st.caption(
            "Rules of thumb: below ~800 ppm is generally considered good; "
            "1,000 ppm is a commonly used comfort guide; above ~1,400 ppm indicates poor ventilation."
        )

# ------------------------------------------------------------------ table
with tab_table:
    st.caption("Results for the selection in the sidebar.")
    show = sub.sort_values(["scenario", "floor_area_m2", "category", "building_type"])[[
        "scenario", "floor_area_m2", "category", "building_type",
        "people_ventilation_Lps", "area_ventilation_Lps", "total_ventilation_Lps",
        "ACH", "co2_generation_Lps", "steady_state_CO2_ppm",
    ]].reset_index(drop=True)
    st.dataframe(
        show.style.format({
            "people_ventilation_Lps": "{:.2f}", "area_ventilation_Lps": "{:.2f}",
            "total_ventilation_Lps": "{:.2f}", "ACH": "{:.2f}",
            "co2_generation_Lps": "{:.4f}", "steady_state_CO2_ppm": "{:.0f}",
        }),
        use_container_width=True, height=500,
    )
    st.download_button("Download as CSV", show.to_csv(index=False), "co2_results.csv", "text/csv")

# ------------------------------------------------------------------ about
with tab_about:
    st.markdown(
        f"""
### The calculation
Steady-state CO₂ is reached when the CO₂ people breathe out equals the CO₂ removed by ventilation:

**CO₂ (ppm) = outdoor CO₂ + (CO₂ generated ÷ ventilation rate) × 1,000,000**

* **Outdoor CO₂:** {outdoor} ppm (editable under *Advanced assumptions*).
* **CO₂ generated (L/s):** depends on age, sex, number of people and activity –
  *sleeping* in the bedroom, *sitting* in the living room.
* **Ventilation rate (L/s):** EN 16798 requirement = people-based + floor-area-based
  (Tables B.6 and B.7). Rates depend on the **category** (I highest … IV lowest; *Adapted occupant* applies to homes only)
  and on how **polluting** the building is.
* **ACH** = ventilation (L/s) × 3.6 ÷ room volume, with room volume = floor area × {ceiling} m ceiling.

### Assumptions to be aware of
* Steady state: assumes the room has been occupied and ventilated at a constant rate long enough to stabilise.
  Real rooms (e.g. a closed bedroom door overnight) can take hours and may not reach it.
* Living-room floor areas ({', '.join(str(a) for a in m.ROOMS['Living room']['areas'])} m²) are illustrative choices.
* Sleep CO₂ generation rates: <https://doi.org/10.1111/ina.12383>.
"""
    )
